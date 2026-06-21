"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for the teampage view (sign-in guard, primary/contrastive selection,
withdrawal and publication info updates).
"""
import os
from datetime import datetime

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition,
    TestSet, Team, Submission, TEXT_FILE
)


class TeampageTests(TestCase):
    """Tests the teampage view."""

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='de', name='German')

        ny = datetime.now().year + 1
        self.comp = Competition.objects.create(
            is_active=True,
            name='CompetitionTP',
            description='Description',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )

        self.testset = TestSet.objects.create(
            is_active=True,
            name='TestSetTP',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='de'),
            file_format=TEXT_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'newstest2019-ende-src.en.txt'),
            ref_file=None,
            compute_scores=False,
            validate=False,
            competition=self.comp,
        )

        self.team = Team.objects.create(
            is_active=True,
            is_verified=True,
            name='Team TP',
            email='tp@team.com',
        )

        self.hyp = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        self.sub1 = self._make_submission()
        self.sub2 = self._make_submission()

    def _make_submission(self):
        return Submission.objects.create(
            name=self.hyp,
            original_name=self.hyp,
            test_set=self.testset,
            submitted_by=self.team,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, self.hyp),
        )

    def _signin(self):
        session = self.client.session
        session['ocelot_team_token'] = self.team.token
        session.save()

    def _reload(self, sub):
        return Submission.objects.get(id=sub.id)

    def test_teampage_requires_signin(self):
        """Anonymous users are redirected away from the team page."""
        response = self.client.get('/teampage', follow=True)
        self.assertContains(response, 'need to be signed in')

    def test_teampage_renders_for_signed_in_team(self):
        """A signed-in team sees the team page with its test set."""
        self._signin()
        response = self.client.get('/teampage')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.testset))

    def test_teampage_auto_selects_default_primary(self):
        """If no primary is chosen, one is auto-selected on render."""
        self._signin()
        self.client.get('/teampage')
        primaries = Submission.objects.filter(
            submitted_by=self.team, is_primary=True
        )
        self.assertEqual(primaries.count(), 1)

    def test_teampage_post_sets_primary_constrained(self):
        """Posting a primary selection updates flags accordingly."""
        self._signin()
        self.client.post('/teampage', {
            'primary': self.sub1.id,
            'primary_constrained': 'constrained',
        })
        sub1 = self._reload(self.sub1)
        self.assertTrue(sub1.is_primary)
        self.assertTrue(sub1.is_constrained)
        self.assertTrue(sub1.is_open_source)

    def test_teampage_post_sets_contrastive(self):
        """Posting primary + contrastive selections sets both."""
        self._signin()
        self.client.post('/teampage', {
            'primary': self.sub1.id,
            'primary_constrained': 'closed',
            'contrastive': self.sub2.id,
            'contrastive_constrained': 'open',
        })
        sub1 = self._reload(self.sub1)
        sub2 = self._reload(self.sub2)
        self.assertTrue(sub1.is_primary)
        self.assertTrue(sub2.is_contrastive)
        self.assertTrue(sub2.is_open_source)

    def test_teampage_post_withdraw(self):
        """Posting a withdrawal flags the test set's submissions."""
        self._signin()
        self.client.post('/teampage', {
            'testset': self.testset.id,
            'withdrawn': '1',
        })
        self.assertTrue(self._reload(self.sub1).is_withdrawn)
        self.assertTrue(self._reload(self.sub2).is_withdrawn)

    def test_teampage_post_updates_publication_info(self):
        """Posting publication info updates the team record."""
        self._signin()
        response = self.client.post('/teampage', {
            'institution_name': 'Institution',
            'publication_name': 'TEAM-X',
            'publication_url': 'TEAM-X at WMT',
            'description': 'A short system description.',
        })
        team = Team.objects.get(id=self.team.id)
        self.assertEqual(team.institution_name, 'Institution')
        self.assertEqual(team.publication_name, 'TEAM-X')
        self.assertEqual(team.publication_url, 'TEAM-X at WMT')
        self.assertEqual(team.description, 'A short system description.')
        self.assertContains(response, 'successfully updated publication')
