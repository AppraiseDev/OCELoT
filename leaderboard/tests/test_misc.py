"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for static pages (updates, download) and view helper functions.
"""
from datetime import datetime
from types import SimpleNamespace

from leaderboard.views import _format_datetime_for_js
from leaderboard.views import _get_team_data

from .common import TestCase, timezone, Team


class StaticViewTests(TestCase):
    """Tests the updates and download pages."""

    def test_updates_page_renders(self):
        """The updates page renders for anonymous users."""
        response = self.client.get('/updates')
        self.assertEqual(response.status_code, 200)

    def test_download_page_renders(self):
        """The download page renders for anonymous users."""
        response = self.client.get('/download')
        self.assertEqual(response.status_code, 200)


class ViewHelperTests(TestCase):
    """Tests view helper functions."""

    def test_get_team_data_without_token(self):
        """Without a session token, no team data is returned."""
        request = SimpleNamespace(session={})
        name, email, token, verified = _get_team_data(request)
        self.assertIsNone(name)
        self.assertIsNone(email)
        self.assertIsNone(token)
        self.assertFalse(verified)

    def test_get_team_data_with_token(self):
        """A valid session token resolves to the team's data."""
        team = Team.objects.create(
            is_active=True,
            is_verified=True,
            name='Helper Team',
            email='helper@team.com',
        )
        request = SimpleNamespace(session={'ocelot_team_token': team.token})
        name, email, token, verified = _get_team_data(request)
        self.assertEqual(name, team.name)
        self.assertEqual(email, team.email)
        self.assertEqual(token, team.token)
        self.assertTrue(verified)

    def test_format_datetime_for_js_none(self):
        """A missing timestamp formats to None."""
        self.assertIsNone(_format_datetime_for_js(None))

    def test_format_datetime_for_js_value(self):
        """A timestamp formats to a readable string."""
        stamp = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        formatted = _format_datetime_for_js(stamp)
        self.assertIn('2026-01-02', formatted)
        self.assertIn('03:04:05', formatted)
