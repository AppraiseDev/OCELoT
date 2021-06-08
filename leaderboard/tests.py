"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import os
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from django.test import TestCase
from django.utils import timezone

from leaderboard.models import Competition
from leaderboard.models import Language
from leaderboard.models import SGML_FILE
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet
from leaderboard.models import TEXT_FILE
from leaderboard.models import XML_FILE
from ocelot.settings import BASE_DIR

TESTDATA_DIR = os.path.join(BASE_DIR, 'leaderboard/testdata')


class SubmissionTests(TestCase):
    """Tests Submission model."""

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='de', name='German')

        _next_year = datetime.now().year + 1
        self.competition = Competition.objects.create(
            is_active=True,
            name='CompetitionA',
            description='Description of the competition A',
            deadline=datetime(_next_year, 1, 1, tzinfo=timezone.utc),
        )

        self.testset = TestSet.objects.create(
            is_active=True,
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
            competition=self.competition,
        )

        self.team = Team.objects.create(
            is_active=True,
            name='Team A',
            email='team-a@email.com',
        )

    def _set_ocelot_team_token(self):
        """Set the team token to be able to render the submission form."""
        session = self.client.session
        session['ocelot_team_token'] = self.team.token
        session.save()

    def _make_submission(self, file_name, file_format=TEXT_FILE):
        """Makes a submission."""
        return Submission.objects.create(
            name=file_name,
            original_name=file_name,
            test_set=self.testset,
            submitted_by=self.team,
            file_format=file_format,
            hyp_file=os.path.join(TESTDATA_DIR, file_name),
        )

    def test_scores_are_computed_for_submission_in_text_format(self):
        """Checks that scores are computed for a submission."""
        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        self._make_submission(_file)
        sub = Submission.objects.get(name=_file)

        self.assertEqual(round(sub.score, 3), 42.431)
        self.assertEqual(round(sub.score_chrf, 3), 0.664)

    def test_scores_are_computed_for_submission_in_sgml_format(self):
        """Checks that scores are computed for a submission."""
        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.sgm'
        self._make_submission(_file, SGML_FILE)
        sub = Submission.objects.get(name=_file)

        self.assertEqual(round(sub.score, 3), 42.431)
        self.assertEqual(round(sub.score_chrf, 3), 0.664)

    def test_inactive_testsets_are_not_shown(self):
        """Checks that inactive test sets are not shown in the submission form."""
        self._set_ocelot_team_token()

        tst = TestSet.objects.get(name='TestSetA')
        tst.is_active = False
        tst.save()

        response = self.client.get('/submit')
        self.assertNotContains(response, tst.name)

    def test_inactive_campaigns_are_not_shown(self):
        """Checks that test sets from inactive campaigns are not shown in the submission form."""
        self._set_ocelot_team_token()

        comp = Competition.objects.get(name='CompetitionA')
        comp.is_active = False
        comp.save()

        response = self.client.get('/submit')
        self.assertNotContains(response, comp.test_sets.first().name)

    def test_campaigns_past_deadline_are_not_shown(self):
        """
        Checks that test sets from campaigns past the deadline are not shown in
        the submission form.
        """
        self._set_ocelot_team_token()

        comp = Competition.objects.get(name='CompetitionA')
        # Timestamp with an hour back
        comp.deadline = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        comp.save()

        response = self.client.get('/submit')
        self.assertNotContains(response, comp.test_sets.first().name)

    def test_campaigns_that_has_not_started_are_not_shown(self):
        """
        Checks that test sets from campaigns that has not started yet are not
        shown in the submission form.
        """
        self._set_ocelot_team_token()

        comp = Competition.objects.get(name='CompetitionA')
        comp.start_time = datetime.now(tz=timezone.utc) + timedelta(
            hours=1
        )
        comp.save()

        response = self.client.get('/submit')
        self.assertNotContains(response, comp.test_sets.first().name)

    def test_successfull_submission(self):
        """Checks that a successfull submission displays message about the success."""
        self._set_ocelot_team_token()

        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        with open(os.path.join(TESTDATA_DIR, _file)) as tst:
            data = {
                'test_set': '1',
                'file_format': 'TEXT',
                'hyp_file': tst,
            }
            response = self.client.post('/submit', data, follow=True)
        self.assertContains(response, 'successfully submitted')
        self.assertNotContains(response, 'submission has closed')

    def test_submission_is_anonymous(self):
        """Checks that a submission is anonymous by default."""
        self._set_ocelot_team_token()

        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        sub = self._make_submission(_file)
        self.assertIn('Anonymous', str(sub))

        comp = sub.test_set.competition
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertContains(response, 'Anonymous submission #')

    def test_submission_can_be_public(self):
        """Checks that submission can be made publicly visible."""
        self._set_ocelot_team_token()

        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        sub = self._make_submission(_file)
        sub.is_public = True
        sub.save()
        self.assertNotIn('Anonymous', str(sub))

        comp = sub.test_set.competition
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertContains(response, _file)
        self.assertNotContains(response, 'Anonymous submission #')

    def test_submission_is_anonymous_if_testset_is_not_public(self):
        """Checks that submission is not publicly visible if the test set is not public."""
        self._set_ocelot_team_token()

        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        sub = self._make_submission(_file)
        sub.is_public = True
        sub.save()
        self.assertNotIn('Anonymous', str(sub))

        tst = sub.test_set
        tst.is_public = False
        tst.save()
        self.assertIn('Anonymous', str(sub))

        comp = sub.test_set.competition
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertContains(response, 'Anonymous submission #')

    def test_submission_is_anonymous_if_competition_is_not_public(self):
        """Checks that submission is not publicly visible if the competition is not public."""
        self._set_ocelot_team_token()

        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        sub = self._make_submission(_file)
        sub.is_public = True
        sub.save()
        self.assertNotIn('Anonymous', str(sub))

        tst = sub.test_set
        tst.is_public = True
        tst.save()
        self.assertNotIn('Anonymous', str(sub))

        comp = sub.test_set.competition
        comp.is_public = False
        comp.save()
        self.assertIn('Anonymous', str(sub))

        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertContains(response, 'Anonymous submission #')

    def test_submission_is_public_if_competition_is_public(self):
        """Checks that submission is publicly visible if the test set or the
        competition are set to be publicly visible."""
        self._set_ocelot_team_token()

        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        sub = self._make_submission(_file)
        sub.is_public = False
        sub.save()
        self.assertIn('Anonymous', str(sub))

        tst = sub.test_set
        tst.is_public = True
        tst.save()
        self.assertNotIn('Anonymous', str(sub))

        comp = sub.test_set.competition
        comp.is_public = True
        comp.save()
        self.assertNotIn('Anonymous', str(sub))

        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertContains(response, _file)
        self.assertNotContains(response, 'Anonymous submission #')


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

        tst = TestSet.objects.get(name='TestSetA')
        self.assertEqual(tst.name, 'TestSetA')
        self.assertTrue(tst.src_file.name.endswith('.sgm'))
        self.assertTrue(tst.ref_file.name.endswith('.sgm'))

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

        tst = TestSet.objects.get(name='TestSetB')
        self.assertEqual(tst.name, 'TestSetB')
        self.assertTrue(tst.src_file.name.endswith('.txt'))
        self.assertTrue(tst.ref_file.name.endswith('.txt'))

    def test_create_test_set_with_xml_files(self):
        """Checks that a test set can be created from XML files."""

        TestSet.objects.create(
            name='TestSetC',
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/sample-src.xml'),
            ref_file=os.path.join(TESTDATA_DIR, 'xml/sample-src-ref.xml'),
        )

        tst = TestSet.objects.get(name='TestSetC')
        self.assertEqual(tst.name, 'TestSetC')
        self.assertTrue(tst.src_file.name.endswith('.xml'))
        self.assertTrue(tst.ref_file.name.endswith('.xml'))

        # Check if text files has been created and are non empty
        src_txt_file = Path(tst.src_file.name.replace('.xml', '.txt'))
        ref_txt_file = Path(tst.ref_file.name.replace('.xml', '.txt'))
        self.assertTrue(src_txt_file.exists())
        self.assertTrue(ref_txt_file.exists())
        self.assertTrue(src_txt_file.stat().st_size > 0)
        self.assertTrue(ref_txt_file.stat().st_size > 0)

        # Clean up created files
        src_txt_file.unlink()
        ref_txt_file.unlink()


