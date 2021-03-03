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
    """Form used for teampage view.  """

    publication_name = forms.CharField(
        max_length=MAX_NAME_LENGTH,
        validators=[validate_team_name],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class SigninForm(forms.Form):
    """Form used for sign-in view.

    Based on forms.Form as we don't want to create a new Team.
    """

    name = forms.CharField(
        label='Team name',
        max_length=MAX_NAME_LENGTH,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    token = forms.CharField(
        label='Token',
        max_length=MAX_TOKEN_LENGTH,
        validators=[validate_token],
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )


class SubmissionForm(forms.ModelForm):
    """Form used for submission view."""

    # Prevent submissions to inactive test sets and test sets from inactive
    # competitions by not showing them as available choices in the submission form.
    #
    # Support competitions with no deadline or start time. Note that lazy
    # querysets should take care of combining OR filters into a single query.
    #
    # TODO: Consider showing competition + test set in the select box, not just
    # the test set name
    test_set = forms.ModelChoiceField(
        queryset=TestSet.objects.filter(
            is_active=True,
            competition__is_active=True,
            competition__deadline__gt=datetime.now(tz=timezone.utc),
            competition__start_time__lt=datetime.now(tz=timezone.utc),
        )
        | TestSet.objects.filter(
            is_active=True,
            competition__is_active=True,
            competition__deadline__isnull=True,
            competition__start_time__lt=datetime.now(tz=timezone.utc),
        )
        | TestSet.objects.filter(
            is_active=True,
            competition__is_active=True,
            competition__deadline__gt=datetime.now(tz=timezone.utc),
            competition__start_time__isnull=True,
        )
        | TestSet.objects.filter(
            is_active=True,
            competition__is_active=True,
            competition__deadline__isnull=True,
            competition__start_time__isnull=True,
        ),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:  # pylint: disable=too-few-public-methods,missing-docstring
        model = Submission
        fields = ['test_set', 'file_format', 'hyp_file']
        widgets = {
            'file_format': forms.Select(attrs={'class': 'form-control'}),
            'hyp_file': forms.FileInput(
                attrs={'class': 'form-control form-control-file'}
            ),
        }


class TeamForm(forms.ModelForm):
    """Form used for team signup view."""

    class Meta:  # pylint: disable=too-few-public-methods,missing-docstring
        model = Team
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.TextInput(attrs={'class': 'form-control'}),
        }
