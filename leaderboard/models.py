"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from json import loads
from json.decoder import JSONDecodeError
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS
from django.db import models
from sacrebleu.sacrebleu import corpus_bleu  # type: ignore
from sacrebleu.sacrebleu import process_to_text  # type: ignore


MAX_CODE_LENGTH = 10  # ISO 639 codes need 3 chars, but better add buffer
MAX_NAME_LENGTH = 200


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

    source_language = model.ForeignKey(Language, on_delete=models.PROTECT)

    target_language = model.ForeignKey(Language, on_delete=models.PROTECT)

    sgml_file = models.FileField(
        upload_to='testsets',
        help_text='SGML file containing test set',
        null=True,
    )

    def __repr__(self):
        return 'TestSet(name={0}, source={1}, target={2}, sgml={3})'.format(
            self.name,
            self.source_language.code,
            self.target_language.code,
            self.sgml_file.name,
        )

    def __str__(self):
        return '{0} test set'.format(self.name)

    def full_clean(self, exclude=None, validate_unique=True):
        """Validates test set JSON data."""
        if isinstance(self.json_data, (str, bytes, bytearray)):
            try:
                _unused = loads(self.json_data)

            except JSONDecodeError:
                raise ValidationError('This field contains invalid JSON.')

        super().full_clean(
            exclude=exclude, validate_unique=validate_unique
        )


class Submission(models.Model):
    """Models a submission."""

    is_primary = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is primary sumission?',
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Test set name (max {0} characters)'.format(MAX_NAME_LENGTH)
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
        _name = self.name if self.is_primary else 'Anonymous'
        # pylint: disable=no-member
        return '{0} submission #{1}'.format(_name, self.id)

    def _compute_score(self):
        """Computes sacreBLEU score for current submission."""

        sgml_path = str(self.sgml_file.name)
        text_path = sgml_path.replace('.sgm', '.txt')
        ref_path = 'testsets/wmt18.ende.ref.txt'

        if not Path(text_path).exists():
            process_to_text(sgml_path, text_path)

        hyp_stream = (x for x in open(text_path, encoding='utf-8'))
        ref_stream = (r for r in open(ref_path, encoding='utf-8'))

        bleu = corpus_bleu(hyp_stream, [ref_stream])

        self.score = bleu.score
        self.save()

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
