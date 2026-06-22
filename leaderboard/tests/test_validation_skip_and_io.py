"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Regression tests for performance fixes #5 (temp-file cleanup helper) and
#6 (validate=False skips the expensive hyp_file field validators).
"""
import gzip
import io
import os
import tempfile
from datetime import datetime
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition,
    TestSet, Team, Submission, JSONL_FILE,
)
from leaderboard.models import ValidationError
from leaderboard.models.formats._io import open_uploaded_text


class OpenUploadedTextTests(SimpleTestCase):
    """#5: in-memory .gz uploads are read and their temp file is cleaned up."""

    def test_in_memory_gz_is_read_and_temp_file_removed(self):
        raw = b'{"a": 1}\n{"a": 2}\n'
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='wb') as gz:
            gz.write(raw)
        upload = SimpleUploadedFile('x.jsonl.gz', buf.getvalue())
        # In-memory uploads do not expose a temporary_file_path().
        self.assertFalse(hasattr(upload, 'temporary_file_path'))

        prev_tmpdir = tempfile.tempdir
        scratch = tempfile.mkdtemp()
        tempfile.tempdir = scratch
        try:
            with open_uploaded_text(upload, suffix='.jsonl.gz') as stream:
                lines = [line.strip() for line in stream]
                # While open, a spilled temp file exists in the scratch dir.
                self.assertTrue(os.listdir(scratch))
            self.assertEqual(lines, ['{"a": 1}', '{"a": 2}'])
            # After the context manager exits, nothing is left behind.
            self.assertEqual(os.listdir(scratch), [])
        finally:
            tempfile.tempdir = prev_tmpdir
            os.rmdir(scratch)


class ValidateFlagSkipsFieldValidatorsTests(TestCase):
    """#6: validate=False skips the expensive hyp_file field validators."""

    # A single GenMT line that passes the JSONL schema...
    SRC_LINE = '{"doc_id": "d1", "tgt_lang": "ha", "src_text": "hello"}\n'
    # ...but has no hypothesis, so validate_jsonl_submission would reject it.
    HYP_LINE = '{"doc_id": "d1", "tgt_lang": "ha", "src_text": "hello"}\n'

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='ha', name='Hausa')
        ny = datetime.now().year + 1
        self.comp = Competition.objects.create(
            is_active=True,
            name='CompetitionSkip',
            description='Skip-validation competition',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )

        self.src_path = os.path.join(TESTDATA_DIR, 'jsonl/skiptest-src.jsonl')
        self.hyp_path = os.path.join(TESTDATA_DIR, 'jsonl/skiptest-hyp.jsonl')
        with open(self.src_path, 'w', encoding='utf-8') as f:
            f.write(self.SRC_LINE)
        with open(self.hyp_path, 'w', encoding='utf-8') as f:
            f.write(self.HYP_LINE)

        self.team = Team.objects.create(
            is_active=True, is_verified=True,
            name='Team Skip', email='skip@team.com',
        )

    def tearDown(self):
        for path in (
            self.src_path,
            self.hyp_path,
            os.path.join(TESTDATA_DIR, 'jsonl/skiptest-src.txt'),
            os.path.join(TESTDATA_DIR, 'jsonl/skiptest-hyp.txt'),
        ):
            p = Path(path)
            if p.exists():
                p.unlink()

    def _make_testset(self, name, validate):
        return TestSet.objects.create(
            is_active=True,
            name=name,
            validate=validate,
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code='ha'),
            file_format=JSONL_FILE,
            src_file=self.src_path,
            ref_file=None,
            competition=self.comp,
        )

    def _submission_for(self, test_set):
        return Submission(
            name='skip-sub',
            original_name='skip-sub',
            test_set=test_set,
            submitted_by=self.team,
            file_format=JSONL_FILE,
            hyp_file=self.hyp_path,
        )

    def test_validate_true_rejects_invalid_hyp(self):
        test_set = self._make_testset('TestSetValidateTrue', validate=True)
        sub = self._submission_for(test_set)
        with self.assertRaises(ValidationError):
            sub.full_clean()

    def test_validate_false_accepts_invalid_hyp(self):
        test_set = self._make_testset('TestSetValidateFalse', validate=False)
        sub = self._submission_for(test_set)
        # Should not raise: the hyp_file field validators are skipped.
        sub.full_clean()
