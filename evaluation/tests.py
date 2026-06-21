"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import os
from datetime import datetime

from django.test import TestCase
from django.utils import timezone

from evaluation.views import _annotate_texts_with_span_diffs
from leaderboard.models import Competition
from leaderboard.models import Language
from leaderboard.models import SGML_FILE
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet
from leaderboard.models import TEXT_FILE
from ocelot.settings import BASE_DIR

TESTDATA_DIR = os.path.join(BASE_DIR, 'leaderboard/testdata')


class ComparisonTests(TestCase):
    """Tests submission output comparison."""

    def setUp(self):
        Language.objects.create(code='en', name='English')
        Language.objects.create(code='de', name='German')

        _next_year = datetime.now().year + 1
        self.competition = Competition.objects.create(
            is_active=True,
            name='MyCompetition',
            description='Description of the competition',
            deadline=datetime(_next_year, 1, 1, tzinfo=timezone.utc),
        )

        testset = TestSet.objects.create(
            is_active=True,
            name='MyTestSet',
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

        self.team_a = Team.objects.create(
            is_active=True,
            name='Team A',
            email='team-a@email.com',
        )

        file_1 = 'newstest2019.msft-WMT19-sentence-level.6785.en-de.txt'
        self.sub_1 = Submission.objects.create(
            name=file_1,
            test_set=testset,
            submitted_by=self.team_a,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, file_1),
        )

        self.team_b = Team.objects.create(
            is_active=True,
            name='Team B',
            email='team-b@email.com',
        )

        file_2 = 'newstest2019.msft-WMT19-sentence_document.6974.en-de.txt'
        self.sub_2 = Submission.objects.create(
            name=file_2,
            test_set=testset,
            submitted_by=self.team_b,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, file_2),
        )

        session = self.client.session
        session['ocelot_team_token'] = self.team_a.token
        session.save()

    def test_non_public_submissions_cannot_be_compared(self):
        """Checks that submission/a/b/ do not render for submissions that are not public."""
        self.sub_1.is_public = False  # Note sub_1 is submitted by team_a
        self.sub_1.save()
        self.sub_2.is_public = False  # Note sub_2 is submitted by team_b
        self.sub_2.save()
        response = self.client.get(
            '/submission/{0}/{1}'.format(self.sub_1.id, self.sub_2.id),
            follow=True,
        )
        self.assertContains(response, 'cannot be compared')
        self.assertContains(response, 'must be public')

    def test_submissions_from_different_test_sets_cannot_be_compared(self):
        """Checks that submission/a/b/ do not render for submissions from different test sets."""

        testset = TestSet.objects.create(
            is_active=True,
            name='AnotherTestSet',
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

        _file = 'newstest2019.msft-WMT19-sentence-level.6785.en-de.txt'
        sub_3 = Submission.objects.create(
            name=_file,
            test_set=testset,
            submitted_by=self.team_a,
            file_format=TEXT_FILE,
            hyp_file=os.path.join(TESTDATA_DIR, _file),
            is_public=True,
        )

        self.sub_1.is_public = True
        self.sub_1.save()

        response = self.client.get(
            '/submission/{0}/{1}'.format(self.sub_1.id, sub_3.id),
            follow=True,
        )
        self.assertContains(response, 'cannot be compared')
        self.assertContains(response, 'the same test set')

    def test_comparing_submissions_renders(self):
        """Checks that submission/a/b/ renders submission names and diff spans."""
        self.sub_1.is_public = True
        self.sub_1.save()
        self.sub_2.is_public = True
        self.sub_2.save()
        response = self.client.get(
            '/submission/{0}/{1}'.format(self.sub_1.id, self.sub_2.id)
        )
        self.assertContains(response, str(self.sub_1))
        self.assertContains(response, str(self.sub_2))
        self.assertContains(response, '<span class="diff')

    def test_submission_view_404_for_missing_submission(self):
        """The segment viewer returns 404 for a non-existent submission."""
        response = self.client.get('/submission/999999')
        self.assertEqual(response.status_code, 404)

    def test_submission_view_renders_public_submission(self):
        """A public submission renders in the segment viewer."""
        self.sub_2.is_public = True  # owned by team_b
        self.sub_2.save()
        response = self.client.get('/submission/{0}'.format(self.sub_2.id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.sub_2))

    def test_submission_view_hides_non_public_not_yours(self):
        """A non-public submission of another team is not viewable."""
        # Signed in as team_a (see setUp); sub_2 belongs to team_b and is private
        response = self.client.get(
            '/submission/{0}'.format(self.sub_2.id), follow=True
        )
        self.assertContains(response, 'not public')

    def test_submission_view_shows_your_own_private_submission(self):
        """Your own submission is viewable even when not public."""
        # Signed in as team_a (see setUp); sub_1 belongs to team_a and is private
        response = self.client.get('/submission/{0}'.format(self.sub_1.id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.sub_1))


class SpanDiffTests(TestCase):
    """Unit tests for _annotate_texts_with_span_diffs()."""

    def test_equal_texts_are_unchanged(self):
        """Identical texts get no diff annotations."""
        a, b = _annotate_texts_with_span_diffs('a b c', 'a b c')
        self.assertEqual(a, 'a b c')
        self.assertEqual(b, 'a b c')

    def test_empty_text_is_unchanged(self):
        """An empty text short-circuits without annotation."""
        a, b = _annotate_texts_with_span_diffs('', 'a b c')
        self.assertEqual(a, '')
        self.assertEqual(b, 'a b c')

    def test_word_replacement_marks_substitution(self):
        """A changed word is wrapped in a diff-sub span on both sides."""
        a, b = _annotate_texts_with_span_diffs('a b c', 'a B c')
        self.assertIn('diff-sub', a)
        self.assertIn('diff-sub', b)

    def test_insertion_marks_only_second_text(self):
        """An inserted word is marked as an insertion in the second text."""
        a, b = _annotate_texts_with_span_diffs('a c', 'a b c')
        self.assertNotIn('diff-ins', a)
        self.assertIn('diff-ins', b)

    def test_deletion_marks_only_first_text(self):
        """A deleted word is marked as a deletion in the first text."""
        a, b = _annotate_texts_with_span_diffs('a b c', 'a c')
        self.assertIn('diff-del', a)
        self.assertNotIn('diff-del', b)

    def test_char_based_diff(self):
        """Character-based diffing highlights character differences."""
        a, b = _annotate_texts_with_span_diffs('猫が好き', '犬が好き', char_based=True)
        self.assertIn('diff-sub', a)
        self.assertIn('diff-sub', b)
        # Characters are joined without spaces in char-based mode
        self.assertIn('が好き', a)
        self.assertIn('が好き', b)
