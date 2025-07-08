"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Submission model tests for testsets in JSONL format.
"""
import gzip
import json
import os
from datetime import datetime
from pathlib import Path
from shutil import copyfile

from django.core.files.uploadedfile import SimpleUploadedFile

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition,
    TestSet, Team, Submission, TEXT_FILE, JSONL_FILE, MEDIA_ROOT
)
from leaderboard.models import ValidationError


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
        # JSONL testset with optional languages and no references
        self.testset_opt = TestSet.objects.create(
            is_active=True,
            name='TestSetOptionalLangJSONL',
            file_format=JSONL_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'jsonl/wmt-src.jsonl'),
            ref_file=None,
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
            'jsonl/wmt-hyp-b.txt',
            'jsonl/wmt-hyp-short.jsonl',
            'jsonl/wmt-hyp-short.txt',
            'jsonl/wmt-hyp-long.jsonl',
            'jsonl/wmt-hyp-long.txt',
            # Add compressed file cleanup
            'jsonl/sample-hyp_compressed.jsonl.gz',
            'jsonl/sample-hyp_compressed.txt',
            # Add validation test file cleanup
            'jsonl/test_src_validation.txt',
            'jsonl/test_src_validation.jsonl.gz',
            'jsonl/test_hyp_validation_valid.jsonl.gz',
            'jsonl/test_hyp_validation_invalid.jsonl.gz',
        ):
            p = Path(TESTDATA_DIR) / fname
            if p.exists():
                p.unlink()

    def _make_submission(self, file_name, file_format=JSONL_FILE, test_set=None):
        # Create submission instance and run validations on hyp_file
        hyp_path = os.path.join(TESTDATA_DIR, file_name)
        sub = Submission(
            name=file_name,
            original_name=file_name,
            test_set=test_set or self.testset,
            submitted_by=self.team,
            file_format=file_format,
            hyp_file=hyp_path,
        )
        # Validate using model full_clean to trigger field validators
        sub.full_clean()
        sub.save()
        return sub

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

    def _create_compressed_jsonl(self, source_file, target_file):
        """Helper method to create a compressed JSONL file from an uncompressed one."""
        source_path = os.path.join(TESTDATA_DIR, source_file)
        target_path = os.path.join(TESTDATA_DIR, target_file)

        with open(source_path, 'r', encoding='utf-8') as f_in:
            with gzip.open(target_path, 'wt', encoding='utf-8') as f_out:
                f_out.write(f_in.read())

        return target_path

    def test_submission_in_text_format_to_jsonl_testset(self):
        """Text‐format submission against JSONL testset yields scores."""
        src_txt = 'jsonl/sample-hyp.ha.txt'
        # assume this file exists in testdata/jsonl/
        sub = self._make_submission(src_txt, file_format=TEXT_FILE)
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
        # check that a .txt was created under MEDIA_ROOT
        media_txt = Path(MEDIA_ROOT) / sub.hyp_file.name.replace('.jsonl', '.txt')
        self.assertTrue(media_txt.exists(), f"{media_txt} does not exist")
        self.assertTrue(media_txt.stat().st_size > 0)

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

    def test_submissions_to_optional_languages_testset(self):
        """Checks submissions for a multi-language (optional languages) JSONL test set."""
        # Use JSONL test set with optional languages and no references
        testset_opt = self.testset_opt
        self.assertIsNone(testset_opt.source_language)
        self.assertIsNone(testset_opt.target_language)

        # Verify source text file is extracted
        src_txt = Path(testset_opt.src_file.name.replace('.jsonl', '.txt'))
        self.assertTrue(src_txt.exists())
        self.assertTrue(src_txt.stat().st_size > 0)

        # Create submissions using wmt-hyp-a and wmt-hyp-b
        sub_b = self._make_submission('jsonl/wmt-hyp-b.jsonl', test_set=testset_opt)

        # Since there are no references, no scores should be computed
        self.assertIsNone(sub_b.score)
        self.assertIsNone(sub_b.score_chrf)

        # Check that hyp files have been uploaded to submissions folder
        media_file_b = Path(MEDIA_ROOT) / sub_b.hyp_file.name
        self.assertTrue(media_file_b.exists(), f"{media_file_b} does not exist")

        # Clean up created text files
        src_txt.unlink()

    def test_submission_without_hyps_rejected(self):
        """Checks that JSONL submission without hyps is rejected."""
        # Using a JSONL file without hyps field (reference file) to simulate missing hyps
        with self.assertRaises(ValidationError) as cm:
            self._make_submission(
                'jsonl/wmt-src.jsonl', test_set=self.testset_opt
            )
        # Verify the correct validation message is included
        expected = 'Could not find "hypothesis"'
        self.assertIn(expected, str(cm.exception))

    def test_submission_with_short_hyps_rejected(self):
        """Checks that JSONL submission with fewer hyps lines than source is rejected."""
        # Create a short hyp file with only one segment
        src = Path(TESTDATA_DIR) / 'jsonl/wmt-hyp-a.jsonl'
        dst = Path(TESTDATA_DIR) / 'jsonl/wmt-hyp-short.jsonl'
        lines = src.read_text(encoding='utf8').splitlines()[:2]
        dst.write_text('\n'.join(lines) + '\n', encoding='utf8')
        # Attempt submission and expect length mismatch error
        with self.assertRaises(ValidationError) as cm:
            self._make_submission('jsonl/wmt-hyp-short.jsonl', test_set=self.testset_opt)
        # Validate error message
        msg = str(cm.exception)
        self.assertIn('Submission invalid: hyp', msg)
        # Clean up short hyp file
        dst.unlink()

    def test_submission_with_long_hyps_rejected(self):
        """Checks that JSONL submission with more hyps lines than source is rejected."""
        # Create a long hyp file by duplicating all lines
        src = Path(TESTDATA_DIR) / 'jsonl/wmt-hyp-a.jsonl'
        dst = Path(TESTDATA_DIR) / 'jsonl/wmt-hyp-long.jsonl'
        lines = src.read_text(encoding='utf8').splitlines()
        # Duplicate lines to exceed source segments
        long_lines = lines + lines
        dst.write_text('\n'.join(long_lines) + '\n', encoding='utf8')
        # Attempt submission and expect length mismatch error
        with self.assertRaises(ValidationError) as cm:
            self._make_submission('jsonl/wmt-hyp-long.jsonl', test_set=self.testset_opt)
        # Check error message for hyp length mismatch
        self.assertIn('Submission invalid: hyp', str(cm.exception))
        # Clean up long hyp file
        dst.unlink()

    def test_submission_in_compressed_jsonl_format(self):
        """JSONL submission in compressed (.jsonl.gz) format to JSONL testset computes correct scores."""
        # Create a compressed version of the sample hypothesis file
        src_file = os.path.join(TESTDATA_DIR, 'jsonl/sample-hyp.jsonl')
        compressed_file = os.path.join(TESTDATA_DIR, 'jsonl/sample-hyp_compressed.jsonl.gz')

        # Read the original JSONL file and compress it
        with open(src_file, 'r', encoding='utf-8') as f_in:
            with gzip.open(compressed_file, 'wt', encoding='utf-8') as f_out:
                f_out.write(f_in.read())

        # Verify the compressed file exists and has content
        self.assertTrue(Path(compressed_file).exists())
        self.assertGreater(Path(compressed_file).stat().st_size, 0)

        # Create submission with compressed file
        sub = self._make_submission('jsonl/sample-hyp_compressed.jsonl.gz')

        # Verify scores are computed correctly (same as uncompressed version)
        self.assertEqual(round(sub.score, 3), 81.141)
        self.assertEqual(round(sub.score_chrf, 3), 89.180)

        # Check that a .txt file was created under MEDIA_ROOT with correct extension handling
        media_txt = Path(MEDIA_ROOT) / sub.hyp_file.name.replace('.jsonl.gz', '.txt')
        self.assertTrue(media_txt.exists(), f"{media_txt} does not exist")
        self.assertTrue(media_txt.stat().st_size > 0)

        # Verify the submission file itself was saved correctly
        media_file = Path(MEDIA_ROOT) / sub.hyp_file.name
        self.assertTrue(media_file.exists(), f"{media_file} does not exist")
        self.assertTrue(media_file.name.endswith('.jsonl.gz'))

    def test_compressed_jsonl_validation(self):
        """Test that compressed JSONL files pass validation checks."""
        # Create a test compressed JSONL file with valid content
        test_data = [
            {
                "dataset_id": "test",
                "doc_id": "doc1",
                "tgt_lang": "ha",
                "hypothesis": "Test hypothesis 1"
            },
            {
                "dataset_id": "test",
                "doc_id": "doc2",
                "tgt_lang": "ha",
                "hypothesis": "Test hypothesis 2"
            }
        ]

        compressed_file = os.path.join(TESTDATA_DIR, 'jsonl/test_validation_compressed.jsonl.gz')

        # Create compressed file
        with gzip.open(compressed_file, 'wt', encoding='utf-8') as f:
            for item in test_data:
                f.write(json.dumps(item) + '\n')

        try:
            # Test that file format validation accepts .jsonl.gz extension
            from leaderboard.models import validate_jsonl_schema, validate_jsonl_submission

            # Create a SimpleUploadedFile object to test validation
            with open(compressed_file, 'rb') as f:
                uploaded_file = SimpleUploadedFile(
                    "test_validation_compressed.jsonl.gz",
                    f.read(),
                    content_type="application/gzip"
                )

            # Test schema validation - should not raise exception
            validate_jsonl_schema(uploaded_file)

            # Test submission validation - should not raise exception
            validate_jsonl_submission(uploaded_file)

        finally:
            # Clean up test file
            if Path(compressed_file).exists():
                Path(compressed_file).unlink()

    def test_validate_hyp_file_content_with_compressed_jsonl(self):
        """Test that _validate_hyp_file_content works with compressed JSONL files."""
        # Create a test source file with 3 lines
        src_data = [
            {"dataset_id": "test", "doc_id": "doc1", "src_lang": "en", "src_text": "Source 1"},
            {"dataset_id": "test", "doc_id": "doc2", "src_lang": "en", "src_text": "Source 2"},
            {"dataset_id": "test", "doc_id": "doc3", "src_lang": "en", "src_text": "Source 3"}
        ]

        src_file = os.path.join(TESTDATA_DIR, 'jsonl/test_src_validation.jsonl.gz')
        with gzip.open(src_file, 'wt', encoding='utf-8') as f:
            for item in src_data:
                f.write(json.dumps(item) + '\n')

        # Create a compressed testset using this source file
        test_testset = TestSet.objects.create(
            is_active=True,
            name='TestSetValidation',
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='ha'),
            file_format=JSONL_FILE,
            src_file=src_file,
            ref_file=None,
            competition=self.comp,
        )

        try:
            # Test case 1: Compressed hyp file with matching line count (should pass)
            hyp_data_valid = [
                {"dataset_id": "test", "doc_id": "doc1", "tgt_lang": "ha", "hypothesis": "Hyp 1"},
                {"dataset_id": "test", "doc_id": "doc2", "tgt_lang": "ha", "hypothesis": "Hyp 2"},
                {"dataset_id": "test", "doc_id": "doc3", "tgt_lang": "ha", "hypothesis": "Hyp 3"}
            ]

            hyp_file_valid = os.path.join(TESTDATA_DIR, 'jsonl/test_hyp_validation_valid.jsonl.gz')
            with gzip.open(hyp_file_valid, 'wt', encoding='utf-8') as f:
                for item in hyp_data_valid:
                    f.write(json.dumps(item) + '\n')

            # Create submission with matching line count - should not raise ValidationError
            sub_valid = Submission(
                name='test_valid_compressed',
                original_name='test_valid_compressed',
                test_set=test_testset,
                submitted_by=self.team,
                file_format=JSONL_FILE,
                hyp_file=hyp_file_valid,
            )

            # This should not raise an exception
            sub_valid._validate_hyp_file_content()

            # Test case 2: Compressed hyp file with mismatched line count (should fail)
            hyp_data_invalid = [
                {"dataset_id": "test", "doc_id": "doc1", "tgt_lang": "ha", "hypothesis": "Hyp 1"},
                {"dataset_id": "test", "doc_id": "doc2", "tgt_lang": "ha", "hypothesis": "Hyp 2"}
                # Missing third line
            ]

            hyp_file_invalid = os.path.join(TESTDATA_DIR, 'jsonl/test_hyp_validation_invalid.jsonl.gz')
            with gzip.open(hyp_file_invalid, 'wt', encoding='utf-8') as f:
                for item in hyp_data_invalid:
                    f.write(json.dumps(item) + '\n')

            sub_invalid = Submission(
                name='test_invalid_compressed',
                original_name='test_invalid_compressed',
                test_set=test_testset,
                submitted_by=self.team,
                file_format=JSONL_FILE,
                hyp_file=hyp_file_invalid,
            )

            # This should raise a ValidationError
            with self.assertRaises(ValidationError) as cm:
                sub_invalid._validate_hyp_file_content()

            self.assertIn('hyp JSONL lines (2) != src JSONL lines (3)', str(cm.exception))

        finally:
            # Clean up test files
            for test_file in [
                src_file,
                hyp_file_valid,
                hyp_file_invalid
            ]:
                if Path(test_file).exists():
                    Path(test_file).unlink()

    def test_successful_jsonl_submission(self):
        """Checks that a successful submission displays message about the success."""
        self._set_ocelot_team_token()

        # Simulate a submission request
        _file = 'jsonl/wmt-hyp-b.jsonl'
        with open(os.path.join(TESTDATA_DIR, _file), encoding='utf8') as f:
            data = {
                'test_set': self.testset_opt.id,
                'hyp_file': f,
            }
            response = self.client.post('/submit', data, follow=True)
        self.assertContains(response, 'successfully submitted')


#####################################################################
# Tests for analyze_xyz_file functions

class WMTSTMTSubmissionTests(TestCase):
    """Tests Submission model for WMT-ST MT JSONL format."""

    def setUp(self):
        """Set up test data for WMT-ST MT JSONL format tests."""
        Language.objects.create(code='de', name='German')
        Language.objects.create(code='dsb', name='Lower Sorbian')

        _next_year = datetime.now().year + 1
        self.competition = Competition.objects.create(
            is_active=True,
            name='WMT-ST-MT Competition',
            description='WMT Speech Translation MT Competition',
            deadline=datetime(_next_year, 1, 1, tzinfo=timezone.utc),
        )

        # Create test set for WMT-ST MT format (uses multi-language setting)
        self.testset = TestSet.objects.create(
            is_active=True,
            name='WMT-ST-MT TestSet',
            source_language=None,  # Multi-language test set
            target_language=None,  # Multi-language test set
            file_format=JSONL_FILE,
            src_file=os.path.join(
                TESTDATA_DIR, 'jsonl-wmt-st/wmt-st-mt.jsonl'
            ),
            ref_file=os.path.join(
                TESTDATA_DIR, 'jsonl-wmt-st/wmt-st-mt.jsonl'
            ),
            competition=self.competition,
        )

        self.team = Team.objects.create(
            is_active=True,
            is_verified=True,
            name='WMT-ST Team',
            email='wmt-st-team@email.com',
        )

    def _set_ocelot_team_token(self):
        """Set the team token to be able to render the submission form."""
        session = self.client.session
        session['ocelot_team_token'] = self.team.token
        session.save()

    def _make_submission(self, file_name, file_format=JSONL_FILE):
        """Makes a WMT-ST MT submission."""
        return Submission.objects.create(
            name=file_name,
            original_name=file_name,
            test_set=self.testset,
            submitted_by=self.team,
            file_format=file_format,
            hyp_file=os.path.join(TESTDATA_DIR, 'jsonl-wmt-st', file_name),
        )

    def test_wmt_st_mt_testset_validation(self):
        """Test that WMT-ST MT JSONL test set validates correctly."""
        # Test set should be valid and format should be detected
        self.assertTrue(self.testset.is_active)
        self.assertEqual(self.testset.file_format, JSONL_FILE)

    def test_wmt_st_mt_submission_with_predictions(self):
        """Test WMT-ST MT submission with predictions."""
        _file = 'wmt-st-mt.pred.jsonl'
        sub = self._make_submission(_file)
        
        # Check basic submission properties
        self.assertEqual(sub.name, _file)
        self.assertEqual(sub.file_format, JSONL_FILE)
        self.assertEqual(sub.test_set, self.testset)
        self.assertEqual(sub.submitted_by, self.team)
        self.assertTrue(sub.is_valid)

    def test_wmt_st_mt_submission_pred_only(self):
        """Test WMT-ST MT submission with predictions only."""
        _file = 'wmt-st-mt.pred_only.jsonl'
        sub = self._make_submission(_file)
        
        # Check basic submission properties
        self.assertEqual(sub.name, _file)
        self.assertEqual(sub.file_format, JSONL_FILE)
        self.assertEqual(sub.test_set, self.testset)
        self.assertEqual(sub.submitted_by, self.team)
        self.assertTrue(sub.is_valid)

    def test_wmt_st_mt_submission_scores_computation(self):
        """Test that scores are computed for WMT-ST MT submissions."""
        _file = 'wmt-st-mt.pred.jsonl'
        sub = self._make_submission(_file)
        
        # Scores should be computed if compute_scores is enabled
        if self.testset.compute_scores:
            self.assertIsNotNone(sub.score)
            self.assertIsNotNone(sub.score_chrf)
            # Scores should be positive numbers
            self.assertGreater(sub.score, 0)
            self.assertGreater(sub.score_chrf, 0)

    def test_wmt_st_mt_submission_is_anonymous_by_default(self):
        """Test that WMT-ST MT submission is anonymous by default."""
        _file = 'wmt-st-mt.pred.jsonl'
        sub = self._make_submission(_file)
        
        # Check that submission is anonymous by default
        self.assertFalse(sub.is_public)
        self.assertIn('Anonymous', str(sub))

    def test_wmt_st_mt_submission_can_be_public(self):
        """Test that WMT-ST MT submission can be made public."""
        _file = 'wmt-st-mt.pred.jsonl'
        sub = self._make_submission(_file)
        sub.is_public = True
        sub.save()
        
        # Check that submission is public
        self.assertTrue(sub.is_public)
        self.assertNotIn('Anonymous', str(sub))

    def test_wmt_st_mt_submission_form_shows_testset(self):
        """Test that WMT-ST MT test set appears in submission form."""
        self._set_ocelot_team_token()
        
        response = self.client.get('/submit')
        self.assertContains(response, self.testset.name)

    def test_wmt_st_mt_submission_form_upload(self):
        """Test uploading WMT-ST MT submission through form."""
        self._set_ocelot_team_token()
        
        _file = 'jsonl-wmt-st/wmt-st-mt.pred.jsonl'
        with open(os.path.join(TESTDATA_DIR, _file), encoding='utf8') as f:
            data = {
                'test_set': str(self.testset.id),
                'hyp_file': f,
            }
            response = self.client.post('/submit', data, follow=True)
        
        # Check that submission was successful
        self.assertNotContains(response, 'submission has closed')
        # Check that a submission was created
        self.assertTrue(Submission.objects.filter(
            test_set=self.testset,
            submitted_by=self.team
        ).exists())

    def test_wmt_st_mt_format_detection(self):
        """Test that WMT-ST MT format is correctly detected."""
        # Import the detection function
        from leaderboard.utils import detect_jsonl_format
        
        # Test that WMT-ST MT format is detected
        st_mt_file = os.path.join(TESTDATA_DIR, 'jsonl-wmt-st/wmt-st-mt.jsonl')
        self.assertTrue(detect_jsonl_format(st_mt_file, 'WMT-ST-MT'))
        
        # Test with pred file
        pred_file = os.path.join(TESTDATA_DIR, 'jsonl-wmt-st/wmt-st-mt.pred.jsonl')
        self.assertTrue(detect_jsonl_format(pred_file, 'WMT-ST-MT'))
        
        # Test with pred only file  
        pred_only_file = os.path.join(TESTDATA_DIR, 'jsonl-wmt-st/wmt-st-mt.pred_only.jsonl')
        self.assertTrue(detect_jsonl_format(pred_only_file, 'WMT-ST-MT'))

    def test_wmt_st_mt_testset_text_file_creation(self):
        """Test that text files are created from WMT-ST MT JSONL files."""
        # Force text file creation
        self.testset._create_text_files()
        
        # Check if text files were created
        src_path = str(self.testset.src_file.name).replace('.jsonl', '.txt')
        ref_path = str(self.testset.ref_file.name).replace('.jsonl', '.txt')
        
        # Files should exist after text file creation
        self.assertTrue(os.path.exists(src_path) or 
                       os.path.exists(os.path.join(TESTDATA_DIR, 'jsonl-wmt-st/wmt-st-mt.txt')))