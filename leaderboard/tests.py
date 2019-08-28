"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.core.exceptions import ValidationError
from django.test import TestCase


class LeaderboardTests(TestCase):
    """Tests leaderboard app."""

    def test_frontpage_renders_correctly(self):
        """Checks that frontpage renders correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_frontpage_contains_language_test_set_selectors(self):
        """Checks that frontpage contains selectors."""
        response = self.client.get('/')
        expected_selectors = (
            'source_language',
            'target_language',
            'test_set_name',
        )
        self.assertEqual(response.status_code, 200)
        for expected_selector in expected_selectors:
            self.assertContains(response, expected_selector)

    def test_frontpage_knows_about_test_sets(self):
        """Checks that frontpage retrieve list of test sets."""
        from leaderboard.models import Language, TestSet

        _msg = 'Need to implement test for Language and TestSet objects'
        with self.assertRaisesMessage(NotImplementedError, _msg):
            raise NotImplementedError(_msg)

    def test_testset_model_has_name_and_json_data(self):
        """Checks that TestSet model has name and JSON data."""
        from leaderboard.models import TestSet

        _good = TestSet(name='foo', json_data='bar')
        self.assertEqual(_good.name, 'foo')
        self.assertEqual(_good.json_data, 'bar')

    def test_testset_needs_both_name_and_json_data(self):
        """Checks that TestSet model needs both name and JSON data."""
        from leaderboard.models import TestSet

        _bad = TestSet()

        _msg = (
            "{'name': ['This field cannot be blank.'], "
            "'json_data': ['This field cannot be blank.']}"
        )
        with self.assertRaisesMessage(ValidationError, _msg):
            _bad.full_clean()

        _bad.name = 'foo'
        _msg = "{'json_data': ['This field cannot be blank.']}"
        with self.assertRaisesMessage(ValidationError, _msg):
            _bad.full_clean()

        _bad = TestSet()
        _bad.json_data = 'bar'
        _msg = "{'name': ['This field cannot be blank.']}"
        with self.assertRaisesMessage(ValidationError, _msg):
            _bad.full_clean()

        _good = TestSet(name='foo', json_data='bar')
        _good.full_clean()
