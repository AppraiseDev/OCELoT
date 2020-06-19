"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from json import loads
from json.decoder import JSONDecodeError
from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS
from django.db import models
from sacrebleu import corpus_bleu  # type: ignore
from sacrebleu import process_to_text  # type: ignore


MAX_CODE_LENGTH = 10  # ISO 639 codes need 3 chars, but better add buffer
MAX_NAME_LENGTH = 200
MAX_TOKEN_LENGTH = 10


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
            self.source_language.code,
            self.target_language.code,
            self.ref_sgml_file.name,
            self.ref_sgml_file.name,
        )

    def __str__(self):
        return '{0} test set ({1}-{2})'.format(
            self.name, self.source_language.code, self.target_language.code
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

    score = models.FloatField(
        blank=True, db_index=True, help_text='SacreBLEU score', null=True
    )

    sgml_file = models.FileField(
        upload_to='submissions',
        help_text='SGML file containing submission output',
        null=True,
    )

    test_set = models.ForeignKey(TestSet, on_delete=models.PROTECT)

    def __repr__(self):
        return 'Submission(name={0}, is_primary={1})'.format(
            self.name, self.is_primary
        )

    def __str__(self):
        _name = self.name if self.is_public else 'Anonymous'
        # pylint: disable=no-member
        return '{0} submission #{1}'.format(_name, self.id)

    def _compute_score(self):
        """Computes sacreBLEU score for current submission."""
        hyp_sgml_path = str(self.sgml_file.name)
        hyp_text_path = hyp_sgml_path.replace('.sgm', '.txt')

        if not Path(hyp_text_path).exists():
            process_to_text(hyp_sgml_path, hyp_text_path)

        ref_sgml_path = self.test_set.ref_sgml_file.name
        ref_text_path = ref_sgml_path.replace('.sgm', '.txt')

        hyp_stream = (x for x in open(hyp_text_path, encoding='utf-8'))
        ref_stream = (r for r in open(ref_text_path, encoding='utf-8'))

        bleu = corpus_bleu(hyp_stream, [ref_stream])

        self.score = bleu.score
        self.save()

    def _score(self):
        """Returns human-readable score."""
        try:
            if not self.score:
                self._compute_score()

            return round(self.score, 1)
        except:
            return '---'

    def _source_language(self):
        """Returns test set source language."""
        return self.test_set.source_language

    def _target_language(self):
        """Returns test set target language."""
        return self.test_set.target_language

    def full_clean(self, exclude=None, validate_unique=True):
        """Validates submission SGML file."""
        sgml_name = str(self.sgml_file.name)
        if not sgml_name.endswith('.sgm'):
            _msg = 'Invalid SGML file named {0}'.format(sgml_name)
            raise ValidationError(_msg)

        sgml_path = Path('submissions') / sgml_name
        if sgml_path.exists():
            _msg = 'Duplicate SGML file named {0}'.format(sgml_path)
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
            'Team name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
    )

    email = models.EmailField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text='Team email',
    )

    token = models.CharField(
        blank=True, db_index=True, max_length=MAX_TOKEN_LENGTH
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
