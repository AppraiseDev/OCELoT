"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Submission model tests for testsets in XML format.
"""
import os
from datetime import datetime
from pathlib import Path
from shutil import copyfile

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition, 
    TestSet, Team, Submission, XML_FILE, TEXT_FILE
)


class XMLSubmissionTests(TestCase):
    """Tests Submission model for XML format."""

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
