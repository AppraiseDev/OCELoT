"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

Team model.
"""
from uuid import uuid4

from django.db import DEFAULT_DB_ALIAS
from django.db import models

from .constants import MAX_DESCRIPTION_LENGTH
from .constants import MAX_NAME_LENGTH
from .constants import MAX_TOKEN_LENGTH
from .validators import validate_institution_name
from .validators import validate_publication_name
from .validators import validate_team_name
from .validators import validate_token


class Team(models.Model):
    """Models a team."""

    is_active = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is active?',
    )

    is_flagged = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is flagged?',
    )

    is_removed = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is removed?',
    )

    is_verified = models.BooleanField(
        blank=False,
        db_index=True,
        default=True,  # make the team verified by default, changed from WMT25
        help_text='Is verified?',
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

    institution_name = models.CharField(
        blank=True,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Institution name (max {0} characters)'.format(
                32
            )  # see validation
        ),
        validators=[validate_institution_name],
    )

    publication_name = models.CharField(
        blank=True,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Team short name (max {0} characters)'.format(
                32
            )  # see validation
        ),
        validators=[validate_publication_name],
    )

    publication_url = models.CharField(
        blank=True,
        max_length=MAX_NAME_LENGTH,
        help_text='Publication URL or citation',
    )

    description = models.TextField(
        blank=True,
        max_length=MAX_DESCRIPTION_LENGTH,
        help_text=(
            'Team description (max {0} characters)'.format(
                MAX_DESCRIPTION_LENGTH
            )
        ),
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

    def _submissions(self):
        from .submission import Submission

        return Submission.objects.filter(submitted_by=self).count()

    def _primary_submissions(self):
        from .submission import Submission

        return Submission.objects.filter(
            submitted_by=self,
            is_primary=True,
        ).count()

    def _compute_token(self):
        token = uuid4().hex[:MAX_TOKEN_LENGTH]
        self.token = token
        self.save()

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
