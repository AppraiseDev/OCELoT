"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for submit() view branches: submission limit, unsupported file
extension and the is_primary checkbox.
"""
import os
from datetime import datetime
from pathlib import Path

from leaderboard.views import MAX_SUBMISSION_LIMIT

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition,
    TestSet, Team, Submission, XML_FILE, TEXT_FILE
)


class SubmitViewBranchTests(TestCase):
    """Tests branches of the submit() view."""

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='ha', name='Hausa')

        ny = datetime.now().year + 1
        self.comp = Competition.objects.create(
            is_active=True,
            name='CompetitionSubmit',
            description='Description',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )

        # No scoring / no length validation: keeps the view branches fast and
        # independent of segment counts.
        self.testset = TestSet.objects.create(
            is_active=True,
            name='TestSetSubmit',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='ha'),
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/sample-src.xml'),
            ref_file=os.path.join(TESTDATA_DIR, 'xml/sample-src-ref.xml'),
            compute_scores=False,
            validate=False,
            competition=self.comp,
        )

        self.team = Team.objects.create(
            is_active=True,
            is_verified=True,
            name='Team Submit',
            email='submit@team.com',
        )

        session = self.client.session
        session['ocelot_team_token'] = self.team.token
        session.save()

    def tearDown(self):
        for fname in ('xml/sample-src.txt', 'xml/sample-src-ref.txt'):
            p = Path(TESTDATA_DIR) / fname
            if p.exists():
                p.unlink()

    def _precreate_submissions(self, count):
        for _ in range(count):
            Submission.objects.create(
                name='xml/sample-hyp.xml',
                original_name='xml/sample-hyp.xml',
                test_set=self.testset,
                submitted_by=self.team,
                file_format=XML_FILE,
                hyp_file=os.path.join(TESTDATA_DIR, 'xml/sample-hyp.xml'),
            )

    def test_submission_limit_is_enforced(self):
        """Posting beyond the submission limit is rejected."""
        self._precreate_submissions(MAX_SUBMISSION_LIMIT)

        with open(os.path.join(TESTDATA_DIR, 'xml/sample-hyp.xml'), encoding='utf8') as f:
            response = self.client.post('/submit', {
                'test_set': self.testset.id,
                'hyp_file': f,
            }, follow=True)

        self.assertContains(response, 'reached the submission limit')
        self.assertEqual(
            Submission.objects.filter(
                submitted_by=self.team, test_set=self.testset
            ).count(),
            MAX_SUBMISSION_LIMIT,
        )

    def test_unsupported_extension_is_rejected(self):
        """Uploading a file with an unsupported extension is rejected."""
        txt = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        with open(os.path.join(TESTDATA_DIR, txt), encoding='utf8') as f:
            response = self.client.post('/submit', {
                'test_set': self.testset.id,
                'hyp_file': f,
            }, follow=True)

        self.assertContains(response, 'error with your submission')
        self.assertEqual(
            Submission.objects.filter(submitted_by=self.team).count(), 0
        )

    def test_is_primary_checkbox_marks_submission_primary(self):
        """Submitting with is_primary checked makes the submission primary."""
        with open(os.path.join(TESTDATA_DIR, 'xml/sample-hyp.xml'), encoding='utf8') as f:
            self.client.post('/submit', {
                'test_set': self.testset.id,
                'hyp_file': f,
                'is_primary': 'on',
            })

        sub = Submission.objects.filter(submitted_by=self.team).first()
        self.assertIsNotNone(sub)
        self.assertTrue(sub.is_primary)
