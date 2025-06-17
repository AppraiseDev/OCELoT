"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Submission model tests for testsets in JSONL format.
"""
import os
from datetime import datetime
from pathlib import Path
from shutil import copyfile

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition, 
    TestSet, Team, Submission, JSONL_FILE, MEDIA_ROOT
)


class JSONLSubmissionTests(TestCase):
    """Tests Submission model for JSONL‐format test sets."""

    def setUp(self):
        # create languages
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='ha', name='Hausa')

        # competition in the future
        ny = datetime.now().year + 1
        self.comp = Competition.objects.create(
            is_active=True,
            name='CompetitionJSONL',
            description='Description of the JSONL competition',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )

        # standard JSONL testset
        self.testset = TestSet.objects.create(
            is_active=True,
            name='TestSetJSONL',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='ha'),
            file_format=JSONL_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'jsonl/sample-src.jsonl'),
            ref_file=os.path.join(TESTDATA_DIR, 'jsonl/sample-src-ref.jsonl'),
            competition=self.comp,
        )

        # JSONL testset without references
        self.testset_noref = TestSet.objects.create(
            is_active=True,
            name='TestSetJSONLNoRefs',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='ha'),
            file_format=JSONL_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'jsonl/sample-src.jsonl'),
            ref_file=None,
            competition=self.comp,
        )

        # multi‐reference JSONL testset
        self.testset_multiref = TestSet.objects.create(
            is_active=True,
            name='TestSetJSONLMultiRefs',
            source_language=self.testset.source_language,
            target_language=self.testset.target_language,
            file_format=JSONL_FILE,
            src_file=self.testset.src_file.name,
            ref_file=os.path.join(
                TESTDATA_DIR, 'jsonl/sample-src-multirefs.jsonl'
            ),
            competition=self.comp,
        )

        self.team = Team.objects.create(
            is_active=True, 
            is_verified=True,
            name='Team JSONL',
            email='jsonl@team.com'
        )

    def tearDown(self):
        # remove any generated files
        for fname in (
            'jsonl/sample-src.txt',
            'jsonl/sample-src-ref.txt',
            'jsonl/sample-src-multirefs.txt',
            'jsonl/sample-hyp.txt',
            'jsonl/sample-hyp_standard.txt',
            'jsonl/sample-hyp_standard.jsonl',
            'jsonl/sample-hyp_multiref.txt',
            'jsonl/sample-hyp_multiref.jsonl',
            'jsonl/sample-hyp_norefs.txt',
            'jsonl/sample-hyp_norefs.jsonl',
            'jsonl/sample-hyp-no-systems.jsonl',
        ):
            p = Path(TESTDATA_DIR) / fname
            if p.exists():
                p.unlink()

    def _make_submission(self, file_name, file_format=JSONL_FILE, test_set=None):
        return Submission.objects.create(
            name=file_name,
            original_name=file_name,
            test_set=test_set or self.testset,
            submitted_by=self.team,
            file_format=file_format,
            hyp_file=os.path.join(TESTDATA_DIR, file_name),
        )

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

    def _set_ocelot_team_token(self):
        """Set the team token to be able to render the submission form."""
        session = self.client.session
        session['ocelot_team_token'] = self.team.token
        session.save()

    def test_submission_in_text_format_to_jsonl_testset(self):
        """Text‐format submission against JSONL testset yields scores."""
        src_txt = 'jsonl/sample-hyp.ha.txt'
        # assume this file exists in testdata/jsonl/
        sub = self._make_submission(src_txt, file_format= '\t' not in src_txt and '' or JSONL_FILE)
        # scores should be positive
        self.assertGreater(sub.score, 0)
        self.assertGreater(sub.score_chrf, 0)

    def test_submission_in_jsonl_format_to_jsonl_testset(self):
        """JSONL submission to JSONL testset computes correct scores."""
        # copy file to avoid reading an automatically created '.txt' from the sample-hyp.jsonl
        copyfile(
            os.path.join(TESTDATA_DIR, 'jsonl/sample-hyp.jsonl'),
            os.path.join(TESTDATA_DIR, 'jsonl/sample-hyp_standard.jsonl'),
        )
        hyp = 'jsonl/sample-hyp_standard.jsonl'

        sub = self._make_submission(hyp)
        self.assertEqual(round(sub.score, 3), 81.141)
        self.assertEqual(round(sub.score_chrf, 3), 89.180)
        # check that a .txt was created
        txt = Path(TESTDATA_DIR) / hyp.replace('.jsonl', '.txt')
        self.assertTrue(txt.exists())
        self.assertTrue(txt.stat().st_size > 0)

    def test_submission_in_jsonl_format_to_jsonl_multiref_testset(self):
        """JSONL submission to multiref JSONL testset uses only first ref."""
        copyfile(
            os.path.join(TESTDATA_DIR, 'jsonl/sample-hyp.jsonl'),
            os.path.join(TESTDATA_DIR, 'jsonl/sample-hyp_multiref.jsonl'),
        )
        hyp = 'jsonl/sample-hyp_multiref.jsonl'

        sub = self._make_submission(hyp, test_set=self.testset_multiref)
        # should be same as single‐ref score
        self.assertEqual(round(sub.score, 3), 81.141)
        self.assertEqual(round(sub.score_chrf, 3), 89.180)

    def test_submission_in_jsonl_format_to_jsonl_testset_without_refs(self):
        """JSONL submission to JSONL testset without references."""
        copyfile(
            os.path.join(TESTDATA_DIR, 'jsonl/sample-hyp.jsonl'),
            os.path.join(TESTDATA_DIR, 'jsonl/sample-hyp_norefs.jsonl'),
        )
        hyp = 'jsonl/sample-hyp_norefs.jsonl'
        sub = self._make_submission(hyp, test_set=self.testset_noref)
        # check if the submission file was saved under MEDIA_ROOT
        media_file = Path(MEDIA_ROOT) / sub.hyp_file.name
        self.assertTrue(media_file.exists(), f"{media_file} does not exist")

#    def test_submission_in_jsonl_format_must_have_systems(self):
#        """Checks that submissions in JSONL format without system translations are not allowed."""
#        self._set_ocelot_team_token()
#        self.team.is_verified = True
#        self.team.save()
#
#        # Create a copied temp file for testing to avoid reading an
#        # automatically created '.txt' from the sample-src.xml
#        src_file = 'jsonl/sample-src.jsonl'
#        hyp_file = src_file.replace('-src.jsonl', '-hyp-no-systems.jsonl')
#        src_path = Path(TESTDATA_DIR) / src_file
#        hyp_path = Path(TESTDATA_DIR) / hyp_file
#
#        # Copy file
#        hyp_path.write_text(src_path.read_text())
#
#        with open(hyp_path, encoding='utf8') as xml:
#            data = {
#                'test_set': '1',
#                'file_format': 'JSONL',
#                'hyp_file': xml,
#            }
#            response = self.client.post('/submit', data, follow=True)
#
#        #print(f"Response content: {response.content.decode('utf-8')}", file=sys.stderr)
#        self.assertContains(response, 'No system found')
#        self.assertNotContains(response, 'successfully submitted')
#
#        self._clean_text_file(hyp_file, file_ext='.jsonl')
