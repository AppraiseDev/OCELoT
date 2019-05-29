"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.contrib import admin

from leaderboard.models import Language


class LanguageAdmin(admin.ModelAdmin):
    """Model admin for Language objects."""
    fields = ['code', 'name']


admin.site.register(Language, LanguageAdmin)
