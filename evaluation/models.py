"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.core.exceptions import ValidationError
from django.db import models

from leaderboard.models import Submission
from leaderboard.models import Team

MAX_CHOICE_LENGTH = 10


class PairwiseRanking(models.Model):
    """Models a pairwise ranking between two submissions at segment level."""

    BETTER = 'A>B'
    WORSE = 'A<B'
    EQUAL = 'A=B'

    RANK_CHOICES = [(BETTER, 'A>B'), (WORSE, 'A<B'), (EQUAL, 'A=B')]

    rank = models.CharField(
        blank=False,
        db_index=True,
        choices=RANK_CHOICES,
        max_length=MAX_CHOICE_LENGTH,
        help_text='Pairwise ranking of segments A and B',
    )

    # Note that Django will not create backward relations in Submissions to
    # this model thanks to related_name='+'.
    submission_A = models.ForeignKey(
        Submission, on_delete=models.PROTECT, related_name='+'
    )
    submission_B = models.ForeignKey(
        Submission, on_delete=models.PROTECT, related_name='+'
    )

    submitted_by = models.ForeignKey(
        Team, on_delete=models.PROTECT, blank=True, null=True
    )

    line_number = models.PositiveIntegerField(
        blank=False, help_text='Line number, 1-based'
    )

    # Segment texts are stored in DB to avoid loosing data if the submission
    # files are removed and to make the export much faster.
    segment_A = models.TextField(blank=False, help_text='Segment A')
    segment_B = models.TextField(blank=False, help_text='Segment B')

    # For the same reasons as above, source and reference segments are also
    # stored in DB, but these are not mandatory.
    src_segment = models.TextField(
        blank=True, null=True, help_text='Source segment'
    )
    ref_segment = models.TextField(
        blank=True, null=True, help_text='Reference segment'
    )

    date_created = models.DateTimeField(
        auto_now_add=True,
        help_text='Creation date of this flag',
        null=True,
    )

    def __repr__(self):
        return 'PairwiseRanking(rank={0}, A={1}, B={2}, line={3}, testset={4})'.format(
            self.rank,
            self.submission_A.name,
            self.submission_B.name,
            self.line_number,
            self.submission_A.test_set.name,
        )

    def __str__(self):
        return self.rank

    def full_clean(self, exclude=None, validate_unique=True):
        """Validates submissions."""

        if self.submission_A.test_set != self.submission_B.test_set:
            _msg = 'Segments A and B must come the same test set'
            raise ValidationError(_msg)

        super().full_clean(
            exclude=exclude, validate_unique=validate_unique
        )

    def get_test_set(self):
        """Returns the test set name."""
        return str(self.submission_A.test_set)

    def _submission_A_name(self):
        """Returns name of submission A."""
        return self.submission_A.name

    def _submission_B_name(self):
        """Returns name of submission B."""
        return self.submission_B.name