class CompetitionTests(TestCase):
    """Tests Competition model."""

    def test_creating_competition_with_no_start_time_and_deadline(self):
        """Checks a competition with no start time and deadline."""
        comp = Competition.objects.create(
            is_active=True,
            name='CompetitionNoStartTime',
            description='Description',
        )
        self.assertIsNone(comp.start_time)
        self.assertIsNone(comp.deadline)


class LeaderboardTests(TestCase):
    """Tests leaderboard app."""

    def setUp(self):
        l_en = Language.objects.create(code='en', name='English')
        l_de = Language.objects.create(code='de', name='German')

        _next_year = datetime.now().year + 1
        comp_a = Competition.objects.create(
            is_active=True,
            name='Competition A',
            description='Description of the competition A',
            deadline=datetime(_next_year, 1, 1, tzinfo=timezone.utc),
        )

        test_a = TestSet.objects.create(
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
            competition=comp_a,
        )

        team_a = Team.objects.create(
            is_active=True,
            name='Team A',
            email='team-a@email.com',
        )

        _file1 = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        Submission.objects.create(
            name=_file1,
            original_name=_file1,
            test_set=test_a,
            submitted_by=team_a,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, _file1),
        )

        team_b = Team.objects.create(
            is_active=True,
            name='Team B',
            email='team-b@email.com',
        )

        _file2 = 'newstest2019.msft-WMT19-sentence-level.6785.en-de.txt'
        Submission.objects.create(
            name=_file2,
            original_name=_file2,
            test_set=test_a,
            submitted_by=team_b,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, _file2),
        )

        Competition.objects.create(
            is_active=True,
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

    def test_frontpage_does_not_show_inactive_competitions(self):
        """Checks that frontpage retrieve list of competitions."""
        comp = Competition.objects.get(name='Competition A')
        comp.is_active = False
        comp.save()
        response = self.client.get('/')
        self.assertNotContains(response, 'Competition A')
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

    def test_leaderboard_is_not_shown_for_inactive_competition(self):
        """Checks that leaderboard/<inactive-competition-id> redirects to the frontpage."""
        comp = Competition.objects.get(name='Competition A')
        comp.is_active = False
        comp.save()
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertEqual(response.status_code, 302)

    def test_leaderboard_shows_competition_description(self):
        """Checks that leaderboard contains description of the competition."""
        comp = Competition.objects.get(name='Competition A')
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertContains(response, comp.description)

    def test_leaderboard_without_submissions(self):
        """Checks that leaderboard without submissions shows no submissions."""
        comp = Competition.objects.get(name='Competition B')
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertNotContains(response, 'Anonymous submission #')
        self.assertContains(response, 'No submissions')

    def test_leaderboard_with_submissions(self):
        """Checks that leaderboard with submissions shows submissions."""
        comp = Competition.objects.get(name='Competition A')
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        # Get all submissions to this campaign
        subs = Submission.objects.filter(test_set__competition=comp)
        for sub in subs:
            self.assertContains(response, str(sub))
        self.assertNotContains(response, 'No submissions')
