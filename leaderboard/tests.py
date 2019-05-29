"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.test import TestCase


class LeaderboardTests(TestCase):
    """Tests leaderboard app."""

    def test_frontpage_renders_correctly(self):
        """Checks that frontpage renders correctly."""
        from leaderboard.views import frontpage  # this will raise
