"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Submission model tests for testsets in JSON format.
"""
import gzip
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from shutil import copyfile

from django.core.files.uploadedfile import SimpleUploadedFile

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition,
    TestSet, Team, Submission, TEXT_FILE, MEDIA_ROOT
)
from leaderboard.models import ValidationError, JSON_FILE
from leaderboard.utils import analyze_json_file, process_json_to_text


class JSONSubmissionTests(TestCase):
    """Tests Submission model for JSON‐format test sets."""

    def setUp(self):
        # Create languages - for MIST tasks, language codes may be generic
        Language.objects.create(code='multi', name='Multilingual')
        Language.objects.create(code='en', name='English')

        # Competition in the future
        ny = datetime.now().year + 1
        self.comp = Competition.objects.create(
            is_active=True,
            name='CompetitionJSON',
            description='Description of the JSON competition (MIST)',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )

        # Standard JSON testset using MIST format
        self.testset = TestSet.objects.create(
            is_active=True,
            name='TestSetJSON',
            source_language=Language.objects.get(code='multi'),
            target_language=Language.objects.get(code='multi'),
            file_format=JSON_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'json/mist25.json'),
            ref_file=os.path.join(TESTDATA_DIR, 'json/mist25-hyp.json'),
            competition=self.comp,
        )

        # JSON testset without references
        self.testset_noref = TestSet.objects.create(
            is_active=True,
            name='TestSetJSONNoRefs',
            source_language=Language.objects.get(code='multi'),
            target_language=Language.objects.get(code='multi'),
            file_format=JSON_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'json/mist25.json'),
            ref_file=None,
            competition=self.comp,
        )

        self.team = Team.objects.create(
            is_active=True,
            is_verified=True,
            name='Team JSON',
            email='json@team.com'
        )

    def tearDown(self):
        # Remove any generated files
        for fname in (
            # Main test files automatically generated
            'json/mist25.txt',
            'json/mist25-hyp.txt',
            # Files from test_process_json_to_text
            'json/test_src.txt',
            'json/test_hyp.txt',
            # Files from test_valid_json_submission
            'json/test_hyp_valid.json',
            'json/test_src_valid.json',
            'json/test_hyp_valid.txt',
            'json/test_src_valid.txt',
            # Files from test_json_submission_validation_schema
            'json/test_invalid.json',
            # Files from test_json_submission_validation_empty
            'json/test_empty.json',
            # Files from test_json_submission_validation_missing_answers
            'json/test_no_answer.json',
            # Files from test_json_submission_validation_mismatched_items
            'json/test_hyp_wrong.json',
            'json/test_src_wrong.json',
            'json/test_hyp_wrong.txt',
            'json/test_src_wrong.txt',
            # Files from test_json_submission_compressed
            'json/test_hyp_compressed.json.gz',
            'json/test_src_compressed.json.gz',
            'json/test_hyp_compressed.txt',
            'json/test_src_compressed.txt',
            # Files from test_json_submission_file_extension_validation
            'json/test_wrong.txt',
            # Legacy/unused filenames (keeping for compatibility)
            'json/test_hyp.json',
            'json/test_src_validation.txt',
            'json/test_src_validation.json.gz',
            'json/test_hyp_validation_valid.json.gz',
            'json/test_hyp_validation_invalid.json.gz',
            'json/test_wrong_items.json',
        ):
            p = Path(TESTDATA_DIR) / fname
            if p.exists():
                p.unlink()

    def _make_submission(self, file_name, file_format=JSON_FILE, test_set=None):
        """Create submission instance and run validations on hyp_file."""
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

    def _clean_text_file(self, input_file, add_test_dir=True, file_ext='.txt'):
        """Removes a temporary text file."""
        _file = (
            os.path.join(TESTDATA_DIR, input_file)
            if add_test_dir
            else input_file
        )
        input_path = Path(_file.replace('.json', file_ext))
        if input_path.exists():
            input_path.unlink()

    def _create_temp_json_file(self, data, file_name, compressed=False):
        """Create a temporary JSON file for testing."""
        file_path = Path(TESTDATA_DIR) / 'json' / file_name
        
        if compressed and file_name.endswith('.json'):
            file_name += '.gz'
            file_path = Path(TESTDATA_DIR) / 'json' / file_name
            
        if compressed:
            with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        return str(file_path)

    def test_analyze_json_file(self):
        """Test analyze_json_file utility function."""
        # Test with source file (has prompts)
        result = analyze_json_file(os.path.join(TESTDATA_DIR, 'json/mist25.json'))
        self.assertTrue(result['has_prompts'])
        self.assertFalse(result['has_answers'])
        self.assertGreater(len(result['taskids']), 0)
        
        # Test with hypothesis file (has answers)
        result_hyp = analyze_json_file(os.path.join(TESTDATA_DIR, 'json/mist25-hyp.json'))
        self.assertFalse(result_hyp['has_prompts'])
        self.assertTrue(result_hyp['has_answers'])
        self.assertGreater(len(result_hyp['taskids']), 0)

    def test_process_json_to_text(self):
        """Test process_json_to_text utility function."""
        # Test extracting source text (prompts)
        src_txt_path = os.path.join(TESTDATA_DIR, 'json/test_src.txt')
        success = process_json_to_text(
            os.path.join(TESTDATA_DIR, 'json/mist25.json'),
            src_txt_path,
            source=True
        )
        self.assertTrue(success)
        self.assertTrue(Path(src_txt_path).exists())
        
        with open(src_txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        self.assertGreater(len(lines), 0)
        
        # Clean up
        Path(src_txt_path).unlink()
        
        # Test extracting system answers
        hyp_txt_path = os.path.join(TESTDATA_DIR, 'json/test_hyp.txt')
        success = process_json_to_text(
            os.path.join(TESTDATA_DIR, 'json/mist25-hyp.json'),
            hyp_txt_path,
            system=True
        )
        self.assertTrue(success)
        self.assertTrue(Path(hyp_txt_path).exists())
        
        with open(hyp_txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        self.assertGreater(len(lines), 0)
        
        # Clean up
        Path(hyp_txt_path).unlink()

    def test_json_testset_creation(self):
        """Test that JSON testsets are created correctly."""
        self.assertEqual(self.testset.file_format, JSON_FILE)
        self.assertTrue(self.testset.src_file.name.endswith('mist25.json'))
        self.assertTrue(self.testset.ref_file.name.endswith('mist25-hyp.json'))

    def test_json_testset_text_file_creation(self):
        """Test that text files are created from JSON files."""
        # Force creation of text files
        self.testset._create_text_files()
        
        # Check that source text file was created
        src_txt_path = Path(TESTDATA_DIR) / 'json/mist25.txt'
        self.assertTrue(src_txt_path.exists())
        
        # Check that reference text file was created
        ref_txt_path = Path(TESTDATA_DIR) / 'json/mist25-hyp.txt'
        self.assertTrue(ref_txt_path.exists())
        
        # Verify content
        with open(src_txt_path, 'r', encoding='utf-8') as f:
            src_lines = f.readlines()
        with open(ref_txt_path, 'r', encoding='utf-8') as f:
            ref_lines = f.readlines()
            
        self.assertEqual(len(src_lines), len(ref_lines))
        self.assertGreater(len(src_lines), 0)

    def test_valid_json_submission(self):
        """Test creating a valid JSON submission."""
        # Create a test hypothesis file
        test_data = [
            {"taskid": "test_task_1", "answer": "Test answer 1"},
            {"taskid": "test_task_2", "answer": "Test answer 2"},
        ]
        
        # Create a corresponding source file for validation
        src_data = [
            {"taskid": "test_task_1", "prompt": "Test prompt 1"},
            {"taskid": "test_task_2", "prompt": "Test prompt 2"},
        ]
        
        hyp_file = self._create_temp_json_file(test_data, 'test_hyp_valid.json')
        src_file = self._create_temp_json_file(src_data, 'test_src_valid.json')
        
        # Create a testset with our test files
        test_testset = TestSet.objects.create(
            is_active=True,
            name='TestSetJSONValid',
            source_language=Language.objects.get(code='multi'),
            target_language=Language.objects.get(code='multi'),
            file_format=JSON_FILE,
            src_file=src_file,
            ref_file=None,
            competition=self.comp,
        )
        
        # Create submission
        sub = self._make_submission('json/test_hyp_valid.json', test_set=test_testset)
        
        self.assertEqual(sub.file_format, JSON_FILE)
        self.assertTrue(sub.is_valid)
        self.assertEqual(sub.test_set, test_testset)

    def test_json_submission_validation_schema(self):
        """Test JSON schema validation."""
        # Test invalid JSON (not an array)
        invalid_data = {"taskid": "test", "answer": "answer"}
        invalid_file = self._create_temp_json_file(invalid_data, 'test_invalid.json')
        
        with self.assertRaises(ValidationError):
            self._make_submission('json/test_invalid.json')

    def test_json_submission_validation_empty(self):
        """Test validation of empty JSON file."""
        # Create empty JSON file
        empty_file = Path(TESTDATA_DIR) / 'json/test_empty.json'
        empty_file.write_text('[]', encoding='utf-8')
        
        with self.assertRaises(ValidationError):
            self._make_submission('json/test_empty.json')

    def test_json_submission_validation_missing_answers(self):
        """Test validation of JSON file without answers."""
        # Create JSON file without answer fields
        no_answer_data = [
            {"taskid": "test_task_1", "prompt": "Test prompt 1"},
            {"taskid": "test_task_2", "prompt": "Test prompt 2"},
        ]
        no_answer_file = self._create_temp_json_file(no_answer_data, 'test_no_answer.json')
        
        with self.assertRaises(ValidationError):
            self._make_submission('json/test_no_answer.json')

    def test_json_submission_validation_mismatched_items(self):
        """Test validation when hypothesis and source have different number of items."""
        # Create hypothesis file with different number of items than source
        test_data = [
            {"taskid": "test_task_1", "answer": "Test answer 1"},
            # Missing second item
        ]
        
        src_data = [
            {"taskid": "test_task_1", "prompt": "Test prompt 1"},
            {"taskid": "test_task_2", "prompt": "Test prompt 2"},
        ]
        
        hyp_file = self._create_temp_json_file(test_data, 'test_hyp_wrong.json')
        src_file = self._create_temp_json_file(src_data, 'test_src_wrong.json')
        
        # Create a testset with our test files
        test_testset = TestSet.objects.create(
            is_active=True,
            name='TestSetJSONWrong',
            source_language=Language.objects.get(code='multi'),
            target_language=Language.objects.get(code='multi'),
            file_format=JSON_FILE,
            src_file=src_file,
            ref_file=None,
            competition=self.comp,
        )
        
        with self.assertRaises(ValidationError):
            self._make_submission('json/test_hyp_wrong.json', test_set=test_testset)

    def test_json_submission_compressed(self):
        """Test creating a JSON submission with compressed file."""
        # Create test data
        test_data = [
            {"taskid": "test_task_1", "answer": "Test answer 1"},
            {"taskid": "test_task_2", "answer": "Test answer 2"},
        ]
        
        src_data = [
            {"taskid": "test_task_1", "prompt": "Test prompt 1"},
            {"taskid": "test_task_2", "prompt": "Test prompt 2"},
        ]
        
        # Create compressed files
        hyp_file = self._create_temp_json_file(test_data, 'test_hyp_compressed.json', compressed=True)
        src_file = self._create_temp_json_file(src_data, 'test_src_compressed.json', compressed=True)
        
        # Create a testset with compressed files
        test_testset = TestSet.objects.create(
            is_active=True,
            name='TestSetJSONCompressed',
            source_language=Language.objects.get(code='multi'),
            target_language=Language.objects.get(code='multi'),
            file_format=JSON_FILE,
            src_file=src_file,
            ref_file=None,
            competition=self.comp,
        )
        
        # Create submission
        sub = self._make_submission('json/test_hyp_compressed.json.gz', test_set=test_testset)
        
        self.assertEqual(sub.file_format, JSON_FILE)
        self.assertTrue(sub.is_valid)

    def test_json_submission_file_extension_validation(self):
        """Test that submissions must have correct file extensions."""
        # Test with wrong extension
        test_data = [{"taskid": "test", "answer": "answer"}]
        
        # Create file with wrong extension
        wrong_ext_file = Path(TESTDATA_DIR) / 'json/test_wrong.txt'
        with open(wrong_ext_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        with self.assertRaises(ValidationError):
            sub = Submission(
                name='test_wrong.txt',
                original_name='test_wrong.txt',
                test_set=self.testset,
                submitted_by=self.team,
                file_format=JSON_FILE,
                hyp_file='json/test_wrong.txt',
            )
            sub.full_clean()

    def test_json_submission_text_extraction(self):
        """Test that text files are properly extracted from JSON submissions."""
        # Use the existing mist25-hyp.json file
        sub = self._make_submission('json/mist25-hyp.json')
        
        # Get hypothesis text
        hyp_text_path = sub.get_hyp_text(path_only=True)
        self.assertTrue(Path(hyp_text_path).exists())
        
        # Verify content
        hyp_lines = list(sub.get_hyp_text())
        self.assertGreater(len(hyp_lines), 0)
        
        # Get source text
        src_lines = list(sub.get_src_text())
        self.assertGreater(len(src_lines), 0)
        
        # Should have same number of lines
        self.assertEqual(len(hyp_lines), len(src_lines))

    def test_json_submission_with_references(self):
        """Test JSON submission with reference testset."""
        # Use testset with references
        sub = self._make_submission('json/mist25-hyp.json', test_set=self.testset)
        
        # Get reference text
        ref_text_path = sub.get_ref_text(path_only=True)
        self.assertTrue(Path(ref_text_path).exists())
        
        ref_lines = list(sub.get_ref_text())
        self.assertGreater(len(ref_lines), 0)

    def test_json_submission_without_references(self):
        """Test JSON submission with testset without references."""
        sub = self._make_submission('json/mist25-hyp.json', test_set=self.testset_noref)
        
        # Should return None for references
        ref_text = sub.get_ref_text()
        self.assertIsNone(ref_text)

    def test_json_src_testset_validation(self):
        """Test validation of JSON source testset files."""
        from leaderboard.models import validate_json_src_testset
        
        # Test with valid source file
        with open(os.path.join(TESTDATA_DIR, 'json/mist25.json'), 'rb') as f:
            mock_file = SimpleUploadedFile("mist25.json", f.read())
            mock_file.name = "mist25.json"
            
        # Should not raise an exception
        validate_json_src_testset(mock_file)

    def test_json_ref_testset_validation(self):
        """Test validation of JSON reference testset files."""
        from leaderboard.models import validate_json_ref_testset
        
        # Test with valid reference file
        with open(os.path.join(TESTDATA_DIR, 'json/mist25-hyp.json'), 'rb') as f:
            mock_file = SimpleUploadedFile("mist25-hyp.json", f.read())
            mock_file.name = "mist25-hyp.json"
            
        # Should not raise an exception
        validate_json_ref_testset(mock_file)

    def test_json_submission_validation(self):
        """Test validation of JSON submission files."""
        from leaderboard.models import validate_json_submission
        
        # Test with valid submission file
        with open(os.path.join(TESTDATA_DIR, 'json/mist25-hyp.json'), 'rb') as f:
            mock_file = SimpleUploadedFile("mist25-hyp.json", f.read())
            mock_file.name = "mist25-hyp.json"
            
        # Should not raise an exception
        validate_json_submission(mock_file)

    def test_json_schema_validation(self):
        """Test JSON schema validation."""
        from leaderboard.models import validate_json_schema
        
        # Test with valid JSON file
        with open(os.path.join(TESTDATA_DIR, 'json/mist25.json'), 'rb') as f:
            mock_file = SimpleUploadedFile("mist25.json", f.read())
            mock_file.name = "mist25.json"
            
        # Should not raise an exception
        validate_json_schema(mock_file)

    def test_json_testset_str_representation(self):
        """Test string representation of JSON testset."""
        expected = 'TestSetJSON test set (multi-multi)'
        self.assertEqual(str(self.testset), expected)

    def test_json_submission_str_representation(self):
        """Test string representation of JSON submission."""
        sub = self._make_submission('json/mist25-hyp.json')
        self.assertIn('submission', str(sub))
        self.assertIn(str(sub.id), str(sub))
