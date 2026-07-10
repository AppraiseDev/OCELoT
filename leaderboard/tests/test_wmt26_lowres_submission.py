"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Submission model tests for WMT26 low-resource LLM JSONL test sets.

The fixtures in leaderboard/testdata/jsonl-wmt26-lowres are short, synthetic
stand-ins for the official shared-task files. They preserve the official field
names, mixed dataset_id layout, and task-specific metrics without committing
private gold text.
"""
import json
import os
from datetime import datetime
from pathlib import Path

from sacrebleu import corpus_chrf  # type: ignore

from leaderboard.models import validate_jsonl_ref_testset
from leaderboard.models import validate_jsonl_schema
from leaderboard.models import validate_jsonl_src_testset
from leaderboard.models import validate_jsonl_submission
from leaderboard.utils import JSONL_WMT26_LR_GC_FORMAT
from leaderboard.utils import JSONL_WMT26_LR_MR_FORMAT
from leaderboard.utils import JSONL_WMT26_LR_MT_FORMAT
from leaderboard.utils import JSONL_WMT26_LR_QA_FORMAT
from leaderboard.utils import JSONL_WMT26_LR_SC_FORMAT
from leaderboard.utils import analyze_jsonl_file
from leaderboard.utils import detect_jsonl_format

from .common import (
    Competition, JSONL_FILE, MEDIA_ROOT, Submission, Team, TestCase, TestSet,
    TESTDATA_DIR, timezone,
)

LOWRES_DIR = 'jsonl-wmt26-lowres'


class WMT26LowResourceSubmissionTests(TestCase):
    """Tests the WMT26 low-resource JSONL task family."""

    def setUp(self):
        ny = datetime.now().year + 1
        self.comp = Competition.objects.create(
            is_active=True,
            name='CompetitionWMT26LowResource',
            description='Description of the WMT26 low-resource competition',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )
        self.team = Team.objects.create(
            is_active=True,
            is_verified=True,
            name='Team WMT26 LowResource',
            email='wmt26-lowresource@team.com',
        )
        self.created_testsets = []

    def tearDown(self):
        testdata_dir = Path(TESTDATA_DIR) / LOWRES_DIR
        for path in testdata_dir.glob('*.txt'):
            path.unlink()
        for path in testdata_dir.glob('*.generated.jsonl'):
            path.unlink()

        submissions_dir = Path(MEDIA_ROOT) / 'submissions'
        if submissions_dir.exists():
            for path in submissions_dir.glob('wmt26_lowresource_*'):
                path.unlink()

    def _path(self, file_name):
        return os.path.join(TESTDATA_DIR, LOWRES_DIR, file_name)

    def _open(self, file_name):
        return open(self._path(file_name), 'rb')

    def _make_testset(self, task_name):
        testset = TestSet.objects.create(
            is_active=True,
            name=f'WMT26 LowResource {task_name}',
            file_format=JSONL_FILE,
            src_file=self._path(f'{task_name}.gold.jsonl'),
            ref_file=self._path(f'{task_name}.gold.jsonl'),
            competition=self.comp,
        )
        self.created_testsets.append(testset)
        return testset

    def _make_submission(self, testset, file_name):
        sub = Submission(
            name=file_name,
            original_name=file_name,
            test_set=testset,
            submitted_by=self.team,
            file_format=JSONL_FILE,
            hyp_file=self._path(file_name),
        )
        sub.full_clean()
        sub.save()
        return sub

    def _write_perfect_mt_submission(self):
        src = Path(self._path('ukr_mt_test.gold.jsonl'))
        dst = Path(self._path('ukr_mt_test.perfect.generated.jsonl'))
        with src.open(encoding='utf-8') as fin, dst.open('w', encoding='utf-8') as fout:
            for line in fin:
                obj = json.loads(line)
                fout.write(json.dumps({
                    'dataset_id': obj['dataset_id'],
                    'sent_id': obj['sent_id'],
                    'source': obj['source'],
                    'pred': obj['target'],
                }) + '\n')
        return dst.name

    def test_detects_all_low_resource_task_formats(self):
        cases = {
            'sb_mt_test.gold.jsonl': JSONL_WMT26_LR_MT_FORMAT,
            'ukr_mt_test.dummy.jsonl': JSONL_WMT26_LR_MT_FORMAT,
            'sb_qa_test.gold.jsonl': JSONL_WMT26_LR_QA_FORMAT,
            'ukr_qa_test.dummy.jsonl': JSONL_WMT26_LR_QA_FORMAT,
            'sb_sc_test.gold.jsonl': JSONL_WMT26_LR_SC_FORMAT,
            'ukr_gc_test.dummy.jsonl': JSONL_WMT26_LR_GC_FORMAT,
            'sb_mr_test.gold.jsonl': JSONL_WMT26_LR_MR_FORMAT,
        }
        for file_name, expected in cases.items():
            with self.subTest(file_name=file_name):
                self.assertEqual(detect_jsonl_format(self._path(file_name)), expected)

    def test_validators_accept_gold_and_dummy_files(self):
        task_names = [
            'sb_mt_test', 'ukr_mt_test', 'sb_qa_test', 'ukr_qa_test',
            'sb_sc_test', 'ukr_sc_test', 'sb_gc_test', 'ukr_gc_test',
            'sb_mr_test', 'ukr_mr_test',
        ]
        for task_name in task_names:
            with self.subTest(task_name=task_name):
                gold_name = f'{task_name}.gold.jsonl'
                dummy_name = f'{task_name}.dummy.jsonl'
                with self._open(gold_name) as file_obj:
                    validate_jsonl_schema(file_obj)
                with self._open(gold_name) as file_obj:
                    validate_jsonl_src_testset(file_obj)
                with self._open(gold_name) as file_obj:
                    validate_jsonl_ref_testset(file_obj)
                with self._open(dummy_name) as file_obj:
                    validate_jsonl_schema(file_obj)
                with self._open(dummy_name) as file_obj:
                    validate_jsonl_submission(file_obj)

    def test_analyze_jsonl_file_detects_references_and_systems(self):
        gold = analyze_jsonl_file(self._path('ukr_sc_test.gold.jsonl'))
        dummy = analyze_jsonl_file(self._path('ukr_sc_test.dummy.jsonl'))

        self.assertEqual(gold['translators'], {'True'})
        self.assertEqual(gold['systems'], set())
        self.assertEqual(dummy['translators'], set())
        self.assertEqual(dummy['systems'], {'True'})

    def test_extracts_accuracy_targets_from_jsonl(self):
        testset = self._make_testset('ukr_sc_test')
        sub = self._make_submission(testset, 'ukr_sc_test.dummy.jsonl')

        ref_lines = [line.strip() for line in sub.get_ref_text()]
        hyp_lines = [line.strip() for line in sub.get_hyp_text()]
        self.assertEqual(ref_lines[0], 'CORRECT\tCORRECT')
        self.assertEqual(ref_lines[1], 'recieve\treceive')
        self.assertEqual(hyp_lines[0], 'pred\tpred')
        self.assertEqual(len(ref_lines), len(hyp_lines))

    def test_mt_uses_chrfpp_for_low_resource_task(self):
        testset = self._make_testset('ukr_mt_test')
        perfect_name = self._write_perfect_mt_submission()
        sub = self._make_submission(testset, perfect_name)

        hyp_stream = list(sub.get_hyp_text())
        ref_stream = list(sub.get_ref_text())
        expected_chrfpp = corpus_chrf(hyp_stream, [ref_stream], word_order=2).score

        self.assertTrue(sub.is_valid)
        self.assertAlmostEqual(sub.score, 100.0, places=3)
        self.assertAlmostEqual(sub.score_chrf, expected_chrfpp, places=3)

    def test_qa_accuracy_handles_zero_indexed_answers(self):
        testset = self._make_testset('ukr_qa_test')
        sub = self._make_submission(testset, 'ukr_qa_test.dummy.jsonl')

        self.assertTrue(sub.is_valid)
        self.assertEqual(sub.score, 16.7)
        self.assertIsNone(sub.score_chrf)

    def test_mr_zero_accuracy_is_preserved(self):
        testset = self._make_testset('ukr_mr_test')
        sub = self._make_submission(testset, 'ukr_mr_test.dummy.jsonl')

        self.assertTrue(sub.is_valid)
        self.assertEqual(sub.score, 0.0)
        self.assertIsNone(sub.score_chrf)

    def test_mixed_dataset_ids_remain_one_testset(self):
        testset = self._make_testset('sb_mt_test')
        sub = self._make_submission(testset, 'sb_mt_test.dummy.jsonl')

        src_segments = list(sub.get_src_text())
        hyp_segments = list(sub.get_hyp_text())
        self.assertEqual(len(src_segments), 12)
        self.assertEqual(len(hyp_segments), 12)
        self.assertTrue(sub.is_valid)
