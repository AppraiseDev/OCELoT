"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.db import models

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

    json_data = models.TextField(
        blank=False, null=True, help_text=('JSON data for test set')
    )

    def __repr__(self):
        return 'TestSet(name={0})'.format(self.name)

    def __str__(self):
        return '{0} test set'.format(self.name)
