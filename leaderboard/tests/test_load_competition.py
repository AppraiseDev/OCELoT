"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for the load_competition management command.
"""
import json
import os
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError

from .common import (
    Competition, MEDIA_ROOT, TestCase, TestSet, TESTDATA_DIR,
)

LOWRES_DIR = os.path.join(TESTDATA_DIR, 'jsonl-wmt26-lowres')
COMP_NAME = 'WMT26 LowRes Command Test'


class LoadCompetitionCommandTests(TestCase):
    """Tests bulk creation of a competition and its test sets."""

    def tearDown(self):
        # Remove media artifacts created by the command (files live outside the
        # test transaction, so they must be cleaned up explicitly).
        testsets_dir = Path(MEDIA_ROOT) / 'testsets'
        if testsets_dir.exists():
            for path in testsets_dir.glob('wmt26lowres-test*'):
                path.unlink()

    def _write_definition(self, testsets, competition=None):
        definition = {
            'competition': competition or {
                'name': COMP_NAME,
                'description': 'Description for the command test.',
                'is_public': None,
            },
            'defaults': {
                'file_format': 'JSONL',
                'compute_scores': True,
                'validate': True,
            },
            'testsets': testsets,
        }
        handle = tempfile.NamedTemporaryFile(
            'w', suffix='.json', delete=False, encoding='utf-8'
        )
        json.dump(definition, handle)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def _run(self, definition_path, *args):
        out = StringIO()
        call_command(
            'load_competition', definition_path,
            '--base-dir', LOWRES_DIR, *args, stdout=out, stderr=out,
        )
        return out.getvalue()

    def _txt_path(self, field):
        path = field.name
        if MEDIA_ROOT and MEDIA_ROOT not in path:
            path = str(Path(MEDIA_ROOT) / path)
        return path.replace('.jsonl', '.txt')

    # -- creation --------------------------------------------------------

    def test_creates_competition_and_testsets_inactive(self):
        definition = self._write_definition([
            {'name': 'wmt26lowres-test-mt', 'gold_file': 'ukr_mt_test.gold.jsonl'},
            {'name': 'wmt26lowres-test-qa', 'gold_file': 'ukr_qa_test.gold.jsonl'},
        ])
        output = self._run(definition)

        comp = Competition.objects.get(name=COMP_NAME)
        self.assertFalse(comp.is_active)  # never auto-activated

        testsets = TestSet.objects.filter(competition=comp).order_by('name')
        self.assertEqual(testsets.count(), 2)
        for test_set in testsets:
            self.assertFalse(test_set.is_active)
            self.assertEqual(test_set.file_format, 'JSONL')
            self.assertTrue(test_set.compute_scores)
            self.assertTrue(bool(test_set.src_file))
            self.assertTrue(bool(test_set.ref_file))

        # Reminder to activate is logged.
        self.assertIn('INACTIVE', output)

    def test_is_active_true_activates_objects(self):
        definition = self._write_definition(
            [{
                'name': 'wmt26lowres-test-mt',
                'gold_file': 'ukr_mt_test.gold.jsonl',
                'is_active': True,
            }],
            competition={
                'name': COMP_NAME,
                'description': 'Active competition.',
                'is_active': True,
            },
        )
        output = self._run(definition)

        comp = Competition.objects.get(name=COMP_NAME)
        self.assertTrue(comp.is_active)
        test_set = TestSet.objects.get(name='wmt26lowres-test-mt')
        self.assertTrue(test_set.is_active)
        self.assertIn('ACTIVE', output)

    def test_src_and_ref_txt_are_distinct(self):
        definition = self._write_definition([
            {'name': 'wmt26lowres-test-mt', 'gold_file': 'ukr_mt_test.gold.jsonl'},
        ])
        self._run(definition)

        test_set = TestSet.objects.get(name='wmt26lowres-test-mt')
        # src and ref are stored under different names...
        self.assertNotEqual(test_set.src_file.name, test_set.ref_file.name)

        src_txt = self._txt_path(test_set.src_file)
        ref_txt = self._txt_path(test_set.ref_file)
        self.assertTrue(Path(src_txt).exists())
        self.assertTrue(Path(ref_txt).exists())
        # ...so their .txt companions don't collide: source != reference.
        src_lines = Path(src_txt).read_text(encoding='utf-8').splitlines()
        ref_lines = Path(ref_txt).read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(src_lines), len(ref_lines))
        self.assertTrue(src_lines[0].startswith('Source sentence'))
        self.assertTrue(ref_lines[0].startswith('Target sentence'))

    # -- add to existing competition -------------------------------------

    def test_adds_testsets_to_existing_competition(self):
        first = self._write_definition([
            {'name': 'wmt26lowres-test-mt', 'gold_file': 'ukr_mt_test.gold.jsonl'},
        ])
        self._run(first)

        # Same competition name, a new test set plus the existing one.
        second = self._write_definition([
            {'name': 'wmt26lowres-test-mt', 'gold_file': 'ukr_mt_test.gold.jsonl'},
            {'name': 'wmt26lowres-test-mr', 'gold_file': 'ukr_mr_test.gold.jsonl'},
        ])
        output = self._run(second)

        comp = Competition.objects.get(name=COMP_NAME)
        self.assertEqual(TestSet.objects.filter(competition=comp).count(), 2)
        self.assertIn('skipped existing test set', output)
        self.assertEqual(Competition.objects.filter(name=COMP_NAME).count(), 1)

    # -- dry run ---------------------------------------------------------

    def test_dry_run_persists_nothing(self):
        definition = self._write_definition([
            {'name': 'wmt26lowres-test-mt', 'gold_file': 'ukr_mt_test.gold.jsonl'},
        ])
        output = self._run(definition, '--dry-run')

        self.assertIn('DRY RUN', output)
        self.assertFalse(Competition.objects.filter(name=COMP_NAME).exists())
        self.assertFalse(TestSet.objects.filter(name='wmt26lowres-test-mt').exists())
        self.assertFalse(
            (Path(MEDIA_ROOT) / 'testsets' / 'wmt26lowres-test-mt-src.jsonl').exists()
        )

    # -- validation errors -----------------------------------------------

    def test_missing_gold_file_raises(self):
        definition = self._write_definition([
            {'name': 'wmt26lowres-test-mt', 'gold_file': 'does_not_exist.jsonl'},
        ])
        with self.assertRaises(CommandError):
            self._run(definition)
        self.assertFalse(Competition.objects.filter(name=COMP_NAME).exists())

    def test_new_competition_requires_description(self):
        definition = self._write_definition(
            [{'name': 'wmt26lowres-test-mt', 'gold_file': 'ukr_mt_test.gold.jsonl'}],
            competition={'name': COMP_NAME},  # no description
        )
        with self.assertRaises(CommandError):
            self._run(definition)
