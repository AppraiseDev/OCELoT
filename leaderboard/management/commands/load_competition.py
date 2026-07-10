"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

Management command to bulk-create a Competition and its TestSets (or add
TestSets to an existing Competition) from a JSON definition file.

The command copies each gold JSONL file into media storage as the test set's
source and reference files (under distinct names) and lets TestSet.save()
generate the .txt companions. It never creates submissions and never activates
anything: created objects are left inactive and the command prints a reminder
to activate them.
"""
import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from leaderboard.models import Competition
from leaderboard.models import Language
from leaderboard.models import TestSet
from leaderboard.models.constants import FILE_FORMAT_CHOICES
from leaderboard.models.constants import JSONL_FILE
from leaderboard.utils import detect_jsonl_format

VALID_FILE_FORMATS = {choice[0] for choice in FILE_FORMAT_CHOICES}

# Keys copied from `defaults`/per-test-set config onto the TestSet. Test sets
# default to inactive unless `is_active` is set to true in the definition.
_TESTSET_SCALAR_DEFAULTS = {
    'file_format': JSONL_FILE,
    'compute_scores': True,
    'validate': True,
    'is_public': None,
    'collection': None,
    'is_active': False,
}


class _DryRunRollback(Exception):
    """Internal sentinel used to roll back the transaction on --dry-run."""


class Command(BaseCommand):
    help = (
        'Create a competition and its test sets (or add test sets to an '
        'existing competition) from a JSON definition file.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'definition',
            type=str,
            help='Path to the JSON definition file.',
        )
        parser.add_argument(
            '--base-dir',
            type=str,
            default=None,
            help=(
                'Base directory for resolving relative gold_file/src_file/'
                'ref_file paths (default: the definition file directory).'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and report without writing anything.',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help=(
                'Update fields of an existing competition or test set in '
                'place instead of reusing/skipping it.'
            ),
        )

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _parse_datetime(value, field_name):
        """Parse an ISO 8601 datetime string, tolerating a trailing 'Z'."""
        if value in (None, ''):
            return None
        parsed = parse_datetime(value)
        if parsed is None and isinstance(value, str) and value.endswith('Z'):
            parsed = parse_datetime(value[:-1] + '+00:00')
        if parsed is None:
            raise CommandError(
                f'Invalid datetime for "{field_name}": {value!r} '
                f'(expected ISO 8601, e.g. 2026-07-01T00:00:00Z)'
            )
        return parsed

    @staticmethod
    def _get_or_create_language(code):
        """Return a Language for the given ISO code, creating one if needed.

        `code` is not unique in the schema, so we fetch the first match rather
        than risk MultipleObjectsReturned from get_or_create.
        """
        if not code:
            return None
        language = Language.objects.filter(code=code).first()
        if language is None:
            language = Language.objects.create(code=code, name=code)
        return language

    def _resolve_path(self, value, base_dir, field_name, testset_name):
        """Resolve a file path against base_dir and ensure it exists."""
        if not value:
            return None
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = base_dir / path
        path = path.resolve()
        if not path.is_file():
            raise CommandError(
                f'Test set "{testset_name}": {field_name} not found: {path}'
            )
        return path

    @staticmethod
    def _attach_file(field, source_path, target_name):
        """Copy source_path into storage under target_name (no model save)."""
        with open(source_path, 'rb') as handle:
            field.save(target_name, File(handle), save=False)

    # -- validation ------------------------------------------------------

    def _load_definition(self, definition_path):
        try:
            with open(definition_path, encoding='utf-8') as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise CommandError(f'Invalid JSON in {definition_path}: {exc}')
        if not isinstance(data, dict):
            raise CommandError('Definition file must be a JSON object.')

        competition = data.get('competition')
        if not isinstance(competition, dict) or not competition.get('name'):
            raise CommandError(
                'Definition must contain a "competition" object with a "name".'
            )

        testsets = data.get('testsets')
        if not isinstance(testsets, list) or not testsets:
            raise CommandError(
                'Definition must contain a non-empty "testsets" array.'
            )
        return data

    def _build_testset_config(self, raw, defaults, base_dir):
        """Merge defaults with a per-test-set entry and resolve file paths."""
        name = raw.get('name')
        if not name:
            raise CommandError('Every test set must have a "name".')

        config = dict(_TESTSET_SCALAR_DEFAULTS)
        for key in _TESTSET_SCALAR_DEFAULTS:
            if key in defaults:
                config[key] = defaults[key]
            if key in raw:
                config[key] = raw[key]

        if config['file_format'] not in VALID_FILE_FORMATS:
            raise CommandError(
                f'Test set "{name}": invalid file_format '
                f'{config["file_format"]!r} (choices: '
                f'{", ".join(sorted(VALID_FILE_FORMATS))}).'
            )

        gold = raw.get('gold_file')
        src_value = raw.get('src_file', gold)
        # ref_file defaults to the gold file; an explicit null disables refs.
        ref_value = raw['ref_file'] if 'ref_file' in raw else gold

        src_path = self._resolve_path(src_value, base_dir, 'src_file', name)
        if src_path is None:
            raise CommandError(
                f'Test set "{name}": a "gold_file" or "src_file" is required.'
            )
        ref_path = self._resolve_path(ref_value, base_dir, 'ref_file', name)

        return {
            'name': name,
            'config': config,
            'src_path': src_path,
            'ref_path': ref_path,
            'source_language': raw.get('source_language'),
            'target_language': raw.get('target_language'),
        }

    # -- main ------------------------------------------------------------

    def handle(self, *args, **options):
        definition_path = Path(options['definition']).expanduser().resolve()
        if not definition_path.is_file():
            raise CommandError(f'Definition file not found: {definition_path}')

        base_dir = (
            Path(options['base_dir']).expanduser().resolve()
            if options['base_dir']
            else definition_path.parent
        )
        dry_run = options['dry_run']
        update = options['update']

        data = self._load_definition(definition_path)
        comp_def = data['competition']
        defaults = data.get('defaults', {})

        # Resolve and validate every test set up front so we fail before any
        # writes if something is wrong.
        testsets = [
            self._build_testset_config(raw, defaults, base_dir)
            for raw in data['testsets']
        ]

        comp_name = comp_def['name']
        existing_comp = Competition.objects.filter(name=comp_name).first()
        if existing_comp is None and not comp_def.get('description'):
            raise CommandError(
                f'Competition "{comp_name}" does not exist and no '
                f'"description" was provided to create it.'
            )

        if dry_run:
            self._report_dry_run(
                comp_name, existing_comp, testsets, update,
                bool(comp_def.get('is_active', False)),
            )
            return

        created_testsets = 0
        skipped_testsets = 0
        inactive_created = 0
        try:
            with transaction.atomic():
                competition, comp_created = self._upsert_competition(
                    comp_def, existing_comp, update
                )
                for entry in testsets:
                    created, is_active = self._create_testset(
                        competition, entry, update
                    )
                    if created:
                        created_testsets += 1
                        if not is_active:
                            inactive_created += 1
                    else:
                        skipped_testsets += 1
        except _DryRunRollback:  # pragma: no cover - defensive
            return

        self._report_summary(
            competition, comp_created, created_testsets, skipped_testsets,
            inactive_created,
        )

    def _upsert_competition(self, comp_def, existing_comp, update):
        fields = {
            'description': comp_def.get('description', ''),
            'is_public': comp_def.get('is_public', None),
            'is_active': bool(comp_def.get('is_active', False)),
            'start_time': self._parse_datetime(
                comp_def.get('start_time'), 'competition.start_time'
            ),
            'deadline': self._parse_datetime(
                comp_def.get('deadline'), 'competition.deadline'
            ),
        }

        if existing_comp is None:
            competition = Competition.objects.create(
                name=comp_def['name'],
                **fields,
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created competition "{competition.name}".')
            )
            return competition, True

        if update:
            for key, value in fields.items():
                setattr(existing_comp, key, value)
            existing_comp.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated competition "{existing_comp.name}".'
                )
            )
        else:
            self.stdout.write(
                f'Using existing competition "{existing_comp.name}" '
                f'(pass --update to modify its fields).'
            )
        return existing_comp, False

    def _create_testset(self, competition, entry, update):
        """Create one test set; return True if created, False if skipped."""
        name = entry['name']
        existing = TestSet.objects.filter(
            competition=competition, name=name
        ).first()
        if existing is not None and not update:
            self.stdout.write(
                self.style.WARNING(
                    f'  - skipped existing test set "{name}" '
                    f'(pass --update to overwrite).'
                )
            )
            return False, False

        test_set = existing or TestSet(competition=competition, name=name)
        config = entry['config']
        test_set.file_format = config['file_format']
        test_set.compute_scores = config['compute_scores']
        test_set.validate = config['validate']
        test_set.is_public = config['is_public']
        test_set.collection = config['collection']
        test_set.is_active = bool(config['is_active'])
        test_set.source_language = self._get_or_create_language(
            entry['source_language']
        )
        test_set.target_language = self._get_or_create_language(
            entry['target_language']
        )

        slug = slugify(name) or 'testset'
        self._attach_file(test_set.src_file, entry['src_path'], f'{slug}-src.jsonl')
        if entry['ref_path'] is not None:
            self._attach_file(
                test_set.ref_file, entry['ref_path'], f'{slug}-ref.jsonl'
            )
        else:
            test_set.ref_file = None

        test_set.save()  # generates the .txt companions

        detected = detect_jsonl_format(str(entry['src_path']))
        verb = 'Updated' if existing else 'Created'
        self.stdout.write(
            self.style.SUCCESS(
                f'  - {verb} test set "{name}" '
                f'[{config["file_format"]}, format={detected or "unknown"}].'
            )
        )
        if detected is None and config['file_format'] == JSONL_FILE:
            self.stdout.write(
                self.style.WARNING(
                    f'    WARNING: unrecognized JSONL format for "{name}"; '
                    f'automatic scoring may not work.'
                )
            )
        return True, test_set.is_active

    # -- reporting -------------------------------------------------------

    def _report_dry_run(self, comp_name, existing_comp, testsets, update, comp_would_active):
        self.stdout.write('DRY RUN - no changes will be written.')
        if existing_comp is None:
            self.stdout.write(f'Would create competition "{comp_name}".')
        else:
            action = 'update' if update else 'reuse'
            self.stdout.write(
                f'Would {action} existing competition "{comp_name}".'
            )
        for entry in testsets:
            name = entry['name']
            exists = existing_comp is not None and TestSet.objects.filter(
                competition=existing_comp, name=name
            ).exists()
            if exists and not update:
                action = 'skip (exists)'
            elif exists:
                action = 'update'
            else:
                action = 'create'
            detected = detect_jsonl_format(str(entry['src_path']))
            state = 'active' if entry['config']['is_active'] else 'inactive'
            self.stdout.write(
                f'  - {action} [{state}]: "{name}" '
                f'[format={detected or "unknown"}, src={entry["src_path"].name}]'
            )
        would_activate = bool(comp_would_active) and all(
            e['config']['is_active'] for e in testsets
        )
        if would_activate:
            self.stdout.write(
                'NOTE: created objects would be ACTIVE (is_active=true).'
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    'NOTE: some created objects would be INACTIVE; activate '
                    'them in the admin (or set is_active=true) afterwards.'
                )
            )

    def _report_summary(
        self, competition, comp_created, created_testsets, skipped_testsets,
        inactive_created,
    ):
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done: competition "{competition.name}" '
                f'({"created" if comp_created else "existing"}), '
                f'{created_testsets} test set(s) created, '
                f'{skipped_testsets} skipped.'
            )
        )
        if inactive_created or not competition.is_active:
            self.stdout.write(
                self.style.WARNING(
                    'NOTE: some created objects are INACTIVE. Remember to '
                    'activate the competition and its test sets in the admin '
                    '(or set is_active=true) to make them visible on the '
                    'leaderboard.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    'All created objects are ACTIVE and visible on the '
                    'leaderboard.'
                )
            )
