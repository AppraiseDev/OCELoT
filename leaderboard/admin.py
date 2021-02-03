"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from django.contrib import admin
from django.http import FileResponse

from leaderboard.models import Competition
from leaderboard.models import Language
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet


def download_submission_files(modeladmin, request, queryset):
    """Creates zip file with all SGML or text files for queryset."""
    del modeladmin  # unused
    del request  # unused

    tmp_file = NamedTemporaryFile(delete=False)
    with ZipFile(tmp_file, 'w', ZIP_DEFLATED) as zip_file:
        for submission in queryset:
            publication_name = submission.submitted_by.publication_name
            if not submission.submitted_by.publication_name:
                publication_name = submission.name

            file_extension = submission.hyp_file.name.split('.')[-1]

            new_filename = 'submissions/{0}.{1}-{2}.{3}.{4}.{5}'.format(
                submission.test_set.name,
                submission.test_set.source_language.code,
                submission.test_set.target_language.code,
                publication_name,
                submission.id,
                file_extension,
            )
            new_filename.replace(' ', '_').lower()

            zip_file.writestr(
                Path(new_filename).name,
                submission.hyp_file.open('rb').read(),
            )

    tmp_file.seek(0)
    response = FileResponse(
        open(tmp_file.name, 'rb'),
        as_attachment=True,
        content_type='application/x-zip-compressed',
        filename='submissions.zip',
    )
    return response


download_submission_files.short_description = (  # type: ignore
    "Download SGML or text files for selected submissions"
)


class LanguageAdmin(admin.ModelAdmin):
    """Model admin for Language objects."""

    fields = ['code', 'name']


class SubmissionAdmin(admin.ModelAdmin):
    """Model admin for Submission objects."""

    actions = [download_submission_files]

    fields = [
        'name',
        'test_set',
        'file_format',
        'hyp_file',
        'submitted_by',
        'is_constrained',
        'is_flagged',
        'is_primary',
        'is_public',
        'is_removed',
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
        'is_flagged',
        'is_primary',
        'is_public',
        'is_removed',
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
        'publication_name',
        'is_active',
        'is_flagged',
        'is_removed',
        'is_verified',
    ]

    list_display = [
        '__str__',
        'email',
        'token',
        '_submissions',
        '_primary_submissions',
    ]

    list_filter = [
        'is_active',
        'is_flagged',
        'is_removed',
        'is_verified',
    ]

    search_fields = ['name', 'email', 'token']

    ordering = ('name',)


class TestSetAdmin(admin.ModelAdmin):
    """Model admin for TestSet objects."""

    fields = [
        'name',
        'source_language',
        'target_language',
        'file_format',
        'src_file',
        'ref_file',
        'is_active',
    ]

    list_display = [
        '__str__',
        'source_language',
        'target_language',
    ]

    list_filter = [
        'is_active',
        'file_format',
    ]

    ordering = ('-name', 'source_language', 'target_language')


class CompetitionAdmin(admin.ModelAdmin):
    """Model admin for Competition objects."""

    fields = [
        'name',
        'description',
        'deadline',
        'test_sets',
    ]

    list_display = [
        '__str__',
    ]

    ordering = ('-name',)


admin.site.register(Language, LanguageAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TestSet, TestSetAdmin)
admin.site.register(Competition, CompetitionAdmin)
