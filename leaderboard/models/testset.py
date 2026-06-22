"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

TestSet model.
"""
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS
from django.db import models

from leaderboard.utils import analyze_jsonl_file
from leaderboard.utils import analyze_xml_file
from leaderboard.utils import process_jsonl_to_text
from leaderboard.utils import process_json_to_text
from leaderboard.utils import process_to_text
from leaderboard.utils import process_xml_to_text
from ocelot.settings import MEDIA_ROOT

from .competition import Competition
from .constants import FILE_FORMAT_CHOICES
from .constants import JSON_FILE
from .constants import JSONL_FILE
from .constants import MAX_FORMAT_LENGTH
from .constants import MAX_NAME_LENGTH
from .constants import SGML_FILE
from .constants import TEXT_FILE
from .constants import XML_FILE
from .formats import validate_json_ref_testset
from .formats import validate_json_src_testset
from .formats import validate_jsonl_ref_testset
from .formats import validate_jsonl_src_testset
from .formats import validate_xml_ref_testset
from .formats import validate_xml_src_testset
from .language import Language


class TestSet(models.Model):
    """Models a test set."""

    is_active = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is active test set?',
    )

    # True or False overrides the setting from Submission.
    # Set to None to fallback to Submission.is_public
    is_public = models.BooleanField(
        blank=True,
        db_index=True,
        default=None,
        help_text='Are submissions publicly visible? '
        'Overwrite settings from submissions unless Unknown',
        null=True,
    )

    compute_scores = models.BooleanField(
        blank=False,
        db_index=True,
        default=True,
        help_text='Compute automatic scores?',
    )

    validate = models.BooleanField(
        blank=False,
        db_index=True,
        default=True,
        help_text='Validate submissions for this test set? Set to False to skip validation',
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Test set name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
    )

    source_language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name='source_language_set',
        null=True,
        blank=True,
        help_text='Source language (optional for multi-language test sets)',
    )

    target_language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name='target_language_set',
        null=True,
        blank=True,
        help_text='Target language (optional for multi-language test sets)',
    )

    file_format = models.CharField(
        choices=FILE_FORMAT_CHOICES,
        default=XML_FILE,
        max_length=MAX_FORMAT_LENGTH,
    )

    src_file = models.FileField(
        blank=True,
        upload_to='testsets',
        help_text='XML, JSONL (optionally compressed as .jsonl.gz), JSON (optionally compressed as .json.gz) or text file containing test set source',
        null=True,
        validators=[
            validate_xml_src_testset,
            validate_jsonl_src_testset,
            validate_json_src_testset,
        ],
    )

    ref_file = models.FileField(
        blank=True,
        upload_to='testsets',
        help_text='XML, JSONL (optionally compressed as .jsonl.gz), JSON (optionally compressed as .json.gz) or text file containing test set reference(s)',
        null=True,
        validators=[
            validate_xml_ref_testset,
            validate_jsonl_ref_testset,
            validate_json_ref_testset,
        ],
    )

    competition = models.ForeignKey(
        Competition,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='test_sets',
        related_query_name='test_sets',
    )

    # If a collection ID is provided, automatic scores are computed only on the
    # data from that collection
    collection = models.CharField(
        blank=True,
        null=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Optional collection name (max {0} characters)'.format(
                MAX_NAME_LENGTH
            )
        ),
    )

    def __repr__(self):
        source_code = self.source_language.code if self.source_language else 'multi'
        target_code = self.target_language.code if self.target_language else 'multi'
        return 'TestSet(name={0}, source={1}, target={2}, src={3}, ref={4}, collection={5})'.format(
            self.name,
            source_code,
            target_code,
            self.src_file.name,
            self.ref_file.name,
            self.collection,
        )

    def __str__(self):
        source_code = self.source_language.code if self.source_language else '*'
        target_code = self.target_language.code if self.target_language else '*'
        return '{0} test set ({1}-{2})'.format(
            self.name,
            source_code,
            target_code,
        )

    def _create_text_files(self):
        """
        Creates test set text files from SGML, XML, JSONL or JSON files.
        If files are already in text format, do nothing.
        For XML/JSONL/JSON formats, it extracts data only from the collection if defined.
        """
        if self.file_format == TEXT_FILE:
            return

        if self.file_format == SGML_FILE:
            for sgml_file in (self.ref_file, self.src_file):
                sgml_path = str(sgml_file.name)
                text_path = sgml_path.replace('.sgm', '.txt')
                if not Path(text_path).exists():
                    process_to_text(sgml_path, text_path)

        elif self.file_format == XML_FILE:
            # Extract source text
            src_path = str(self.src_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in src_path:
                src_path = str(Path(MEDIA_ROOT) / src_path)

            txt_path = src_path.replace('.xml', '.txt')

            if not Path(txt_path).exists():
                # After validation it's guaranteed that src_langs has only one element
                _, src_langs, _, _, _ = analyze_xml_file(src_path)
                process_xml_to_text(
                    src_path,
                    txt_path,
                    source=src_langs.pop(),
                    collection=self.collection,
                )

            if not self.has_references():  # Reference file may not exist
                return

            # Extract reference texts; multiple references will be tab-separated
            ref_path = str(self.ref_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in ref_path:
                ref_path = str(Path(MEDIA_ROOT) / ref_path)
            txt_path = ref_path.replace('.xml', '.txt')

            if not Path(txt_path).exists():
                _, _, _, translators, _ = analyze_xml_file(ref_path)
                # Sort to guarantee reproducibility
                # Scores will be computed against the first reference only
                translator = sorted(list(translators))[0]
                process_xml_to_text(
                    ref_path,
                    txt_path,
                    reference=translator,
                    collection=self.collection,
                )

        elif self.file_format == JSONL_FILE:
            # Extract source text
            src_path = str(self.src_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in src_path:
                src_path = str(Path(MEDIA_ROOT) / src_path)
            # Handle both .jsonl and .jsonl.gz files
            if src_path.endswith('.jsonl.gz'):
                txt_src = src_path.replace('.jsonl.gz', '.txt')
            else:
                txt_src = src_path.replace('.jsonl', '.txt')

            # use the shared JSONL‐to‐text processor
            process_jsonl_to_text(
                jsonl_path=src_path,
                txt_path=txt_src,
                source=True,
                collection=self.collection,
            )

            if not self.has_references():
                return

            # Extract reference texts
            ref_path = str(self.ref_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in ref_path:
                ref_path = str(Path(MEDIA_ROOT) / ref_path)
            # Handle both .jsonl and .jsonl.gz files
            if ref_path.endswith('.jsonl.gz'):
                txt_ref = ref_path.replace('.jsonl.gz', '.txt')
            else:
                txt_ref = ref_path.replace('.jsonl', '.txt')

            # pick first translator for reference extraction
            translators = analyze_jsonl_file(ref_path).get('translators', [])
            translator = sorted(translators)[0] if translators else None

            process_jsonl_to_text(
                jsonl_path=ref_path,
                txt_path=txt_ref,
                reference=translator,
                collection=self.collection,
            )

        elif self.file_format == JSON_FILE:
            # Extract source text
            src_path = str(self.src_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in src_path:
                src_path = str(Path(MEDIA_ROOT) / src_path)
            # Handle both .json and .json.gz files
            if src_path.endswith('.json.gz'):
                txt_src = src_path.replace('.json.gz', '.txt')
            else:
                txt_src = src_path.replace('.json', '.txt')

            # use the shared JSON‐to‐text processor
            process_json_to_text(
                json_path=src_path,
                txt_path=txt_src,
                source=True,
            )

            if not self.has_references():
                return

            # Extract reference texts
            ref_path = str(self.ref_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in ref_path:
                ref_path = str(Path(MEDIA_ROOT) / ref_path)
            # Handle both .json and .json.gz files
            if ref_path.endswith('.json.gz'):
                txt_ref = ref_path.replace('.json.gz', '.txt')
            else:
                txt_ref = ref_path.replace('.json', '.txt')

            process_json_to_text(
                json_path=ref_path,
                txt_path=txt_ref,
                system=True,  # Extract answers as references
            )

        # if we reach here, file_format was neither TEXT, SGML, XML, JSONL nor JSON…
        return

    def has_references(self):
        """Returns True when self.ref_file is not None."""
        return bool(self.ref_file)

    def full_clean(self, exclude=None, validate_unique=True):
        """Validates test set files."""
        for current_file in (self.ref_file, self.src_file):
            if not self.has_references():  # Reference file may not exist
                continue

            current_path = str(current_file.name)

            if self.file_format == SGML_FILE:
                if not current_path.endswith('.sgm'):
                    _msg = 'Invalid SGML file name {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

            elif self.file_format == XML_FILE:
                if not current_path.endswith('.xml'):
                    _msg = 'Invalid XML file named {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

                # TODO: Validate that a collection (if requested) is present in
                # the XML file. Do it here or in validate_xml_submission()

            elif self.file_format == JSONL_FILE:
                if not (current_path.endswith('.jsonl') or current_path.endswith('.jsonl.gz')):
                    _msg = 'Invalid JSONL file name {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

            elif self.file_format == JSON_FILE:
                if not (current_path.endswith('.json') or current_path.endswith('.json.gz')):
                    _msg = 'Invalid JSON file name {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

            elif self.file_format == TEXT_FILE:
                if not current_path.endswith('.txt'):
                    _msg = 'Invalid text file name {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

        super().full_clean(
            exclude=exclude, validate_unique=validate_unique
        )

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=DEFAULT_DB_ALIAS,
        update_fields=None,
    ):
        """Creates test set text files on save()."""
        super().save(force_insert, force_update, using, update_fields)
        if self.id:
            self._create_text_files()
