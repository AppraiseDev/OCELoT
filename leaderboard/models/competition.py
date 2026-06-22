"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

Competition model.
"""
from django.db import models

from .constants import MAX_DESCRIPTION_LENGTH
from .constants import MAX_NAME_LENGTH


class Competition(models.Model):
    """Models a competition."""

    is_active = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is active competition?',
    )

    # True or False overrides the setting from TestSet and Submission.
    # Set to None to fallback to TestSet.is_public
    is_public = models.BooleanField(
        blank=True,
        db_index=True,
        default=None,
        help_text='Are submissions publicly visible? '
        'Overwrites settings in test sets and submissions unless Unknown',
        null=True,
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        help_text=(
            'Competition name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
        max_length=MAX_NAME_LENGTH,
        unique=True,
    )

    description = models.TextField(
        blank=False,
        help_text=(
            'Competition description (max {0} characters)'.format(
                MAX_DESCRIPTION_LENGTH
            )
        ),
        max_length=MAX_DESCRIPTION_LENGTH,
    )

    # Date and time when the competition starts
    start_time = models.DateTimeField(
        blank=True,
        help_text='Competition start time (an empty value means no start time)',
        null=True,
    )

    # Date and time when the competition ends
    deadline = models.DateTimeField(
        blank=True,
        help_text='Competition deadline (an empty value means no deadline)',
        null=True,
    )

    def __repr__(self):
        return (
            'Competition(name={0}, start_time={1}, deadline={2})'.format(
                self.name, self.start_time, self.deadline
            )
        )

    def __str__(self):
        return self.name
