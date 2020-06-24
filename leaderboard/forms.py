"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django import forms

from leaderboard.models import MAX_NAME_LENGTH
from leaderboard.models import MAX_TOKEN_LENGTH
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import validate_token


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

    class Meta:  # pylint: disable=too-few-public-methods,missing-docstring
        model = Submission
        fields = ['test_set', 'sgml_file']


class TeamForm(forms.ModelForm):
    """Form used for team signup view."""

    class Meta:  # pylint: disable=too-few-public-methods,missing-docstring
        model = Team
        fields = ['name', 'email']
