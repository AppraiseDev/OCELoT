"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import re
from pathlib import Path
from uuid import uuid4

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS
from django.db import models
from sacrebleu.sacrebleu import corpus_bleu  # type: ignore
from sacrebleu.sacrebleu import process_to_text  # type: ignore


MAX_CODE_LENGTH = 10  # ISO 639 codes need 3 chars, but better add buffer
MAX_NAME_LENGTH = 200
MAX_TOKEN_LENGTH = 10


def validate_team_name(value):
    """Validates team name matches r'^[a-zA-Z0-9_\\- ]{2,32}$'."""
    valid_name = re.compile(r'^[a-zA-Z0-9_\- ]{2,32}$')
    if not valid_name.match(value):
        _msg = 'Team name must match regexp r"^[a-zA-Z0-9_\\- ]{2,32}$"'
        raise ValidationError(_msg)


def validate_token(value):
    """Validates token matches r'[a-f0-9]{10}'."""
    valid_token = re.compile(r'[a-f0-9]{10}')
    if not valid_token.match(value):
        _msg = 'Team name must match regexp r"[a-f0-9]{10}"'
        raise ValidationError(_msg)


class Language(models.Model):
    """Models a language."""

    code = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_CODE_LENGTH,
        help_text=(
            'ISO 639 code (max {0} characters)'.format(MAX_CODE_LENGTH)
        ),
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Test set name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
    )

    def __repr__(self):
        return 'Language(code={0}, name={1})'.format(self.code, self.name)

    def __str__(self):
        return '{0} ({1})'.format(self.name, self.code)


class TestSet(models.Model):
    """Models a test set."""

    is_active = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is active test set?',
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
    )

    target_language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name='target_language_set',
        null=True,
    )

    ref_sgml_file = models.FileField(
        upload_to='testsets',
        help_text='SGML file containing test set reference text',
        null=True,
    )

    src_sgml_file = models.FileField(
        upload_to='testsets',
        help_text='SGML file containing test set source text',
        null=True,
    )

    def __repr__(self):
        return 'TestSet(name={0}, source={1}, target={2}, src={3}, ref={4})'.format(
            self.name,
            self.source_language.code,  # pylint: disable=no-member
            self.target_language.code,  # pylint: disable=no-member
            self.ref_sgml_file.name,
            self.ref_sgml_file.name,
        )

    def __str__(self):
        return '{0} test set ({1}-{2})'.format(
            self.name,
            self.source_language.code,  # pylint: disable=no-member
            self.target_language.code,  # pylint: disable=no-member
        )

    def _create_text_files(self):
        """Creates test set text files."""
        for sgml_file in (self.ref_sgml_file, self.src_sgml_file):
            sgml_path = str(sgml_file.name)

            text_path = sgml_path.replace('.sgm', '.txt')
            if not Path(text_path).exists():
                process_to_text(sgml_path, text_path)

    def full_clean(self, exclude=None, validate_unique=True):
        """Validates test set SGML files."""
        for sgml_file in (self.ref_sgml_file, self.src_sgml_file):
            sgml_path = str(sgml_file.name)

            if not sgml_path.endswith('.sgm'):
                _msg = 'Invalid SGML file name {0}'.format(sgml_path)
                raise ValidationError(_msg)

        super().full_clean(
            exclude=exclude, validate_unique=validate_unique
        )

    # pylint: disable=no-member,bad-continuation
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


class Team(models.Model):
    """Models a team."""

    is_active = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is active team?',
    )

    is_verified = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is verified team?',
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Team name (max {0} characters)'.format(32)  # see validation
        ),
        unique=True,
        validators=[validate_team_name],
    )

    email = models.EmailField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text='Team email',
    )

    token = models.CharField(
        blank=True,
        db_index=True,
        max_length=MAX_TOKEN_LENGTH,
        unique=True,
        validators=[validate_token],
    )

    def __repr__(self):
        return 'Team(name={0}, email={1}, token={2})'.format(
            self.name, self.email, self.token
        )

    def __str__(self):
        return '{0} ({1})'.format(self.name, self.email)

    def _compute_token(self):
        token = uuid4().hex[:MAX_TOKEN_LENGTH]
        self.token = token
        self.save()

    # pylint: disable=no-member,bad-continuation
    def save(
        self,
        force_insert=False,
        force_update=False,
        using=DEFAULT_DB_ALIAS,
        update_fields=None,
    ):
        """Compute token on save()."""
        super().save(force_insert, force_update, using, update_fields)
        if not self.token and self.id:
            self._compute_token()


