"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from datetime import datetime

from django import forms
from django.utils import timezone

from leaderboard.models import MAX_NAME_LENGTH
from leaderboard.models import MAX_TOKEN_LENGTH
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet
from leaderboard.models import validate_team_name
from leaderboard.models import validate_token


class PublicationNameForm(forms.Form):
    """Form used for teampage view.

    Based on forms.Form as we don't want to create a new Team.
    """

    publication_name = forms.CharField(
        max_length=MAX_NAME_LENGTH,
        validators=[validate_team_name],
    )


class SigninForm(forms.Form):
    """Form used for sign-in view.

    Based on forms.Form as we don't want to create a new Team.
    """

    name = forms.CharField(max_length=MAX_NAME_LENGTH)
    email = forms.EmailField()
    token = forms.CharField(
        max_length=MAX_TOKEN_LENGTH,
        validators=[validate_token],
        widget=forms.PasswordInput(),
    )


class SubmissionForm(forms.ModelForm):
    """Form used for submission view."""

    test_set = forms.ModelChoiceField(
        queryset=TestSet.objects.filter(  # pylint: disable=no-member
            # Prevent submissions to inactive test sets and test sets from
            # inactive competitions by not displaying them as options in
            # the submission form. Note that this is an imperfect solution,
            # and a better one might be disallowing this in the view.
            is_active=True,
            competition__is_active=True,
            competition__deadline__gt=datetime.now(tz=timezone.utc),
            # TODO: consider showing competition + test set in the select box,
            # not just the test set name
        )
    )

    class Meta:  # pylint: disable=too-few-public-methods,missing-docstring
        model = Submission
        fields = ['test_set', 'file_format', 'hyp_file']


class TeamForm(forms.ModelForm):
    """Form used for team signup view."""

    class Meta:  # pylint: disable=too-few-public-methods,missing-docstring
        model = Team
        fields = ['name', 'email']
