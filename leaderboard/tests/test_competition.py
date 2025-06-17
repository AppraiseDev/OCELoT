"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Competition model tests.
"""
from .common import TestCase, Competition


class CompetitionTests(TestCase):
    """Tests Competition model."""

    def test_creating_competition_with_no_start_time_and_deadline(self):
        """Checks a competition with no start time and deadline."""
        comp = Competition.objects.create(
            is_active=True,
            name='CompetitionNoStartTime',
            description='Description',
        )
        self.assertIsNone(comp.start_time)
        self.assertIsNone(comp.deadline)