def _get_submission_upload_path(instance, filename):
    """Construct upload path based on test set and team data."""
    del filename  # not used

    submissions_count = 0
    submissions_for_team = Submission.objects.filter(  # pylint: disable=no-member
        submitted_by=instance.submitted_by.id, test_set=instance.test_set
    )
    if submissions_for_team.exists():
        submissions_count = submissions_for_team.count()

    new_filename = 'submissions/{0}.{1}-{2}.{3}.{4}.sgm'.format(
        instance.test_set.name,
        instance.test_set.source_language.code,
        instance.test_set.target_language.code,
        instance.submitted_by.name,
        submissions_count + 1,
    )
    new_filename.replace(' ', '_').lower()

    return new_filename


class Submission(models.Model):
    """Models a submission."""

    date_created = models.DateTimeField(
        auto_now_add=True,
        null=True,
        help_text='Creation date of this submission',
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
        help_text='Is publicly visible?',
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Submission name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
    )

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

    sgml_file = models.FileField(
        upload_to=_get_submission_upload_path,
        help_text='SGML file containing submission output',
        null=True,
    )

    test_set = models.ForeignKey(TestSet, on_delete=models.PROTECT)

    submitted_by = models.ForeignKey(
        Team, on_delete=models.PROTECT, blank=True, null=True
    )

    def __repr__(self):
        return 'Submission(name={0}, is_primary={1})'.format(
            self.name, self.is_primary
        )

    def __str__(self):
        _name = self.name if self.is_public else 'Anonymous'
        # pylint: disable=no-member
        return '{0} submission #{1}'.format(_name, self.id)

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
        """Computes sacreBLEU score for current submission."""

        # Get docids from ref SGML path -- these are non "testsuite-"
        ref_docids = Submission._get_docids_from_path(
            self.test_set.ref_sgml_file.name  # pylint: disable=no-member
        )

        # Filter hyp SGML in matching order, skipping testsuite-* docs
        hyp_filtered_path = Submission._filter_sgml_by_docids(
            self.sgml_file.name, ref_docids  # pylint: disable=no-member
        )

        # Create text version of filtered hyp SGML
        hyp_text_path = hyp_filtered_path.replace('.sgm', '.txt')
        if not Path(hyp_text_path).exists():
            process_to_text(hyp_filtered_path, hyp_text_path)

        # By design, the reference only contains valid docids
        ref_sgml_path = (
            self.test_set.ref_sgml_file.name  # pylint: disable=no-member
        )
        ref_text_path = ref_sgml_path.replace('.sgm', '.txt')

        hyp_stream = (x for x in open(hyp_text_path, encoding='utf-8'))
        ref_stream = (r for r in open(ref_text_path, encoding='utf-8'))

        try:
            bleu = corpus_bleu(hyp_stream, [ref_stream])
            self.score = bleu.score

        except EOFError:
            self.score = None

        finally:
            self.save()

    def _score(self):
        """Returns human-readable score."""
        try:
            if self.score:
                return round(self.score, 1)

        except TypeError:
            return '---'

    def _source_language(self):
        """Returns test set source language."""
        return self.test_set.source_language  # pylint: disable=no-member

    def _target_language(self):
        """Returns test set target language."""
        return self.test_set.target_language  # pylint: disable=no-member

    def full_clean(self, exclude=None, validate_unique=True):
        """Validates submission SGML file."""
        sgml_name = str(self.sgml_file.name)
        if not sgml_name.endswith('.sgm'):
            _msg = 'Invalid SGML file named {0}'.format(sgml_name)
            raise ValidationError(_msg)

        #        sgml_path = Path('submissions') / sgml_name
        #        if sgml_path.exists():
        #            _msg = 'Duplicate SGML file named {0}'.format(sgml_path)
        #            raise ValidationError(_msg)

        super().full_clean(
            exclude=exclude, validate_unique=validate_unique
        )

    # pylint: disable=no-member,bad-continuation
    def save(
        self,
        force_insert=False,
        force_update=False,
        using=DEFAULT_DB_ALIAS,
        update_fields=None,
    ):
        # def save(self, *args, **kwargs):
        """Compute sacreBLEU score on save()."""
        # super().save(*args, **kwargs)
        super().save(force_insert, force_update, using, update_fields)
        if not self.score and self.id:
            self._compute_score()

    @property
    def get_name(self):
        """Make __str__() accessible in admin listings."""
        return str(self)
