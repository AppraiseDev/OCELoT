"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Submission model tests for WMT26-format (GenMT) test sets.

WMT26 reuses the General MT JSONL path but drops 'dataset_id'/'src_lang' and
renames 'src_text' to 'source_doc'. Crucially, WMT26 documents separate
sentences with HTML tags (e.g. <p>...</p>) instead of newline characters, so
each document is extracted, displayed and compared as a single segment.

The test data in leaderboard/testdata/jsonl/wmt26-*.jsonl is fake/converted so
that the official blind set is never committed to the repository.
"""
import os
from datetime import datetime
from pathlib import Path

from evaluation.views import _annotate_texts_with_span_diffs
from leaderboard.models import ValidationError
from leaderboard.models import validate_jsonl_schema
from leaderboard.models import validate_jsonl_src_testset
from leaderboard.models import validate_jsonl_submission
from leaderboard.utils import JSONL_WMT_GENMT_FORMAT
from leaderboard.utils import detect_jsonl_format

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition,
    TestSet, Team, Submission, JSONL_FILE, MEDIA_ROOT
)


class WMT26SubmissionTests(TestCase):
    """Tests the generalized GenMT path against WMT26-format files."""

    def setUp(self):
        ny = datetime.now().year + 1
        self.comp = Competition.objects.create(
            is_active=True,
            name='CompetitionWMT26',
            description='Description of the WMT26 competition',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )

        # WMT26 is multi-target and human-eval only: no languages, no
        # references, no automatic scoring.
        self.testset = TestSet.objects.create(
            is_active=True,
            name='TestSetWMT26',
            file_format=JSONL_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'jsonl/wmt26-src.jsonl'),
            ref_file=None,
            compute_scores=False,
            competition=self.comp,
        )

        self.team = Team.objects.create(
            is_active=True,
            is_verified=True,
            name='Team WMT26',
            email='wmt26@team.com',
        )

    def tearDown(self):
        # Only remove generated artifacts; never the committed test data.
        generated = [
            'jsonl/wmt26-src.txt',
            'jsonl/wmt26-hyp-a.txt',
            'jsonl/wmt26-hyp-b.txt',
            'jsonl/wmt26-hyp-short.jsonl',
            'jsonl/wmt26-hyp-short.txt',
        ]
        for fname in generated:
            p = Path(TESTDATA_DIR) / fname
            if p.exists():
                p.unlink()

        # Remove submission files uploaded via the submit form
        submissions_dir = Path(MEDIA_ROOT) / 'submissions'
        if submissions_dir.exists():
            for p in submissions_dir.glob('testsetwmt26.*'):
                p.unlink()

    def _signin(self):
        session = self.client.session
        session['ocelot_team_token'] = self.team.token
        session.save()

    def _make_submission(self, file_name, test_set=None):
        hyp_path = os.path.join(TESTDATA_DIR, file_name)
        sub = Submission(
            name=file_name,
            original_name=file_name,
            test_set=test_set or self.testset,
            submitted_by=self.team,
            file_format=JSONL_FILE,
            hyp_file=hyp_path,
        )
        sub.full_clean()
        sub.save()
        return sub

    def _open(self, file_name):
        return open(os.path.join(TESTDATA_DIR, file_name), 'rb')

    # ------------------------------------------------------------------
    # Format detection (covers the generalized detect_jsonl_format)
    # ------------------------------------------------------------------

    def test_wmt26_source_detected_as_genmt(self):
        """WMT26 source (no dataset_id, has source_doc) is GenMT format."""
        path = os.path.join(TESTDATA_DIR, 'jsonl/wmt26-src.jsonl')
        self.assertEqual(detect_jsonl_format(path), JSONL_WMT_GENMT_FORMAT)

    def test_wmt26_submission_detected_as_genmt(self):
        """WMT26 submission (doc_id, tgt_lang, hypothesis) is GenMT format."""
        path = os.path.join(TESTDATA_DIR, 'jsonl/wmt26-hyp-a.jsonl')
        self.assertEqual(detect_jsonl_format(path), JSONL_WMT_GENMT_FORMAT)

    # ------------------------------------------------------------------
    # Validators accept WMT26 (covers relaxed schema + src validation)
    # ------------------------------------------------------------------

    def test_wmt26_src_validation_passes_without_src_lang(self):
        """Source validation no longer requires src_lang for WMT26."""
        with self._open('jsonl/wmt26-src.jsonl') as f:
            validate_jsonl_src_testset(f)  # should not raise

    def test_wmt26_submission_schema_passes_without_dataset_id(self):
        """Schema validation no longer requires dataset_id for WMT26."""
        with self._open('jsonl/wmt26-hyp-a.jsonl') as f:
            validate_jsonl_schema(f)  # should not raise
        with self._open('jsonl/wmt26-hyp-a.jsonl') as f:
            validate_jsonl_submission(f)  # should not raise

    # ------------------------------------------------------------------
    # Test set + submission flow
    # ------------------------------------------------------------------

    def test_wmt26_testset_extracts_source_as_one_segment_per_doc(self):
        """HTML-separated documents are extracted one segment per document."""
        src_txt = Path(self.testset.src_file.name.replace('.jsonl', '.txt'))
        self.assertTrue(src_txt.exists())
        lines = src_txt.read_text(encoding='utf-8').splitlines()
        # 5 documents in the source -> 5 segments (HTML tags are NOT split)
        self.assertEqual(len(lines), 5)
        self.assertIn('<p>', lines[0])
        # The whole document remains a single segment despite multiple <p> tags
        self.assertGreaterEqual(lines[0].count('<p>'), 2)

    def test_wmt26_submission_accepted_and_valid(self):
        """A well-formed WMT26 submission is accepted, valid, and unscored."""
        sub = self._make_submission('jsonl/wmt26-hyp-a.jsonl')
        self.assertTrue(sub.is_valid)
        # No references -> no automatic scores
        self.assertIsNone(sub.score)
        self.assertIsNone(sub.score_chrf)
        # Submission file stored under MEDIA_ROOT
        media_file = Path(MEDIA_ROOT) / sub.hyp_file.name
        self.assertTrue(media_file.exists(), f"{media_file} does not exist")

    def test_wmt26_segments_align_with_source(self):
        """Extracted hyp/src segment counts match (one per document)."""
        sub = self._make_submission('jsonl/wmt26-hyp-a.jsonl')
        src_segments = list(sub.get_src_text())
        hyp_segments = list(sub.get_hyp_text())
        self.assertEqual(len(src_segments), 5)
        self.assertEqual(len(hyp_segments), 5)
        # HTML markup is preserved inside each extracted segment
        self.assertIn('<p>', hyp_segments[0])

    def test_wmt26_short_submission_rejected(self):
        """A WMT26 submission with fewer lines than the source is rejected."""
        src = Path(TESTDATA_DIR) / 'jsonl/wmt26-hyp-a.jsonl'
        dst = Path(TESTDATA_DIR) / 'jsonl/wmt26-hyp-short.jsonl'
        lines = src.read_text(encoding='utf-8').splitlines()[:2]
        dst.write_text('\n'.join(lines) + '\n', encoding='utf-8')

        with self.assertRaises(ValidationError) as cm:
            self._make_submission('jsonl/wmt26-hyp-short.jsonl')
        self.assertIn('hyp', str(cm.exception))

    # ------------------------------------------------------------------
    # Comparison of outputs (HTML documents compared as single segments)
    # ------------------------------------------------------------------

    def test_wmt26_comparison_highlights_differences(self):
        """Two WMT26 submissions can be compared segment by segment."""
        sub_a = self._make_submission('jsonl/wmt26-hyp-a.jsonl')
        sub_b = self._make_submission('jsonl/wmt26-hyp-b.jsonl')

        pairs = list(zip(sub_a.get_hyp_text(), sub_b.get_hyp_text()))
        self.assertEqual(len(pairs), 5)

        text_a, text_b = pairs[0]
        ann_a, ann_b = _annotate_texts_with_span_diffs(
            text_a.strip(), text_b.strip()
        )
        # "Translated" vs "Output" differ, so a diff span is produced
        self.assertIn('diff', ann_a)
        self.assertIn('diff', ann_b)

    # ------------------------------------------------------------------
    # End-to-end submit() form path
    # ------------------------------------------------------------------

    def test_wmt26_submission_via_submit_form(self):
        """A WMT26 JSONL file can be submitted through the submit() view."""
        self._signin()
        with self._open('jsonl/wmt26-hyp-a.jsonl') as f:
            response = self.client.post('/submit', {
                'test_set': self.testset.id,
                'hyp_file': f,
            }, follow=True)

        self.assertContains(response, 'successfully submitted')
        sub = Submission.objects.filter(submitted_by=self.team).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.file_format, JSONL_FILE)
        self.assertTrue(sub.is_valid)
