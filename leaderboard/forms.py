"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from datetime import datetime

from django import forms
from django.utils import timezone

from leaderboard.models import FILE_FORMAT_CHOICES
from leaderboard.models import MAX_DESCRIPTION_LENGTH
from leaderboard.models import MAX_NAME_LENGTH
from leaderboard.models import MAX_TOKEN_LENGTH
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet
from leaderboard.models import validate_institution_name
from leaderboard.models import validate_publication_name
from leaderboard.models import validate_token


PLACEHOLDER_FOR_DESCRIPTION = """TEAM-ONE submission is a standard Transformer
model equipped with our recent technique of problem obfuscation
\\citep{obfuscation:2021}. The best improvement was achieved thanks to doubly
obfuscating both source and target side and mixing in our manually obfuscated
set of examples.

@inproceedings{obfuscation:2021,
  title  = {Amazing Obfuscation of NMT Problems},
  author = ...
}"""


class PublicationNameForm(forms.Form):
    """Form used for teampage view.

    Based on forms.Form as we don't want to create a new Team.
    """

    institution_name = forms.CharField(
        max_length=MAX_NAME_LENGTH,
        validators=[validate_institution_name],
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': r'Institution Team \textsc{ONE}',
            }
        ),
        label='Institution name',
    )
    publication_name = forms.CharField(
        max_length=MAX_NAME_LENGTH,
        validators=[validate_publication_name],
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'TEAM-ONE'}
        ),
        label='Short team name',
    )


class PublicationDescriptionForm(forms.Form):
    """Form used for teampage view.

    Based on forms.Form as we don't want to create a new Team.
    """

    publication_url = forms.CharField(
        max_length=MAX_NAME_LENGTH,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'John Doe, Jack Smith: TeamOneMT at Translation Task',
            }
        ),
        label='System paper',
    )
    description = forms.CharField(
        max_length=MAX_DESCRIPTION_LENGTH,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 7,
                'placeholder': PLACEHOLDER_FOR_DESCRIPTION,
            }
        ),
        label='Paragraph for the overview paper',
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

    file_format = forms.ChoiceField(
        choices=FILE_FORMAT_CHOICES,
        widget=forms.Select(
            attrs={'class': 'form-control', 'disabled': 'disabled'}
        ),
    )

    hyp_file = forms.FileField(
        widget=forms.FileInput(
            attrs={'class': 'form-control form-control-file'},
        ),
        help_text="XML file containing submission output",
    )

    class Meta:  # pylint: disable=too-few-public-methods,missing-docstring
        model = Submission
        fields = ['test_set', 'file_format', 'hyp_file', 'is_primary']


class TeamForm(forms.ModelForm):
    """Form used for team signup view."""

    class Meta:  # pylint: disable=too-few-public-methods,missing-docstring
        model = Team
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.TextInput(attrs={'class': 'form-control'}),
        }
