"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for field validators and publication/sign-in forms.
"""
from django.test import SimpleTestCase

from leaderboard.forms import PublicationDescriptionForm
from leaderboard.forms import PublicationNameForm
from leaderboard.forms import SigninForm
from leaderboard.models import ValidationError
from leaderboard.models import validate_institution_name
from leaderboard.models import validate_publication_name
from leaderboard.models import validate_team_name
from leaderboard.models import validate_token


class ValidatorTests(SimpleTestCase):
    """Tests model field validators."""

    def test_validate_team_name_accepts_valid(self):
        for value in ('Team One', 'ab', 'a-b_c 1'):
            validate_team_name(value)  # should not raise

    def test_validate_team_name_rejects_invalid(self):
        for value in ('a', 'x' * 33, 'bad@name', ''):
            with self.assertRaises(ValidationError):
                validate_team_name(value)

    def test_validate_institution_name_accepts_latin(self):
        validate_institution_name('Institut')

    def test_validate_institution_name_rejects_non_latin(self):
        for value in ('日本語', 'a', 'x' * 33):
            with self.assertRaises(ValidationError):
                validate_institution_name(value)

    def test_validate_publication_name_accepts_valid(self):
        for value in ('TEAM-1.0', 'team_one', 'A.B-C'):
            validate_publication_name(value)

    def test_validate_publication_name_rejects_invalid(self):
        for value in ('has space', 'a', 'bad/name'):
            with self.assertRaises(ValidationError):
                validate_publication_name(value)

    def test_validate_token_accepts_valid(self):
        validate_token('abcdef0123')

    def test_validate_token_rejects_invalid(self):
        for value in ('ABCDEF0123', 'xyz', 'ghijklmnop'):
            with self.assertRaises(ValidationError):
                validate_token(value)


class FormTests(SimpleTestCase):
    """Tests sign-in and publication forms."""

    def test_signin_form_valid(self):
        form = SigninForm(data={
            'name': 'Team One',
            'email': 'team@one.com',
            'token': 'abcdef0123',
        })
        self.assertTrue(form.is_valid())

    def test_signin_form_invalid_token(self):
        form = SigninForm(data={
            'name': 'Team One',
            'email': 'team@one.com',
            'token': 'NOT-HEX!!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('token', form.errors)

    def test_publication_name_form_valid(self):
        form = PublicationNameForm(data={
            'institution_name': 'Institution',
            'publication_name': 'TEAM-ONE',
        })
        self.assertTrue(form.is_valid())

    def test_publication_name_form_invalid_name(self):
        form = PublicationNameForm(data={
            'institution_name': 'Institution',
            'publication_name': 'team one',  # space not allowed
        })
        self.assertFalse(form.is_valid())
        self.assertIn('publication_name', form.errors)

    def test_publication_description_form_requires_fields(self):
        form = PublicationDescriptionForm(data={
            'publication_url': '',
            'description': '',
        })
        self.assertFalse(form.is_valid())
