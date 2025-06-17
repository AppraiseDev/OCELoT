"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for admin actions in the admin panel.
"""
import json

from .common import TestCase, _create_team_json, Team, Submission
from .test_leaderboard import LeaderboardTests


class AdminActionsTests(LeaderboardTests):
    """Tests for admin actions in the admin panel."""

    def test_download_team_file(self):
        """Checks that admin can download team files."""
        # Set primary submission
        subm = Submission.objects.first()
        subm.is_primary = True
        subm.save()
        # Get team JSON file
        team_file = _create_team_json(Team.objects.all())
        team_json = json.loads(team_file)

        # Check if the number of teams in the JSON file is the same as in the database
        self.assertEqual(len(team_json), Team.objects.count())
        # Check if the first submission has one primary submission
        self.assertEqual(len(team_json[0]['primary_submissions']), 1)
        # Check if the second submission has no primary submissions
        self.assertEqual(len(team_json[1]['primary_submissions']), 0)

        for data in team_json:
            for key in ["name", "institution_name", "publication_name"]:
                self.assertTrue(key in data)
