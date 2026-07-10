"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for the staff-only file upload view.
"""
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from .common import MEDIA_ROOT, TestCase


class UploadViewTests(TestCase):
    """Tests the staff-only /upload page."""

    def setUp(self):
        self.url = reverse('upload-view')
        self.uploads_dir = Path(MEDIA_ROOT) / 'uploads'

    def tearDown(self):
        for name in ('upload_test.txt', 'upload_test_2.txt'):
            for path in self.uploads_dir.glob(name.replace('.txt', '*')):
                path.unlink()

    def _make_staff(self):
        user = get_user_model().objects.create_user(
            username='staffer', password='pw', is_staff=True
        )
        self.client.force_login(user)
        return user

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # redirect to admin login

    def test_non_staff_denied(self):
        user = get_user_model().objects.create_user(
            username='plain', password='pw', is_staff=False
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_staff_can_view_form(self):
        self._make_staff()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload a file')

    def test_staff_can_upload_file(self):
        self._make_staff()
        upload = SimpleUploadedFile(
            'upload_test.txt', b'hello world', content_type='text/plain'
        )
        response = self.client.post(self.url, {'file': upload})
        self.assertEqual(response.status_code, 302)
        self.assertTrue((self.uploads_dir / 'upload_test.txt').exists())

    def test_post_without_file_warns(self):
        self._make_staff()
        response = self.client.post(self.url, {}, follow=True)
        self.assertContains(response, 'No file selected')
