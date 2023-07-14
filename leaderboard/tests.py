"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import os
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from shutil import copyfile

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
from leaderboard.utils import analyze_xml_file
from leaderboard.utils import process_xml_to_text
from ocelot.settings import BASE_DIR

TESTDATA_DIR = os.path.join(BASE_DIR, 'leaderboard/testdata')


class UtilsTests(TestCase):
    """Tests for utils."""

    def tearDown(self):
        file_paths = (
            '/xml/sample-hyp.xml.temp.txt',
            '/xml/multi-src-ref.xml.temp.txt',
        )
        for file_path in file_paths:
            txt_path = Path(TESTDATA_DIR + file_path)
            if txt_path.exists():
                txt_path.unlink()

    def test_analyze_xml_file_with_testset(self):
        """Checks if source and reference can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/sample-src-ref.xml'
        _, src_langs, ref_langs, translators, _ = analyze_xml_file(
            xml_path
        )

        self.assertSetEqual(src_langs, set(['en']))
        self.assertSetEqual(ref_langs, set(['ha']))
        self.assertSetEqual(translators, set(['A']))

    def test_analyze_xml_file_with_multi_reference_testset(self):
        """Checks if multiple references can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/sample-src-multirefs.xml'
        _, src_langs, ref_langs, translators, _ = analyze_xml_file(
            xml_path
        )

        self.assertSetEqual(src_langs, set(['en']))
        self.assertSetEqual(ref_langs, set(['ha']))
        self.assertSetEqual(translators, set(['A', 'B']))

    def test_analyze_xml_file_with_hypothesis(self):
        """Checks if systems can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/sample-hyp.xml'
        _, src_langs, _, _, systems = analyze_xml_file(xml_path)

        self.assertSetEqual(src_langs, set(['en']))
        self.assertSetEqual(systems, set(['test-team']))

    def test_analyze_xml_file_with_multiple_datasets(self):
        """Checks if multile data set IDs can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/multi-src-ref.xml'
        collections, _, _, _, _ = analyze_xml_file(xml_path)

        self.assertSetEqual(collections, set(['A', 'B', 'C']))

    def test_process_xml_to_text_with_hypothesis(self):
        """Checks if system segments can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/sample-hyp.xml'
        txt_path = xml_path + '.temp.txt'
        process_xml_to_text(xml_path, txt_path, system='test-team')

        txt_file = Path(txt_path)
        self.assertTrue(txt_file.exists())
        self.assertTrue(txt_file.stat().st_size > 0)

    def test_process_xml_to_text_from_one_collection(self):
        """Checks if source segments from a collection can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/multi-src-ref.xml'

        txt_path = xml_path + '.temp.txt'
        process_xml_to_text(
            xml_path, txt_path, source=True, collection='B'
        )
        txt_file = Path(txt_path)
        self.assertTrue(txt_file.exists())
        with open(txt_file, 'r', encoding='utf8') as content:
            self.assertTrue(len(content.readlines()) == 12)

    def test_process_xml_to_text_from_all_collections(self):
        """Checks if reference segments from all collections can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/multi-src-ref.xml'

        txt_path = xml_path + '.temp.txt'
        process_xml_to_text(
            xml_path, txt_path, reference=True, collection=None
        )
        txt_file = Path(txt_path)
        self.assertTrue(txt_file.exists())
        with open(txt_file, 'r', encoding='utf8') as content:
            self.assertTrue(len(content.readlines()) == 56)


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

    def test_successfull_submission(self):
        """Checks that a successfull submission displays message about the success."""
        self._set_ocelot_team_token()

        _file = 'newstest2019.msft-WMT19-document-level.6808.en-de.txt'
        with open(
            os.path.join(TESTDATA_DIR, _file), encoding='utf8'
        ) as tst:
            data = {
                'test_set': '1',
                'file_format': 'TEXT',
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
                'file_format': 'TEXT',
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


class XMLSubmissionTests(TestCase):
    """Tests Submission model."""

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='ha', name='Hausa')

        _next_year = datetime.now().year + 1
        self.competition = Competition.objects.create(
            is_active=True,
            name='CompetitionB',
            description='Description of the competition B',
            deadline=datetime(_next_year, 1, 1, tzinfo=timezone.utc),
        )

        self.testset = TestSet.objects.create(
            is_active=True,
            name='TestSetB',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='ha'),
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/sample-src.xml'),
            ref_file=os.path.join(TESTDATA_DIR, 'xml/sample-src-ref.xml'),
            competition=self.competition,
        )

        self.testset_multiref = TestSet.objects.create(
            is_active=True,
            name='TestSetMultiRefs',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='ha'),
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/sample-src.xml'),
            ref_file=os.path.join(
                TESTDATA_DIR, 'xml/sample-src-multirefs.xml'
            ),
            competition=self.competition,
        )

        # A copy of XML with source(s) and reference(s) is created to prevent
        # overwritting automatically generated text files
        _tst_file = Path(TESTDATA_DIR) / 'xml/multi-src-ref.xml'
        copyfile(_tst_file, str(_tst_file).replace('src-ref', 'ref'))

        self.testset_collection = TestSet.objects.create(
            is_active=True,
            name='TestSetCollections',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='ha'),
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/multi-src-ref.xml'),
            ref_file=os.path.join(TESTDATA_DIR, 'xml/multi-ref.xml'),
            competition=self.competition,
            collection='B',
        )

        self.team = Team.objects.create(
            is_active=True,
            name='Team B',
            email='team-b@email.com',
        )

    def tearDown(self):
        self._clean_text_file(self.testset.src_file.name, False)
        self._clean_text_file(self.testset.ref_file.name, False)
        self._clean_text_file(self.testset_multiref.src_file.name, False)
        self._clean_text_file(self.testset_multiref.ref_file.name, False)
        self._clean_text_file(self.testset_collection.src_file.name, False)
        self._clean_text_file(self.testset_collection.ref_file.name, False)
        # Clean up temporary file created for 'TestSetCollections'
        _tst_file = Path(TESTDATA_DIR) / 'xml/multi-ref.xml'
        if _tst_file.exists():
            _tst_file.unlink()

    def _clean_text_file(
        self, input_file, add_test_dir=True, file_ext='.txt'
    ):
        """Removes a temporary text file."""
        _file = (
            os.path.join(TESTDATA_DIR, input_file)
            if add_test_dir
            else input_file
        )
        input_path = Path(_file.replace('.xml', file_ext))
        if input_path.exists():
            input_path.unlink()

    def _make_submission(
        self, file_name, file_format=TEXT_FILE, test_set=None
    ):
        """Makes a submission."""
        return Submission.objects.create(
            name=file_name,
            original_name=file_name,
            test_set=test_set or self.testset,
            submitted_by=self.team,
            file_format=file_format,
            hyp_file=os.path.join(TESTDATA_DIR, file_name),
        )

    def _set_ocelot_team_token(self):
        """Set the team token to be able to render the submission form."""
        session = self.client.session
        session['ocelot_team_token'] = self.team.token
        session.save()

    def test_submission_in_text_format_to_xml_testset(self):
        """Checks making a submission in text format to XML testset."""
        _file = 'xml/sample-hyp.ha.txt'
        self._make_submission(_file)
        sub = Submission.objects.get(name=_file)

        self.assertEqual(round(sub.score, 3), 81.141)
        self.assertEqual(round(sub.score_chrf, 3), 89.180)

    def test_submission_in_xml_format_to_xml_testset(self):
        """Checks making a submission in XML format to XML testset."""
        _file = 'xml/sample-hyp.xml'
        self._make_submission(_file, file_format=XML_FILE)
        sub = Submission.objects.get(name=_file)

        self.assertEqual(round(sub.score, 3), 81.141)
        self.assertEqual(round(sub.score_chrf, 3), 89.180)

        self._clean_text_file(_file)

    def test_submission_in_xml_format_to_xml_multiref_testset(self):
        """Checks making a submission in XML format to XML testset with multiple references."""
        _file = 'xml/sample-hyp.xml'
        self._make_submission(
            _file, file_format=XML_FILE, test_set=self.testset_multiref
        )
        sub = Submission.objects.get(name=_file)

        # Scores should be identical to a single-reference test set because
        # only the first reference is used by design
        self.assertEqual(round(sub.score, 3), 81.141)
        self.assertEqual(round(sub.score_chrf, 3), 89.180)

        self._clean_text_file(_file)

    def test_submission_in_xml_format_with_testsuite(self):
        """Checks making a submission in XML format with testsuites."""
        _file = 'xml/sample-hyp.testsuite.xml'
        self._make_submission(_file, file_format=XML_FILE)
        sub = Submission.objects.get(name=_file)

        # Scores should be identical to a single-reference test set
        self.assertEqual(round(sub.score, 3), 81.141)
        self.assertEqual(round(sub.score_chrf, 3), 89.180)

        self._clean_text_file(_file)

    def test_submission_in_xml_format_with_invalid_schema(self):
        """Checks that XML file with invalid XML Schema cannot be submitted."""
        self._set_ocelot_team_token()
        self.team.is_verified = True
        self.team.save()

        _file = 'xml/sample-hyp.invalid.xml'
        with open(
            os.path.join(TESTDATA_DIR, _file), encoding='utf8'
        ) as xml:
            data = {
                'test_set': '1',
                'file_format': 'XML',
                'hyp_file': xml,
            }
            response = self.client.post('/submit', data, follow=True)

        self.assertContains(
            response, 'does not validate against the XML Schema'
        )
        self.assertNotContains(response, 'successfully submitted')

        self._clean_text_file(_file)

    def test_submission_in_xml_format_must_have_systems(self):
        """Checks that submissions in XML format without system translations are not allowed."""
        self._set_ocelot_team_token()
        self.team.is_verified = True
        self.team.save()

        # Create a copied temp file for testing to avoid reading an
        # automatically created '.txt' from the sample-src.xml
        src_file = 'xml/sample-src.xml'
        hyp_file = src_file.replace('-src.xml', '-hyp-no-systems.xml')
        src_path = Path(TESTDATA_DIR) / src_file
        hyp_path = Path(TESTDATA_DIR) / hyp_file

        # Copy file
        hyp_path.write_text(src_path.read_text())

        with open(hyp_path, encoding='utf8') as xml:
            data = {
                'test_set': '1',
                'file_format': 'XML',
                'hyp_file': xml,
            }
            response = self.client.post('/submit', data, follow=True)

        self.assertContains(response, 'No system found')
        self.assertNotContains(response, 'successfully submitted')

        self._clean_text_file(hyp_file, file_ext='.xml')

    def test_submission_in_xml_format_to_xml_testset_with_collection(self):
        """Checks making a submission to XML testset with a defined collection."""
        _file = 'xml/multi-hypA.xml'
        self._make_submission(
            _file, file_format=XML_FILE, test_set=self.testset_collection
        )
        sub = Submission.objects.get(name=_file)

        # Check if only the collection 'B' was extracted to a text file
        txt_path = Path(TESTDATA_DIR) / _file.replace('.xml', '.txt')
        # with open(txt_path, 'r', encoding='utf8') as cnt:
        # self.assertTrue(len(cnt.readlines()) == 12)

        # Check scores
        self.assertEqual(round(sub.score, 3), 34.992)
        self.assertEqual(round(sub.score_chrf, 3), 68.605)

        self._clean_text_file(_file)


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
        self.assertTrue(tst.has_references())

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
        self.assertTrue(tst.has_references())

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
        self.assertTrue(tst.has_references())

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

    def test_create_test_set_with_collections(self):
        """Checks that a test set can be created from a single collection."""

        TestSet.objects.create(
            name='TestSetD',
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/multi-src-ref.xml'),
            ref_file=os.path.join(TESTDATA_DIR, 'xml/multi-src-ref.xml'),
            collection='B',
        )

        tst = TestSet.objects.get(name='TestSetD')
        self.assertEqual(tst.name, 'TestSetD')
        self.assertTrue(tst.src_file.name.endswith('.xml'))
        self.assertTrue(tst.ref_file.name.endswith('.xml'))
        self.assertEqual(tst.collection, 'B')
        self.assertTrue(tst.has_references())

        # Check if text files has been created and have only 12 segments from
        # the collection 'B'
        src_txt_file = Path(tst.src_file.name.replace('.xml', '.txt'))
        ref_txt_file = Path(tst.ref_file.name.replace('.xml', '.txt'))
        self.assertTrue(src_txt_file.exists())
        self.assertTrue(ref_txt_file.exists())
        self.assertTrue(src_txt_file.stat().st_size > 0)
        self.assertTrue(ref_txt_file.stat().st_size > 0)
        with open(src_txt_file, 'r', encoding='utf8') as cnt:
            self.assertTrue(len(cnt.readlines()) == 12)
        with open(ref_txt_file, 'r', encoding='utf8') as cnt:
            self.assertTrue(len(cnt.readlines()) == 12)

        # Clean up created files
        if src_txt_file.exists():
            src_txt_file.unlink()
        if ref_txt_file.exists():
            ref_txt_file.unlink()

    def test_create_test_set_without_reference(self):
        """Checks that a test set can be created without a reference."""

        TestSet.objects.create(
            name='TestSetE',
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/sample-src.xml'),
        )

        tst = TestSet.objects.get(name='TestSetE')
        self.assertEqual(tst.name, 'TestSetE')
        self.assertTrue(tst.src_file.name.endswith('.xml'))
        self.assertFalse(tst.ref_file)
        self.assertFalse(tst.has_references())

        # Check if text files has been created
        src_txt_file = Path(tst.src_file.name.replace('.xml', '.txt'))
        self.assertTrue(src_txt_file.exists())
        self.assertTrue(src_txt_file.stat().st_size > 0)

        # Clean up created files
        if src_txt_file.exists():
            src_txt_file.unlink()


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
