"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Submission model tests for testsets in SGML and TEXT formats.
"""
import os
from datetime import datetime
from datetime import timedelta

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition, 
    TestSet, Team, Submission, SGML_FILE, TEXT_FILE
)


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
            is_verified=True,
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
        self.assertEqual(round(sub.score_chrf, 3), 66.444)

    def test_scores_are_computed_for_submission_in_sgml_format(self):
        """Checks that scores are computed for a submission."""
        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.sgm'
        self._make_submission(_file, SGML_FILE)
        sub = Submission.objects.get(name=_file)

        self.assertEqual(round(sub.score, 3), 42.431)
        self.assertEqual(round(sub.score_chrf, 3), 66.444)

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

    def test_successful_submission(self):
        """Checks that a successful submission displays message about the success."""
        self._set_ocelot_team_token()

        _file = 'xml/sample-hyp.xml'
        with open(
            os.path.join(TESTDATA_DIR, _file), encoding='utf8'
        ) as tst:
            data = {
                'test_set': '1',
                'hyp_file': tst,
            }
            response = self.client.post('/submit', data, follow=True)
        self.assertContains(response, 'successfully submitted')
        self.assertNotContains(response, 'submission has closed')

    def test_submission_cannot_be_made_by_unverified_team(self):
        """Checks that a submission cannot be made by an unverfied team."""
        self._set_ocelot_team_token()
        self.team.is_verified = False
        self.team.save()

        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        with open(
            os.path.join(TESTDATA_DIR, _file), encoding='utf8'
        ) as tst:
            data = {
                'test_set': '1',
                'hyp_file': tst,
            }
            response = self.client.post('/submit', data, follow=True)
        self.assertContains(response, 'needs to be verified')
        self.assertNotContains(response, 'successfully submitted')

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

    def test_removed_submission_are_not_shown_on_leaderboard(self):
        """Checks that submissions marked as removed are not shown."""
        self._set_ocelot_team_token()

        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        sub = self._make_submission(_file)
        sub.save()

        # Check the submission is shown on the leaderboard
        comp = sub.test_set.competition
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertContains(
            response, 'Anonymous submission #{0}'.format(sub.id)
        )

        # Mark submission as removed
        sub.is_removed = True
        sub.save()

        # Check the submission is not shown on the leaderboard
        comp = sub.test_set.competition
        response = self.client.get('/leaderboard/{0}'.format(comp.id))
        self.assertNotContains(
            response, 'Anonymous submission #{0}'.format(sub.id)
        )
