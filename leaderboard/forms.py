from django import forms
from django.core.exceptions import ValidationError

from leaderboard.models import MAX_TOKEN_LENGTH, TestSet


def validate_token(value):
    if len(value) != MAX_TOKEN_LENGTH:
        raise ValidationError('Invalid token')

    valid_token_chars = ['a', 'b', 'c', 'd', 'e', 'f']
    valid_token_chars.extend([str(x) for x in range(10)])

    for char in value:
        if char.lower() not in valid_token_chars:
            raise ValidationError('Invalid token')


class SubmissionForm(forms.Form):
    email = forms.EmailField()
    token = forms.CharField(
        max_length=MAX_TOKEN_LENGTH, validators=[validate_token]
    )
    all_test_sets = ((x.id, str(x)) for x in TestSet.objects.all())
    test_set = forms.ChoiceField(choices=all_test_sets)
    sgml_file = forms.FileField()
