"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.contrib import admin

from leaderboard.models import Language, TestSet


class LanguageAdmin(admin.ModelAdmin):
    """Model admin for Language objects."""

    fields = ['code', 'name']


class TestSetAdmin(admin.ModelAdmin):
    """Model admin for TestSet objects."""

    fields = ['name']


admin.site.register(Language, LanguageAdmin)
admin.site.register(TestSet, TestSetAdmin)
