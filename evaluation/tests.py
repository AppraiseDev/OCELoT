"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import os
from datetime import datetime

from django.test import TestCase
from django.utils import timezone

from leaderboard.models import Competition
from leaderboard.models import Language
from leaderboard.models import SGML_FILE
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet
from leaderboard.models import TEXT_FILE
from ocelot.settings import BASE_DIR

TESTDATA_DIR = os.path.join(BASE_DIR, 'leaderboard/testdata')


class ComparisonTests(TestCase):
    """Tests submission output comparison."""

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='de', name='German')

        _next_year = datetime.now().year + 1
        self.competition = Competition.objects.create(
            is_active=True,
            name='MyCompetition',
            description='Description of the competition',
            deadline=datetime(_next_year, 1, 1, tzinfo=timezone.utc),
        )

        testset = TestSet.objects.create(
            is_active=True,
            name='MyTestSet',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='de'),
            file_format=SGML_FILE,
            src_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-src.en.sgm'
            ),
            ref_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-ref.de.sgm'
            ),
            competition=self.competition,
        )

        self.team_a = Team.objects.create(
            is_active=True,
            name='Team A',
            email='team-a@email.com',
        )

        file_1 = 'newstest2019.msft-WMT19-sentence-level.6785.en-de.txt'
        self.sub_1 = Submission.objects.create(
            name=file_1,
            test_set=testset,
            submitted_by=self.team_a,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, file_1),
        )

        self.team_b = Team.objects.create(
            is_active=True,
            name='Team B',
            email='team-b@email.com',
        )

        file_2 = 'newstest2019.msft-WMT19-sentence_document.6974.en-de.txt'
        self.sub_2 = Submission.objects.create(
            name=file_2,
            test_set=testset,
            submitted_by=self.team_b,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, file_2),
        )

        session = self.client.session
        session['ocelot_team_token'] = self.team_a.token
        session.save()

    def test_non_public_submissions_cannot_be_compared(self):
        """Checks that compare/a/b/ do not render for submissions that are not public."""
        self.sub_1.is_public = False  # Note sub_1 is submitted by team_a
        self.sub_1.save()
        self.sub_2.is_public = False  # Note sub_2 is submitted by team_b
        self.sub_2.save()
        response = self.client.get(
            '/compare/{0}/{1}'.format(self.sub_1.id, self.sub_2.id),
            follow=True,
        )
        self.assertContains(response, 'cannot be compared')
        self.assertContains(response, 'must be public')

    def test_submissions_from_different_test_sets_cannot_be_compared(self):
        """Checks that compare/a/b/ do not render for submissions from different test sets."""

        testset = TestSet.objects.create(
            is_active=True,
            name='AnotherTestSet',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='de'),
            file_format=SGML_FILE,
            src_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-src.en.sgm'
            ),
            ref_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-ref.de.sgm'
            ),
            competition=self.competition,
        )

        _file = 'newstest2019.msft-WMT19-sentence-level.6785.en-de.txt'
        sub_3 = Submission.objects.create(
            name=_file,
            test_set=testset,
            submitted_by=self.team_a,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, _file),
            is_public=True,
        )

        self.sub_1.is_public = True
        self.sub_1.save()

        response = self.client.get(
            '/compare/{0}/{1}'.format(self.sub_1.id, sub_3.id),
            follow=True,
        )
        self.assertContains(response, 'cannot be compared')
        self.assertContains(response, 'the same test set')

    def test_comparing_submissions_renders(self):
        """Checks that compare/a/b/ renders submission names and diff spans."""
        self.sub_1.is_public = True
        self.sub_1.save()
        self.sub_2.is_public = True
        self.sub_2.save()
        response = self.client.get(
            '/compare/{0}/{1}'.format(self.sub_1.id, self.sub_2.id)
        )
        self.assertContains(response, str(self.sub_1))
        self.assertContains(response, str(self.sub_2))
        self.assertContains(response, '<span class="diff')
