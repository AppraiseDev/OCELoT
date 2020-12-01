"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from json import loads
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import TestCase

from leaderboard.models import TestSet


class LeaderboardTests(TestCase):
    """Tests leaderboard app."""

    def test_frontpage_renders_correctly(self):
        """Checks that frontpage renders correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_frontpage_knows_about_test_sets(self):
        """Checks that frontpage retrieve list of test sets."""

        _msg = 'Need to implement test for Language and TestSet objects'
        with self.assertRaisesMessage(NotImplementedError, _msg):
            raise NotImplementedError(_msg)
