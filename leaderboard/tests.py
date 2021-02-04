"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from datetime import datetime
import os

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from ocelot.settings import BASE_DIR

from leaderboard.models import Competition
from leaderboard.models import Language
from leaderboard.models import SGML_FILE
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet
from leaderboard.models import TEXT_FILE

TESTDATA_DIR = os.path.join(BASE_DIR, 'leaderboard/testdata')


class SubmissionTests(TestCase):
    """Tests Submission model."""

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='de', name='German')

        self.testset = TestSet.objects.create(
            name='TestSetA',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='de'),
            file_format=SGML_FILE,
            src_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-src.en.sgm'
            ),
            ref_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-ref.de.sgm'
            ),
        )

        self.team = Team.objects.create(
            is_active=True,
            name='Team A',
            email='team-a@email.com',
        )

    def test_scores_are_computed_for_a_submission(self):
        """Checks that scores are computed for a submission."""
        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        Submission.objects.create(
            name=_file,
            original_name=_file,
            test_set=self.testset,
            submitted_by=self.team,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, _file),
        )

        sub = Submission.objects.get(name=_file)
        self.assertEqual(round(sub.score, 3), 42.431)
        self.assertEqual(round(sub.score_chrf, 3), 0.664)


class TestSetTests(TestCase):
    """Tests TestSet model."""

    def test_create_test_set_with_sgml_files(self):
        """Checks that a test set can be created from SGML files."""
        TestSet.objects.create(
            name='TestSetA',
            file_format=SGML_FILE,
            src_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-src.en.sgm'
            ),
            ref_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-ref.de.sgm'
            ),
        )

        ts = TestSet.objects.get(name='TestSetA')
        self.assertEqual(ts.name, 'TestSetA')
        self.assertTrue(ts.src_file.name.endswith('.sgm'))
        self.assertTrue(ts.ref_file.name.endswith('.sgm'))

    def test_create_test_set_with_text_files(self):
        """Checks that a test set can be created from text files."""
        TestSet.objects.create(
            name='TestSetB',
            file_format=SGML_FILE,
            src_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-src.en.txt'
            ),
            ref_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-ref.de.txt'
            ),
        )

        ts = TestSet.objects.get(name='TestSetB')
        self.assertEqual(ts.name, 'TestSetB')
        self.assertTrue(ts.src_file.name.endswith('.txt'))
        self.assertTrue(ts.ref_file.name.endswith('.txt'))


class LeaderboardTests(TestCase):
    """Tests leaderboard app."""

    def setUp(self):
        l_en = Language.objects.create(code='en', name='English')
        l_de = Language.objects.create(code='de', name='German')

        _next_year = datetime.now().year + 1
        c1 = Competition.objects.create(
            name='Competition A',
            description='Description of the competition A',
            deadline=datetime(_next_year, 1, 1, tzinfo=timezone.utc),
        )

        ts1 = TestSet.objects.create(
            is_active=True,
            name='TestSet A',
            source_language=l_en,
            target_language=l_de,
            file_format=SGML_FILE,
            src_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-src.en.sgm'
            ),
            ref_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-ref.de.sgm'
            ),
        )
        c1.test_sets.add(ts1)

        t1 = Team.objects.create(
            is_active=True,
            name='Team A',
            email='team-a@email.com',
        )

        _file1 = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        Submission.objects.create(
            name=_file1,
            original_name=_file1,
            test_set=ts1,
            submitted_by=t1,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, _file1),
        )

        t2 = Team.objects.create(
            is_active=True,
            name='Team B',
            email='team-b@email.com',
        )

        _file2 = 'newstest2019.msft-WMT19-sentence-level.6785.en-de.txt'
        Submission.objects.create(
            name=_file2,
            original_name=_file2,
            test_set=ts1,
            submitted_by=t2,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, _file2),
        )

        Competition.objects.create(
            name='Competition B',
            description='Description of the competition B',
            deadline=datetime(_next_year, 1, 12, tzinfo=timezone.utc),
        )

    def test_frontpage_renders_correctly(self):
        """Checks that frontpage renders correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_frontpage_knows_about_competitions(self):
        """Checks that frontpage retrieve list of competitions."""
        response = self.client.get('/')
        self.assertContains(response, 'Competition A')
        self.assertContains(response, 'Competition B')

    def test_leaderboard_renders_correctly_if_competition_exists(self):
        """Checks that leaderboard/<existing-id> renders correctly."""
        comp = Competition.objects.all().first()
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, comp.name)

    def test_leaderboard_renders_404_if_competition_does_not_exist(self):
        """Checks that leaderboard/<non-existing-id> renders 404."""
        response = self.client.get('/leaderboard/1234')
        self.assertEqual(response.status_code, 404)
