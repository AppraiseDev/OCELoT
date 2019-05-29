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
