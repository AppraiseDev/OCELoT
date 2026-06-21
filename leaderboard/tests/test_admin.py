"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for admin actions in the admin panel.
"""
import json
from io import BytesIO
from zipfile import ZipFile

from leaderboard.admin import _make_submission_filename
from leaderboard.admin import download_submission_files
from leaderboard.admin import download_testset_files

from .common import TestCase, _create_team_json, Team, Submission, TestSet
from .test_leaderboard import LeaderboardTests


class AdminActionsTests(LeaderboardTests):
    """Tests for admin actions in the admin panel."""

    @staticmethod
    def _zip_names(response):
        """Returns the list of file names inside a zipped FileResponse."""
        content = b''.join(response.streaming_content)
        with ZipFile(BytesIO(content)) as zf:
            return zf.namelist()

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

    def test_download_submission_files(self):
        """Admin can download a zip of all submission files."""
        response = download_submission_files(None, None, Submission.objects.all())
        names = self._zip_names(response)
        self.assertEqual(len(names), Submission.objects.count())

    def test_download_testset_files(self):
        """Admin can download a zip of test set source and reference files."""
        response = download_testset_files(None, None, TestSet.objects.all())
        names = self._zip_names(response)
        # The single test set has both a source and a reference file
        self.assertEqual(len(names), 2)

    def test_make_submission_filename(self):
        """A readable submission filename is built from test set metadata."""
        subm = Submission.objects.first()
        filename = _make_submission_filename(subm)
        self.assertTrue(filename.startswith('submissions/'))
        self.assertIn('en-de', filename)
        self.assertTrue(filename.endswith('.txt'))
        self.assertNotIn(' ', filename)

