"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from datetime import datetime
from json import loads
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from leaderboard.models import Competition
from leaderboard.models import TestSet


class LeaderboardTests(TestCase):
    """Tests leaderboard app."""

    def setUp(self):
        Competition.objects.create(
            name='Competition no. 1',
            description='Description of the competition no. 1',
            deadline=datetime(2021, 1, 1, 12, 30, tzinfo=timezone.utc),
        )
        Competition.objects.create(
            name='Competition no. 2',
            description='Description of the competition no. 2',
            deadline=datetime(2021, 1, 2, 12, 30, tzinfo=timezone.utc),
        )

    def test_frontpage_renders_correctly(self):
        """Checks that frontpage renders correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_frontpage_knows_about_competitions(self):
        """Checks that frontpage retrieve list of competitions."""
        response = self.client.get('/')
        self.assertContains(response, 'Competition no. 1')
        self.assertContains(response, 'Competition no. 2')

    def test_leaderboard_renders_correctly_if_competition_exists(self):
        """Checks that leaderboard/<existing-id> renders correctly."""
        comp = Competition.objects.all().first()
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Competition no. 1')

    def test_leaderboard_renders_404_if_competition_does_not_exist(self):
        """Checks that leaderboard/<non-existing-id> renders 404."""
        response = self.client.get('/leaderboard/1234')
        self.assertEqual(response.status_code, 404)
