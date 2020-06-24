from django import forms
from django.core.exceptions import ValidationError

from leaderboard.models import MAX_NAME_LENGTH
from leaderboard.models import MAX_TOKEN_LENGTH
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet


def _validate_token(value):
    if len(value) != MAX_TOKEN_LENGTH:
        raise ValidationError('Invalid token')

    valid_token_chars = ['a', 'b', 'c', 'd', 'e', 'f']
    valid_token_chars.extend([str(x) for x in range(10)])

    for char in value:
        if char.lower() not in valid_token_chars:
            raise ValidationError('Invalid token')


class SigninForm(forms.Form):
    name = forms.CharField(max_length=MAX_NAME_LENGTH)
    email = forms.EmailField()
    token = forms.CharField(
        max_length=MAX_TOKEN_LENGTH, validators=[_validate_token]
    )


class OldSubmissionForm(forms.Form):
    email = forms.EmailField()
    token = forms.CharField(
        max_length=MAX_TOKEN_LENGTH, validators=[_validate_token]
    )
    test_set = forms.ModelChoiceField(queryset=TestSet.objects.all())
    sgml_file = forms.FileField()


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['test_set', 'sgml_file']


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'email']
