"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from django.contrib import admin
from django.http import FileResponse

from leaderboard.models import Language
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet


def download_sgml_files(modeladmin, request, queryset):
    """Creates zip file with all SGML files for queryset."""
    del modeladmin  # unused
    del request  # unused

    tmp_file = NamedTemporaryFile(delete=False)
    with ZipFile(tmp_file, 'w', ZIP_DEFLATED) as zip_file:
        for submission in queryset:
            zip_file.writestr(
                Path(submission.sgml_file.name).name,
                submission.sgml_file.open('rb').read(),
            )

    tmp_file.seek(0)
    response = FileResponse(
        open(tmp_file.name, 'rb'),
        as_attachment=True,
        content_type='application/x-zip-compressed',
        filename='submissions.zip',
    )
    return response


download_sgml_files.short_description = (  # type: ignore
    "Download SGML files for selected submissions"
)


class LanguageAdmin(admin.ModelAdmin):
    """Model admin for Language objects."""

    fields = ['code', 'name']


class SubmissionAdmin(admin.ModelAdmin):
    """Model admin for Submission objects."""

    actions = [download_sgml_files]

    fields = [
        'name',
        'test_set',
        'sgml_file',
        'submitted_by',
        'is_primary',
        'is_public',
        'score',
        'score_chrf',
    ]

    list_display = [
        '__str__',
        'test_set',
        '_source_language',
        '_target_language',
        '_score',
        '_chrf',
    ]

    list_filter = [
        'test_set',
        'test_set__source_language',
        'test_set__target_language',
        'submitted_by',
    ]

    ordering = (
        'test_set__name',
        'test_set__source_language__code',
        'test_set__target_language__code',
        '-score',
    )


class TeamAdmin(admin.ModelAdmin):
    """Model admin for Team objects."""

    fields = [
        'name',
        'email',
        'token',
        'is_active',
        'is_flagged',
        'is_removed',
        'is_verified',
    ]

    list_display = ['__str__', 'email', 'token']
    list_filter = ['is_active', 'is_flagged', 'is_removed', 'is_verified']

    search_fields = ['name', 'email', 'token']

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
