"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.conf import settings


def project_version(request):
    return {"project_version": settings.VERSION}
