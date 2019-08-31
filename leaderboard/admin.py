"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.contrib import admin

from leaderboard.models import Language, Submission, TestSet


class LanguageAdmin(admin.ModelAdmin):
    """Model admin for Language objects."""

    fields = ['code', 'name']


class SubmissionAdmin(admin.ModelAdmin):
    """Model admin for Submission objects."""

    fields = ['name', 'test_set', 'is_primary', 'sgml_file', 'score']

    list_display = ['__str__', 'test_set', 'score']

    ordering = ('-score',)


class TestSetAdmin(admin.ModelAdmin):
    """Model admin for TestSet objects."""

    fields = ['name']


admin.site.register(Language, LanguageAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(TestSet, TestSetAdmin)
