"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for Submission.set_primary() and set_contrastive() selection logic.
"""
import os
from datetime import datetime

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition,
    TestSet, Team, Submission, TEXT_FILE
)


class PrimaryContrastiveTests(TestCase):
    """Tests primary/contrastive submission selection."""

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='de', name='German')

        ny = datetime.now().year + 1
        self.comp = Competition.objects.create(
            is_active=True,
            name='CompetitionPC',
            description='Description',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )

        # No scoring and no validation: we only care about the flag logic.
        self.testset = TestSet.objects.create(
            is_active=True,
            name='TestSetPC',
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
            name='Team PC',
            email='pc@team.com',
        )

        self.hyp = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        self.sub1 = self._make_submission()
        self.sub2 = self._make_submission()
        self.sub3 = self._make_submission()

    def _make_submission(self):
        return Submission.objects.create(
            name=self.hyp,
            original_name=self.hyp,
            test_set=self.testset,
            submitted_by=self.team,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, self.hyp),
        )

    def _reload(self, sub):
        return Submission.objects.get(id=sub.id)

    def test_set_primary_marks_submission(self):
        """set_primary() flags the submission as primary, not contrastive."""
        self.sub1.set_primary()
        sub1 = self._reload(self.sub1)
        self.assertTrue(sub1.is_primary)
        self.assertFalse(sub1.is_contrastive)

    def test_set_primary_demotes_previous_primary(self):
        """Only one submission stays primary per team/test set."""
        self.sub1.set_primary()
        self.sub2.set_primary()
        self.assertFalse(self._reload(self.sub1).is_primary)
        self.assertTrue(self._reload(self.sub2).is_primary)

    def test_set_primary_clears_its_own_contrastive_flag(self):
        """Promoting a contrastive submission to primary clears contrastive."""
        self.sub1.set_contrastive()
        self.assertTrue(self._reload(self.sub1).is_contrastive)
        self.sub1.set_primary()
        sub1 = self._reload(self.sub1)
        self.assertTrue(sub1.is_primary)
        self.assertFalse(sub1.is_contrastive)

    def test_set_contrastive_marks_submission(self):
        """set_contrastive() flags the submission as contrastive."""
        self.sub2.set_contrastive()
        self.assertTrue(self._reload(self.sub2).is_contrastive)

    def test_set_contrastive_is_noop_for_primary_submission(self):
        """A primary submission cannot also become contrastive."""
        self.sub1.set_primary()
        self.sub1.set_contrastive()
        sub1 = self._reload(self.sub1)
        self.assertTrue(sub1.is_primary)
        self.assertFalse(sub1.is_contrastive)

    def test_only_one_contrastive_at_a_time(self):
        """Setting a new contrastive submission clears the previous one."""
        self.sub2.set_contrastive()
        self.sub3.set_contrastive()
        self.assertFalse(self._reload(self.sub2).is_contrastive)
        self.assertTrue(self._reload(self.sub3).is_contrastive)

    def test_set_primary_keeps_existing_contrastive(self):
        """Choosing a primary submission leaves the contrastive one intact."""
        self.sub2.set_contrastive()
        self.sub1.set_primary()
        self.assertTrue(self._reload(self.sub1).is_primary)
        self.assertTrue(self._reload(self.sub2).is_contrastive)
