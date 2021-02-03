"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from json import loads
from pathlib import Path
from datetime import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from leaderboard.models import Competition
from leaderboard.models import TestSet


class LeaderboardTests(TestCase):
    """Tests leaderboard app."""

    def test_frontpage_renders_correctly(self):
        """Checks that frontpage renders correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_frontpage_knows_about_competitions(self):
        """Checks that frontpage retrieve list of test sets."""

        _msg = 'Need to implement test for Language and TestSet objects'
        with self.assertRaisesMessage(NotImplementedError, _msg):
            raise NotImplementedError(_msg)


class CompetitionTests(TestCase):
    """Tests Competition model."""

    def setUp(self):
        Competition.objects.create(
            name='Competition no. 1',
            description='Description of the competition no. 1',
            deadline=datetime(2021, 1, 1, 12, 30, tzinfo=timezone.utc),
        )

    def test_competition_renders_correctly_if_competition_exists(self):
        """Checks that competitions/<existing-id> renders correctly."""
        comp = Competition.objects.all().first()
        response = self.client.get('/competition/{0}'.format(comp.id))
        self.assertEqual(response.status_code, 200)

    def test_competition_renders_404_if_competition_does_not_exist(self):
        """Checks that competitions/<non-existing-id> renders correctly."""
        response = self.client.get('/competition/1234')
        self.assertEqual(response.status_code, 404)
