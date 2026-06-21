"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for authentication/session flows: signup, signin, signout, welcome.
"""
from datetime import datetime

from .common import (
    TestCase, timezone, Competition, Team
)


class AuthFlowTests(TestCase):
    """Tests team signup/signin/signout/welcome views."""

    def setUp(self):
        ny = datetime.now().year + 1
        Competition.objects.create(
            is_active=True,
            name='CompetitionAuth',
            description='Description',
            deadline=datetime(ny, 1, 1, tzinfo=timezone.utc),
        )
        self.team = Team.objects.create(
            is_active=True,
            is_verified=True,
            name='Existing Team',
            email='existing@team.com',
        )

    def _signin_session(self):
        session = self.client.session
        session['ocelot_team_token'] = self.team.token
        session.save()

    # ---- signup --------------------------------------------------------

    def test_signup_get_renders(self):
        """The signup page renders for anonymous users."""
        response = self.client.get('/signup')
        self.assertEqual(response.status_code, 200)

    def test_signup_creates_team_and_signs_in(self):
        """Posting valid signup data creates a team and starts a session."""
        response = self.client.post(
            '/signup',
            {'name': 'Brand New Team', 'email': 'new@team.com'},
            follow=True,
        )
        self.assertTrue(Team.objects.filter(name='Brand New Team').exists())
        self.assertIsNotNone(self.client.session.get('ocelot_team_token'))
        self.assertContains(response, 'successfully signed up')

    def test_signup_when_already_signed_in_redirects(self):
        """Signed-in users cannot sign up again."""
        self._signin_session()
        response = self.client.get('/signup', follow=True)
        self.assertContains(response, 'already signed up')

    # ---- signin --------------------------------------------------------

    def test_signin_get_renders(self):
        """The sign-in page renders for anonymous users."""
        response = self.client.get('/sign-in')
        self.assertEqual(response.status_code, 200)

    def test_signin_success(self):
        """Correct credentials start a session."""
        response = self.client.post(
            '/sign-in',
            {
                'name': self.team.name,
                'email': self.team.email,
                'token': self.team.token,
            },
            follow=True,
        )
        self.assertContains(response, 'successfully signed in')
        self.assertEqual(
            self.client.session.get('ocelot_team_token'), self.team.token
        )

    def test_signin_failure_with_wrong_token(self):
        """Wrong (but well-formed) credentials fail to sign in."""
        response = self.client.post(
            '/sign-in',
            {
                'name': self.team.name,
                'email': self.team.email,
                'token': 'abcdef0123',  # valid format, not the team's token
            },
            follow=True,
        )
        self.assertContains(response, 'sign in attempt failed')
        self.assertIsNone(self.client.session.get('ocelot_team_token'))

    def test_signin_when_already_signed_in_redirects(self):
        """Signed-in users are told they are already signed in."""
        self._signin_session()
        response = self.client.get('/sign-in', follow=True)
        self.assertContains(response, 'already signed in')

    # ---- signout -------------------------------------------------------

    def test_signout_clears_session(self):
        """Signing out clears the session token."""
        self._signin_session()
        response = self.client.get('/sign-out', follow=True)
        self.assertContains(response, 'successfully signed out')
        self.assertIsNone(self.client.session.get('ocelot_team_token'))

    # ---- welcome -------------------------------------------------------

    def test_welcome_requires_signin(self):
        """The welcome page redirects anonymous users."""
        response = self.client.get('/welcome', follow=True)
        self.assertContains(response, 'need to be signed in')

    def test_welcome_shows_token(self):
        """The welcome page shows the team token when signed in."""
        self._signin_session()
        response = self.client.get('/welcome')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team.token)
