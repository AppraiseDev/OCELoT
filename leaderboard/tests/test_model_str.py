"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for model __str__ / __repr__ representations.
"""
from datetime import datetime

from .common import (
    TestCase, timezone, Language, Competition, TestSet, Team, Submission
)


class ModelStringTests(TestCase):
    """Tests human-readable model representations."""

    def setUp(self):
        self.en = Language.objects.create(code='en', name='English')
        self.de = Language.objects.create(code='de', name='German')

    def test_language_str_and_repr(self):
        self.assertEqual(str(self.en), 'English (en)')
        self.assertEqual(repr(self.en), 'Language(code=en, name=English)')

    def test_competition_str_and_repr(self):
        comp = Competition.objects.create(
            is_active=True,
            name='My Competition',
            description='desc',
            deadline=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(str(comp), 'My Competition')
        self.assertIn('Competition(name=My Competition', repr(comp))

    def test_team_str_and_repr(self):
        team = Team.objects.create(
            is_active=True,
            name='Team Z',
            email='z@team.com',
        )
        self.assertEqual(str(team), 'Team Z (z@team.com)')
        self.assertIn('Team(name=Team Z', repr(team))
        self.assertIn('email=z@team.com', repr(team))

    def test_testset_str_with_languages(self):
        testset = TestSet(
            name='TS One',
            source_language=self.en,
            target_language=self.de,
        )
        self.assertEqual(str(testset), 'TS One test set (en-de)')
        self.assertIn('TestSet(name=TS One', repr(testset))

    def test_testset_str_without_languages(self):
        testset = TestSet(name='Multi TS')
        self.assertEqual(str(testset), 'Multi TS test set (*-*)')
        self.assertIn('source=multi', repr(testset))
        self.assertIn('target=multi', repr(testset))

    def test_submission_repr(self):
        sub = Submission(name='hyp.txt', is_primary=True)
        self.assertEqual(repr(sub), 'Submission(name=hyp.txt, is_primary=True)')
