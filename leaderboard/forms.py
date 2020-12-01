"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django import forms

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
            is_active=True
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
