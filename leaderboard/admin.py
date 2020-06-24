"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.contrib import admin

from leaderboard.models import Language
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet


class LanguageAdmin(admin.ModelAdmin):
    """Model admin for Language objects."""

    fields = ['code', 'name']


class SubmissionAdmin(admin.ModelAdmin):
    """Model admin for Submission objects."""

    fields = [
        'name',
        'test_set',
        'sgml_file',
        'submitted_by',
        'is_primary',
        'is_public',
        'score',
    ]

    list_display = [
        '__str__',
        'test_set',
        '_source_language',
        '_target_language',
        '_score',
    ]

    list_filter = [
        'test_set',
        'test_set__source_language',
        'test_set__target_language',
        'submitted_by',
    ]

    ordering = ('-score',)


class TeamAdmin(admin.ModelAdmin):
    """Model admin for Team objects."""

    fields = ['name', 'email', 'token', 'is_active', 'is_verified']

    list_display = ['__str__', 'email', 'token']
    list_filter = ['is_active', 'is_verified']

    ordering = ('name',)


class TestSetAdmin(admin.ModelAdmin):
    """Model admin for TestSet objects."""

    fields = [
        'name',
        'source_language',
        'target_language',
        'src_sgml_file',
        'ref_sgml_file',
        'is_active',
    ]

    list_display = ['__str__', 'source_language', 'target_language']
    list_filter = ['is_active']

    ordering = ('-name', 'source_language', 'target_language')


admin.site.register(Language, LanguageAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TestSet, TestSetAdmin)
