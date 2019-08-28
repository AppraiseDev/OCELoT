"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
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

    def test_testset_model_has_name_and_json_data(self):
        """Checks that TestSet model has name and JSON data."""
        from .models import TestSet
        a = TestSet(name='foo', json_data='bar')
        self.assertEqual(a.name, 'foo')
        self.assertEqual(a.json_data, 'bar')
