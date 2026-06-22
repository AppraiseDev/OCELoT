"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

Submission model and its upload-path helper.
"""
import json
import re
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS
from django.db import models
from sacrebleu import corpus_bleu  # type: ignore
from sacrebleu import corpus_chrf  # type: ignore
from sacrebleu.utils import smart_open

from leaderboard.utils import analyze_jsonl_file
from leaderboard.utils import analyze_xml_file
from leaderboard.utils import process_jsonl_to_text
from leaderboard.utils import process_json_to_text
from leaderboard.utils import process_to_text
from leaderboard.utils import process_xml_to_text
from ocelot.settings import MEDIA_ROOT

from .constants import FILE_FORMAT_CHOICES
from .constants import JSON_FILE
from .constants import JSONL_FILE
from .constants import MAX_FORMAT_LENGTH
from .constants import MAX_NAME_LENGTH
from .constants import SGML_FILE
from .constants import TEXT_FILE
from .constants import XML_FILE
from .formats import validate_json_submission
from .formats import validate_jsonl_submission
from .formats import validate_sgml_schema
from .formats import validate_xml_submission
from .team import Team
from .testset import TestSet


def _get_submission_upload_path(instance, filename):
    """Construct upload path based on test set and team data."""
    # Use filename to determine if it's compressed
    is_compressed = filename and filename.endswith('.gz')

    submissions_count = 0
    submissions_for_team = Submission.objects.filter(
        submitted_by=instance.submitted_by.id,
        test_set=instance.test_set,
    )
    if submissions_for_team.exists():
        submissions_count = submissions_for_team.count()

    if instance.file_format == SGML_FILE:
        file_extension = 'sgm'

    elif instance.file_format == XML_FILE:
        file_extension = 'xml'

    elif instance.file_format == JSONL_FILE:
        file_extension = 'jsonl.gz' if is_compressed else 'jsonl'

    elif instance.file_format == JSON_FILE:
        file_extension = 'json.gz' if is_compressed else 'json'

    elif instance.file_format == TEXT_FILE:
        file_extension = 'txt'

    source_code = instance.test_set.source_language.code if instance.test_set.source_language else 'multi'
    target_code = instance.test_set.target_language.code if instance.test_set.target_language else 'multi'

    new_filename = 'submissions/{0}.{1}-{2}.{3}.{4}.{5}'.format(
        instance.test_set.name,
        source_code,
        target_code,
        instance.submitted_by.name,
        submissions_count + 1,
        file_extension,
    )
    new_filename = new_filename.replace(' ', '_').lower()
    return new_filename


class Submission(models.Model):
    """Models a submission."""

    date_created = models.DateTimeField(
        auto_now_add=True,
        null=True,
        help_text='Creation date of this submission',
    )

    is_constrained = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is constrained submission?',
    )

    is_open_source = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is open-source submission?',
    )

    is_contrastive = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is contrastive submission?',
    )

    is_flagged = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is flagged?',
    )

    is_primary = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is primary sumission?',
    )

    is_public = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is publicly visible? '
        'Can be overwritten by settings of the test set or competition',
    )

    is_removed = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is removed?',
    )

    is_valid = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is valid?',
    )

    is_withdrawn = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is withdrawn?',
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Submission name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
    )

    # TODO: This field is not used? Fix or remove.
    original_name = models.CharField(
        blank=False,
        editable=False,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Original file name (max {0} characters)'.format(
                MAX_NAME_LENGTH
            )
        ),
    )

    score = models.FloatField(
        blank=True, db_index=True, help_text='SacreBLEU score', null=True
    )

    score_chrf = models.FloatField(
        blank=True, db_index=True, help_text='chrF score', null=True
    )

    file_format = models.CharField(
        choices=FILE_FORMAT_CHOICES,
        default=XML_FILE,
        max_length=MAX_FORMAT_LENGTH,
    )

    hyp_file = models.FileField(
        upload_to=_get_submission_upload_path,
        help_text='Submission file containing system output',
        null=True,
        validators=[
            validate_sgml_schema,
            validate_xml_submission,
            validate_jsonl_submission,
            validate_json_submission,
        ],
    )

    test_set = models.ForeignKey(TestSet, on_delete=models.PROTECT)

    submitted_by = models.ForeignKey(
        Team, on_delete=models.PROTECT, blank=True, null=True
    )

    def is_anonymous(self):
        """Checks if the submission is not publicly visible, taking into
        account settings at test set and competition levels."""
        # If the submission's test set is a part of a competition and the
        # competition has public visibility set (i.e. is not Unknown)
        if (
            self.test_set.competition
            and self.test_set.competition.is_public is not None
        ):
            return not self.test_set.competition.is_public
        # If the submission's test set has public visibility set (i.e. is not
        # Unknown)
        if self.test_set.is_public is not None:
            return not self.test_set.is_public
        # Otherwise, look at the submission public visibility only
        return not self.is_public

    def __repr__(self):
        return 'Submission(name={0}, is_primary={1})'.format(
            self.name, self.is_primary
        )

    def __str__(self):
        _name = 'Anonymous' if self.is_anonymous() else self.name
        return '{0} submission #{1}'.format(_name, self.id)

    def get_hyp_text(self, path_only=False):
        """Returns a list of hypothesis segments.

        Args:
            path_only (bool): Return a path to the hypothesis file instead of
                a list of hypothesis segments

        Returns:
            list/str: A list of segments unless path_only and a file path
                otherwise
        """

        # later it will throw OSError if the file does not exist
        hyp_path = self.hyp_file.path

        if self.file_format == SGML_FILE:
            if self.test_set.file_format == SGML_FILE:
                hyp_filtered_path = hyp_path.replace(
                    '.sgm', '.filtered.sgm'
                )
                if not Path(hyp_filtered_path).exists():
                    # Get docids from ref SGML path -- these are non "testsuite-"
                    ref_docids = Submission._get_docids_from_path(
                        self.test_set.ref_file.name
                    )

                    # Filter hyp SGML in matching order, skipping testsuite-* docs
                    hyp_filtered_path = Submission._filter_sgml_by_docids(
                        self.hyp_file.name,
                        ref_docids,
                    )
            else:
                hyp_filtered_path = hyp_path

            # Create text version of (possibly filtered) hyp SGML
            hyp_text_path = hyp_filtered_path.replace('.sgm', '.txt')
            if not Path(hyp_text_path).exists():
                process_to_text(hyp_filtered_path, hyp_text_path)

        elif self.file_format == XML_FILE:
            # Use resolved path
            hyp_text_path = hyp_path.replace('.xml', '.txt')
            if not Path(hyp_text_path).exists():
                _, _, _, _, sys_names = analyze_xml_file(hyp_path)
                # There will be no text version if no collection found
                # if self.test_set.collection and self.test_set.collection not in collections:
                # hyp_text_path = None
                # It should never happen that there is no system translations
                # thanks to validation, but better to check
                if len(sys_names) > 0:
                    process_xml_to_text(
                        hyp_path,
                        hyp_text_path,
                        system=sys_names.pop(),
                        collection=self.test_set.collection,
                    )

        elif self.file_format == JSONL_FILE:
            # Use resolved hyp_path
            # Handle both .jsonl and .jsonl.gz files
            if hyp_path.endswith('.jsonl.gz'):
                hyp_text_path = hyp_path.replace('.jsonl.gz', '.txt')
            else:
                hyp_text_path = hyp_path.replace('.jsonl', '.txt')

            if not Path(hyp_text_path).exists():
                output = analyze_jsonl_file(hyp_path)
                sys_names = output.get('systems', [])

                # use the shared JSONL‐to‐text processor
                process_jsonl_to_text(
                    jsonl_path=hyp_path,
                    txt_path=hyp_text_path,
                    system=sys_names.pop() if sys_names else True,
                    collection=self.test_set.collection,
                )

        elif self.file_format == JSON_FILE:
            # Use resolved hyp_path
            # Handle both .json and .json.gz files
            if hyp_path.endswith('.json.gz'):
                hyp_text_path = hyp_path.replace('.json.gz', '.txt')
            else:
                hyp_text_path = hyp_path.replace('.json', '.txt')

            if not Path(hyp_text_path).exists():
                # use the shared JSON‐to‐text processor
                process_json_to_text(
                    json_path=hyp_path,
                    txt_path=hyp_text_path,
                    system=True,  # Extract answers from JSON
                )

        elif self.file_format == TEXT_FILE:
            hyp_text_path = hyp_path

        if path_only:
            return hyp_text_path
        hyp_stream = (r for r in open(hyp_text_path, encoding='utf-8'))
        return hyp_stream


    def get_ref_text(self, path_only=False):
        """Returns a list of reference segments.

        Args:
            path_only (bool): Return a path to the reference file instead of
                a list of hypothesis segments

        Returns:
            list/str: A list of segments unless path_only and a file path
                otherwise
        """
        # Reference file may not exist
        if not self.test_set.has_references():
            return

        if self.test_set.file_format == SGML_FILE:
            # By design, the reference only contains valid docids
            ref_sgml_path = self.test_set.ref_file.name
            ref_text_path = ref_sgml_path.replace('.sgm', '.txt')

        elif self.test_set.file_format == XML_FILE:
            # By design, the reference only contains valid docids
            ref_xml_path = self.test_set.ref_file.name
            ref_text_path = ref_xml_path.replace('.xml', '.txt')

        elif self.test_set.file_format == JSONL_FILE:
            ref_jsonl_path = self.test_set.ref_file.name
            # Handle both .jsonl and .jsonl.gz files
            if ref_jsonl_path.endswith('.jsonl.gz'):
                ref_text_path = ref_jsonl_path.replace('.jsonl.gz', '.txt')
            else:
                ref_text_path = ref_jsonl_path.replace('.jsonl', '.txt')

        elif self.test_set.file_format == JSON_FILE:
            ref_json_path = self.test_set.ref_file.name
            # Handle both .json and .json.gz files
            if ref_json_path.endswith('.json.gz'):
                ref_text_path = ref_json_path.replace('.json.gz', '.txt')
            else:
                ref_text_path = ref_json_path.replace('.json', '.txt')

        elif self.test_set.file_format == TEXT_FILE:
            ref_text_path = self.test_set.ref_file.name

        if MEDIA_ROOT:
            ref_text_path = str(Path(MEDIA_ROOT) / ref_text_path)

        if path_only:
            return ref_text_path
        return (r for r in open(ref_text_path, encoding='utf-8'))

    def get_src_text(self):
        """Returns a list of source segments."""
        if self.test_set.file_format == SGML_FILE:
            src_sgml_path = self.test_set.src_file.name
            src_text_path = src_sgml_path.replace('.sgm', '.txt')

        elif self.test_set.file_format == XML_FILE:
            src_xml_path = self.test_set.src_file.name
            src_text_path = src_xml_path.replace('.xml', '.txt')

        elif self.test_set.file_format == JSONL_FILE:
            src_jsonl_path = self.test_set.src_file.name
            # Handle both .jsonl and .jsonl.gz files
            if src_jsonl_path.endswith('.jsonl.gz'):
                src_text_path = src_jsonl_path.replace('.jsonl.gz', '.txt')
            else:
                src_text_path = src_jsonl_path.replace('.jsonl', '.txt')

        elif self.test_set.file_format == JSON_FILE:
            src_json_path = self.test_set.src_file.name
            # Handle both .json and .json.gz files
            if src_json_path.endswith('.json.gz'):
                src_text_path = src_json_path.replace('.json.gz', '.txt')
            else:
                src_text_path = src_json_path.replace('.json', '.txt')

        elif self.test_set.file_format == TEXT_FILE:
            src_text_path = self.test_set.src_file.name

        if MEDIA_ROOT:
            src_text_path = str(Path(MEDIA_ROOT) / src_text_path)

        src_stream = (r for r in open(src_text_path, encoding='utf-8'))
        return src_stream

    def is_yours(self, ocelot_team_token):
        """Checks if the submission is from the specific team."""
        return (
            ocelot_team_token is not None
            and self.submitted_by.token == ocelot_team_token
        )

    @staticmethod
    def _get_docids_from_path(sgml_path, encoding='utf-8'):
        """Gets list of docids from SGML path."""

        with open(sgml_path, encoding=encoding) as sgml_handle:
            sgml_soup = BeautifulSoup(sgml_handle, 'lxml-xml')

        sgml_docids = []
        sgml_regexp = re.compile('doc', re.IGNORECASE)
        for doc in sgml_soup.find_all(sgml_regexp):
            docid = doc.attrs.get('docid')
            sgml_docids.append(docid)

        return sgml_docids

    @staticmethod
    def _filter_sgml_by_docids(sgml_path, docids, encoding='utf-8'):
        """Creates filtered SGML file which contains only docids."""

        valid_docids = [x.lower() for x in docids]

        with open(sgml_path, encoding=encoding) as sgml_handle:
            sgml_soup = BeautifulSoup(sgml_handle, 'lxml-xml')

        sgml_docs = {}
        sgml_regexp = re.compile('doc', re.IGNORECASE)
        for doc in sgml_soup.find_all(sgml_regexp):
            docid = doc.attrs.get('docid', '').lower()
            if not docid in valid_docids:
                doc.extract()
                continue
            sgml_docs[docid] = doc.extract()

        for docid in valid_docids:
            if docid in sgml_docs.keys() and sgml_soup.tstset:
                sgml_soup.tstset.append(sgml_docs[docid])

        sgml_filtered_path = sgml_path.replace('.sgm', '.filtered.sgm')
        with open(sgml_filtered_path, 'w', encoding=encoding) as out_file:
            out_soup = str(sgml_soup)
            out_soup = out_soup.replace(
                '<?xml version="1.0" encoding="utf-8"?>', ''
            )
            out_file.write(out_soup.strip())

        return sgml_filtered_path

    def _compute_score(self):
        """Computes sacreBLEU scores for current submission."""

        # Reference file may not exist
        if not self.test_set.has_references():
            return

        # Do not compute scores if instructed not to do so
        if not self.test_set.compute_scores:
            return

        tokenize = '13a'
        if self.test_set.target_language:
            target_language_code = self.test_set.target_language.code
            if target_language_code == 'ja':
                # We use char-based tokenizer as MeCab was slow/unstable
                tokenize = 'char'
            elif target_language_code == 'km':
                tokenize = 'char'
            elif target_language_code == 'zh':
                tokenize = 'zh'

        hyp_text_path = self.get_hyp_text(path_only=True)
        ref_text_path = self.get_ref_text(path_only=True)

        try:
            hyp_stream = [x for x in open(hyp_text_path, encoding='utf-8')]
            ref_stream = [r for r in open(ref_text_path, encoding='utf-8')]

            bleu = corpus_bleu(hyp_stream, [ref_stream], tokenize=tokenize)
            self.score = bleu.score

            chrf = corpus_chrf(hyp_stream, [ref_stream])
            self.score_chrf = chrf.score

        except Exception:
            # Don't set score to None, as that would trigger infinite loop
            # TODO: this should provide an error message to the user
            # TODO: the error message should be specific. A simple yet ugly
            # solution would be to use self.score as error codes to propagate
            # the source of the error
            self.score = -1
            self.score_chrf = None

        finally:
            # if this is QA testset, compute accuracy
            if not self.score and "-qa" in self.test_set.name.lower():
                self.score = self._compute_accuracy(hyp_stream, ref_stream)

            if not self.score:  # temporary fix to check if this may prevent infinite loop
                self.score = -2
            if not self.score_chrf:
                self.score_chrf = -2
            self.save()

    def _compute_accuracy(self, hyp_stream, ref_stream):
        """Computes accuracy for QA test sets."""
        correct = 0
        total = 0

        for hyp, ref in zip(hyp_stream, ref_stream):
            hyp = hyp.strip()
            ref = ref.strip()

            if hyp == ref:
                correct += 1
            total += 1

        if total > 0:
            return round((correct / total) * 100, 1)
        return 0.0

    def _score(self):
        """Returns human-readable SacreBLEU score."""
        try:
            if self.score:
                return round(self.score, 1)
            return '---'

        except TypeError:
            return '---'

    def _chrf(self):
        """Returns human-readable chrF score."""
        try:
            if self.score_chrf:
                return round(self.score_chrf, 1)
            return '---'

        except TypeError:
            return '---'

    def _source_language(self):
        """Returns test set source language or None for multi-language test sets."""
        return self.test_set.source_language

    def _target_language(self):
        """Returns test set target language or None for multi-language test sets."""
        return self.test_set.target_language

    def _team_name(self):
        """Returns team publication name if set, or the original name otherwise."""
        return self.submitted_by.publication_name or self.submitted_by.name

    def _validate_hyp_length(self, raise_exception=True):
        """Checks if the hyp file matches the test set's number of segments."""
        try:
            src_segments = len(list(self.get_src_text()))
            hyp_segments = len(list(self.get_hyp_text()))

            if hyp_segments != src_segments:
                if not raise_exception:
                    return False
                raise ValidationError(
                    f"Submission invalid: hyp length ({hyp_segments}) != src segments ({src_segments})"
                )
            return True
        except (OSError, IOError, ValueError):
            # File doesn't exist yet (during full_clean) or other file access issues
            # We'll validate this later in save() when the file is properly saved
            return True if not raise_exception else None

    def _validate_hyp_file_content(self):
        """Validates the content of the uploaded hyp file during full_clean()."""
        if not self.hyp_file:
            return

        # Validate the number of lines for JSONL format: non-empty or same as source
        if self.file_format == JSONL_FILE:
            try:
                # Check if the file is empty
                if self.hyp_file.size == 0:
                    raise ValidationError("Hypothesis file is empty.")

                # Count source lines - handle both compressed and uncompressed
                src_file_name = self.test_set.src_file.name
                if src_file_name.endswith('.jsonl.gz'):
                    # Handle compressed source file
                    if hasattr(self.test_set.src_file, 'temporary_file_path'):
                        src_file_path = self.test_set.src_file.temporary_file_path()
                    else:
                        # For in-memory files, write to temp file first
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl.gz') as temp_file:
                            self.test_set.src_file.seek(0)
                            temp_file.write(self.test_set.src_file.read())
                            src_file_path = temp_file.name

                    with smart_open(src_file_path, 'rt', encoding='utf-8') as f:
                        src_lines = len(f.readlines())
                else:
                    # Handle uncompressed source file
                    self.test_set.src_file.seek(0)
                    src_lines = len(self.test_set.src_file.read().splitlines())

                # Count hypothesis lines - handle both compressed and uncompressed
                hyp_file_name = self.hyp_file.name
                if hyp_file_name.endswith('.jsonl.gz'):
                    # Handle compressed hypothesis file
                    if hasattr(self.hyp_file, 'temporary_file_path'):
                        hyp_file_path = self.hyp_file.temporary_file_path()
                    else:
                        # For in-memory files, write to temp file first
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl.gz') as temp_file:
                            self.hyp_file.seek(0)
                            temp_file.write(self.hyp_file.read())
                            hyp_file_path = temp_file.name

                    with smart_open(hyp_file_path, 'rt', encoding='utf-8') as f:
                        hyp_lines = len(f.readlines())
                else:
                    # Handle uncompressed hypothesis file
                    self.hyp_file.seek(0)
                    hyp_lines = len(self.hyp_file.read().splitlines())

                if hyp_lines != src_lines:
                    raise ValidationError(
                        f"Submission invalid: hyp JSONL lines ({hyp_lines}) != src JSONL lines ({src_lines})"
                    )
            except (OSError, IOError, ValueError):
                # If we can't read the file, skip validation - other validators will catch issues
                return

        # Validate the number of items for JSON format: non-empty or same as source
        elif self.file_format == JSON_FILE:
            try:
                # Check if the file is empty
                if self.hyp_file.size == 0:
                    raise ValidationError("Hypothesis file is empty.")

                # Count source items - handle both compressed and uncompressed
                src_file_name = self.test_set.src_file.name
                if src_file_name.endswith('.json.gz'):
                    # Handle compressed source file
                    if hasattr(self.test_set.src_file, 'temporary_file_path'):
                        src_file_path = self.test_set.src_file.temporary_file_path()
                    else:
                        # For in-memory files, write to temp file first
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.json.gz') as temp_file:
                            self.test_set.src_file.seek(0)
                            temp_file.write(self.test_set.src_file.read())
                            src_file_path = temp_file.name

                    with smart_open(src_file_path, 'rt', encoding='utf-8') as f:
                        src_data = json.load(f)
                        src_items = len(src_data) if isinstance(src_data, list) else 0
                else:
                    # Handle uncompressed source file
                    self.test_set.src_file.seek(0)
                    content = self.test_set.src_file.read()
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    src_data = json.loads(content)
                    src_items = len(src_data) if isinstance(src_data, list) else 0

                # Count hypothesis items - handle both compressed and uncompressed
                hyp_file_name = self.hyp_file.name
                if hyp_file_name.endswith('.json.gz'):
                    # Handle compressed hypothesis file
                    if hasattr(self.hyp_file, 'temporary_file_path'):
                        hyp_file_path = self.hyp_file.temporary_file_path()
                    else:
                        # For in-memory files, write to temp file first
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.json.gz') as temp_file:
                            self.hyp_file.seek(0)
                            temp_file.write(self.hyp_file.read())
                            hyp_file_path = temp_file.name

                    with smart_open(hyp_file_path, 'rt', encoding='utf-8') as f:
                        hyp_data = json.load(f)
                        hyp_items = len(hyp_data) if isinstance(hyp_data, list) else 0
                else:
                    # Handle uncompressed hypothesis file
                    self.hyp_file.seek(0)
                    content = self.hyp_file.read()
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    hyp_data = json.loads(content)
                    hyp_items = len(hyp_data) if isinstance(hyp_data, list) else 0

                if hyp_items != src_items:
                    raise ValidationError(
                        f"Submission invalid: hyp JSON items ({hyp_items}) != src JSON items ({src_items})"
                    )
            except (OSError, IOError, ValueError, json.JSONDecodeError):
                # If we can't read the file, skip validation - other validators will catch issues
                return


    def full_clean(self, exclude=None, validate_unique=True):
        """Validates submission SGML, XML, JSONL, JSON or text file."""
        hyp_name = str(self.hyp_file.name)

        if self.file_format == SGML_FILE:
            if not hyp_name.endswith('.sgm'):
                _msg = 'SGML file name must end with {0}'.format(hyp_name)
                raise ValidationError(_msg)

        elif self.file_format == XML_FILE:
            if not hyp_name.endswith('.xml'):
                _msg = 'XML file name must end with {0}'.format(hyp_name)
                raise ValidationError(_msg)

        elif self.file_format == JSONL_FILE:
            if not (hyp_name.endswith('.jsonl') or hyp_name.endswith('.jsonl.gz')):
                _msg = 'JSONL file name must end with .jsonl or .jsonl.gz, got {0}'.format(hyp_name)
                raise ValidationError(_msg)

        elif self.file_format == JSON_FILE:
            if not (hyp_name.endswith('.json') or hyp_name.endswith('.json.gz')):
                _msg = 'JSON file name must end with .json or .json.gz, got {0}'.format(hyp_name)
                raise ValidationError(_msg)

        elif self.file_format == TEXT_FILE:
            if not hyp_name.endswith('.txt'):
                _msg = 'Text file name must end with {0}'.format(hyp_name)
                raise ValidationError(_msg)

        # Skip validation if the test set has validation disabled
        if self.test_set and self.test_set.validate:
            # Validate hyp file content directly from the uploaded file
            self._validate_hyp_file_content()

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
        """Compute sacreBLEU score on save()."""
        self.is_valid = True
        super().save(force_insert, force_update, using, update_fields)

        # TODO: validate only if TestSet does not have skip_validation set to False

        # Final validation after file is saved with proper path
        if self.id and self.test_set and self.test_set.validate and not self._validate_hyp_length(raise_exception=False):
            self.is_valid = False
            # Save again to update the is_valid flag
            super().save(force_insert=False, force_update=True, using=using, update_fields=['is_valid'])

        if not self.score and self.id:
            self._compute_score()

    def set_primary(self):
        """Make this the primary submission for user/test set."""
        self.is_primary = True
        self.is_contrastive = False
        self.save()

        other_submissions = Submission.objects.filter(
            submitted_by=self.submitted_by,
            test_set=self.test_set,
            is_contrastive=False,  # Leave current contrastive submission as-is
        )
        for other_submission in other_submissions:
            if other_submission.id != self.id:
                other_submission.is_contrastive = False
                other_submission.is_primary = False
                other_submission.save()

    def set_contrastive(self):
        """Make this the contrastive submission for user/test set."""
        if self.is_primary:
            return

        self.is_contrastive = True
        self.save()

        other_submissions = Submission.objects.filter(
            submitted_by=self.submitted_by,
            test_set=self.test_set,
            is_primary=False,  # Leave current primary submission as-is
        )
        for other_submission in other_submissions:
            if other_submission.id != self.id:
                other_submission.is_contrastive = False
                other_submission.is_primary = False
                other_submission.save()

    @property
    def get_name(self):
        """Make __str__() accessible in admin listings."""
        return str(self)
