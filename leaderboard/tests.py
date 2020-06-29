"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from json import loads
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import TestCase

from leaderboard.models import TestSet


class LeaderboardTests(TestCase):
    """Tests leaderboard app."""

    def test_frontpage_renders_correctly(self):
        """Checks that frontpage renders correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_frontpage_contains_language_test_set_selectors(self):
        """Checks that frontpage contains selectors."""
        response = self.client.get('/')
        expected_selectors = (
            'source_language',
            'target_language',
            'test_set_name',
        )
        self.assertEqual(response.status_code, 200)
        for expected_selector in expected_selectors:
            self.assertContains(response, expected_selector)

    def test_frontpage_knows_about_test_sets(self):
        """Checks that frontpage retrieve list of test sets."""

        _msg = 'Need to implement test for Language and TestSet objects'
        with self.assertRaisesMessage(NotImplementedError, _msg):
            raise NotImplementedError(_msg)

    def test_testset_model_has_name_and_json_data(self):
        """Checks that TestSet model has name and JSON data."""

        _good = TestSet(name='foo', json_data='bar')
        self.assertEqual(_good.name, 'foo')
        self.assertEqual(_good.json_data, 'bar')

    def test_testset_needs_both_name_and_json_data(self):
        """Checks that TestSet model needs both name and JSON data."""

        _bad = TestSet()

        _msg = (
            "{'name': ['This field cannot be blank.'], "
            "'json_data': ['This field cannot be blank.']}"
        )
        with self.assertRaisesMessage(ValidationError, _msg):
            _bad.full_clean()

        _bad.name = 'foo'
        _msg = "{'json_data': ['This field cannot be blank.']}"
        with self.assertRaisesMessage(ValidationError, _msg):
            _bad.full_clean()

        _bad = TestSet()
        _bad.json_data = 'bar'
        _msg = "['This field contains invalid JSON.']"
        with self.assertRaisesMessage(ValidationError, _msg):
            _bad.full_clean()

        _good = TestSet(name='foo', json_data='{"valid": "json"}')
        _good.full_clean()

    def test_testset_can_validate_json_data(self):
        """Checks that TestSet model can validate JSON data."""

        _bad = TestSet(name='foo', json_data='bar')
        _msg = "['This field contains invalid JSON.']"
        with self.assertRaisesMessage(ValidationError, _msg):
            _bad.full_clean()

    def test_testset_validates_valid_json(self):
        """Checks that TestSet model validates valid JSON data."""

        json_path = Path(
            Path(__file__).parent, 'testdata', 'valid_data.json'
        )
        json_str = json_path.read_text(encoding='utf-8')

        _good = TestSet(name='foo', json_data=json_str)
        _good.full_clean()

        json_obj = loads(json_str)
        self.assertEqual(json_obj['json_version'], 1)
        self.assertEqual(json_obj['source_language'], 'eng')
        self.assertEqual(json_obj['target_language'], 'deu')
        self.assertEqual(json_obj['task_type'], 'translation')
        self.assertTrue('json_text_src' in json_obj)

        if 'json_text_ref' in json_obj:
            self.assertEqual(
                len(json_obj['json_text_src']),
                len(json_obj['json_text_ref']),
            )

        if 'json_auto_src' in json_obj:
            self.assertEqual(
                len(json_obj['json_auto_src']),
                len(json_obj['json_auto_ref']),
            )
