"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for automatic scoring: language-specific tokenization, QA accuracy and
sentinel score handling.
"""
import os
from datetime import datetime
from unittest import mock

from sacrebleu import corpus_bleu  # type: ignore

from .common import (
    TestCase, timezone, TESTDATA_DIR, Language, Competition,
    TestSet, Team, Submission, TEXT_FILE
)

SCORING = 'scoring'


class ScoringTests(TestCase):
    """Tests Submission scoring details."""

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='de', name='German')
        Language.objects.create(code='ja', name='Japanese')
        Language.objects.create(code='zh', name='Chinese')

        ny = datetime.now().year + 1
        self.comp = Competition.objects.create(
            is_active=True,
            name='CompetitionScoring',
            description='Description',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )

        self.team = Team.objects.create(
            is_active=True,
            is_verified=True,
            name='Team Scoring',
            email='scoring@team.com',
        )

    def _make_testset(self, name, tgt_code, src, ref):
        return TestSet.objects.create(
            is_active=True,
            name=name,
            source_language=Language.objects.get(code='en'),
            target_language=Language.objects.get(code=tgt_code),
            file_format=TEXT_FILE,
            src_file=os.path.join(TESTDATA_DIR, src),
            ref_file=os.path.join(TESTDATA_DIR, ref),
            competition=self.comp,
        )

    def _make_submission(self, testset, hyp):
        return Submission.objects.create(
            name=hyp,
            original_name=hyp,
            test_set=testset,
            submitted_by=self.team,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, hyp),
        )

    @staticmethod
    def _lines(path):
        with open(os.path.join(TESTDATA_DIR, path), encoding='utf-8') as f:
            return [line for line in f]

    def test_japanese_target_uses_char_tokenizer(self):
        """Japanese test sets score with the char tokenizer, not 13a."""
        testset = self._make_testset(
            'JaTestSet', 'ja', f'{SCORING}/ja-src.txt', f'{SCORING}/ja-ref.txt'
        )
        sub = self._make_submission(testset, f'{SCORING}/ja-hyp.txt')

        hyp = self._lines(f'{SCORING}/ja-hyp.txt')
        ref = self._lines(f'{SCORING}/ja-ref.txt')
        expected_char = corpus_bleu(hyp, [ref], tokenize='char').score
        expected_13a = corpus_bleu(hyp, [ref], tokenize='13a').score

        self.assertAlmostEqual(sub.score, expected_char, places=3)
        self.assertNotAlmostEqual(sub.score, expected_13a, places=3)

    def test_chinese_target_uses_zh_tokenizer(self):
        """Chinese test sets score with the zh tokenizer, not 13a."""
        testset = self._make_testset(
            'ZhTestSet', 'zh', f'{SCORING}/zh-src.txt', f'{SCORING}/zh-ref.txt'
        )
        sub = self._make_submission(testset, f'{SCORING}/zh-hyp.txt')

        hyp = self._lines(f'{SCORING}/zh-hyp.txt')
        ref = self._lines(f'{SCORING}/zh-ref.txt')
        expected_zh = corpus_bleu(hyp, [ref], tokenize='zh').score
        expected_13a = corpus_bleu(hyp, [ref], tokenize='13a').score

        self.assertAlmostEqual(sub.score, expected_zh, places=3)
        self.assertNotAlmostEqual(sub.score, expected_13a, places=3)

    def test_compute_accuracy_partial(self):
        """Exact-match accuracy returns the percentage of matching lines."""
        testset = self._make_testset(
            'AccTestSet', 'de', f'{SCORING}/disjoint-src.txt',
            f'{SCORING}/disjoint-ref.txt'
        )
        sub = self._make_submission(testset, f'{SCORING}/disjoint-hyp.txt')

        hyp = ['A\n', 'B\n', 'C\n', 'D\n']
        ref = ['A\n', 'X\n', 'C\n', 'Y\n']
        self.assertEqual(sub._compute_accuracy(hyp, ref), 50.0)

    def test_compute_accuracy_full_and_empty(self):
        """Accuracy is 100 for all matches and 0 for empty input."""
        testset = self._make_testset(
            'AccTestSet2', 'de', f'{SCORING}/disjoint-src.txt',
            f'{SCORING}/disjoint-ref.txt'
        )
        sub = self._make_submission(testset, f'{SCORING}/disjoint-hyp.txt')

        self.assertEqual(sub._compute_accuracy(['A\n', 'B\n'], ['A\n', 'B\n']), 100.0)
        self.assertEqual(sub._compute_accuracy([], []), 0.0)

    def test_disjoint_submission_gets_sentinel_score(self):
        """A zero-BLEU submission falls back to the -2 sentinel score."""
        testset = self._make_testset(
            'DisjointTestSet', 'de', f'{SCORING}/disjoint-src.txt',
            f'{SCORING}/disjoint-ref.txt'
        )
        sub = self._make_submission(testset, f'{SCORING}/disjoint-hyp.txt')
        # corpus BLEU is exactly 0 for disjoint vocabularies -> -2 sentinel
        self.assertEqual(sub.score, -2)

    def test_qa_testset_triggers_accuracy_branch(self):
        """A '-qa' test set with zero BLEU computes accuracy (0 here -> -2)."""
        testset = self._make_testset(
            'Acc-QA-TestSet', 'de', f'{SCORING}/disjoint-src.txt',
            f'{SCORING}/disjoint-ref.txt'
        )
        sub = self._make_submission(testset, f'{SCORING}/disjoint-hyp.txt')
        # No exact matches -> accuracy 0 -> sentinel -2
        self.assertEqual(sub.score, -2)

    def test_score_computed_once_and_persisted(self):
        """Scoring runs exactly once on create, is persisted via a targeted
        write, and is not recomputed when the submission is saved again."""
        testset = self._make_testset(
            'IdempotentTestSet', 'ja', f'{SCORING}/ja-src.txt',
            f'{SCORING}/ja-ref.txt'
        )

        original = Submission._compute_score
        with mock.patch.object(
            Submission, '_compute_score', autospec=True, side_effect=original
        ) as spy:
            sub = self._make_submission(testset, f'{SCORING}/ja-hyp.txt')

            # Scored exactly once during creation.
            self.assertEqual(spy.call_count, 1)
            # A real (non-sentinel) score was computed...
            self.assertNotIn(sub.score, (-1, -2))
            self.assertGreater(sub.score, 0)
            # ...and persisted by the targeted update_fields write.
            self.assertAlmostEqual(
                Submission.objects.get(pk=sub.pk).score, sub.score, places=6
            )

            # Re-saving (e.g. set_primary) must not recompute the score.
            sub.set_primary()
            self.assertEqual(spy.call_count, 1)
