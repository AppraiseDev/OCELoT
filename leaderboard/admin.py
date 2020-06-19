"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.contrib import admin

from leaderboard.models import Language
from leaderboard.models import Submission
from leaderboard.models import TestSet


class LanguageAdmin(admin.ModelAdmin):
    """Model admin for Language objects."""

    fields = ['code', 'name']


class SubmissionAdmin(admin.ModelAdmin):
    """Model admin for Submission objects."""

    fields = ['name', 'test_set', 'is_primary', 'sgml_file', 'score']

    list_display = ['__str__', 'test_set', '_source_language', '_target_language', 'score']

    ordering = ('-score',)


class TestSetAdmin(admin.ModelAdmin):
    """Model admin for TestSet objects."""

    fields = ['name', 'source_language', 'target_language', 'sgml_file']

    list_display = ['__str__', 'source_language', 'target_language']

    ordering = ('-name', 'source_language', 'target_language')


admin.site.register(Language, LanguageAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(TestSet, TestSetAdmin)
