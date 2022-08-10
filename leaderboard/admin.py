"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from django.contrib import admin
from django.forms.models import model_to_dict
from django.http import FileResponse

from leaderboard.models import Competition
from leaderboard.models import Language
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet


def _make_submission_filename(submission):
    """Creates a readable filename for a submission."""
    publication_name = submission.submitted_by.publication_name
    if not submission.submitted_by.publication_name:
        publication_name = submission.name

    file_extension = submission.hyp_file.name.split('.')[-1]

    filename = 'submissions/{0}.{1}-{2}.{3}.{4}.{5}'.format(
        submission.test_set.name,
        submission.test_set.source_language.code,
        submission.test_set.target_language.code,
        publication_name,
        submission.id,
        file_extension,
    )
    return filename.replace(' ', '_').lower()


def download_submission_files(modeladmin, request, queryset):
    """Creates zip file with all SGML or text files for queryset."""
    del modeladmin  # unused
    del request  # unused

    tmp_file = NamedTemporaryFile(delete=False)
    with ZipFile(tmp_file, 'w', ZIP_DEFLATED) as zip_file:
        for submission in queryset:
            new_filename = _make_submission_filename(submission)
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

    ordering = ('name',)


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
        '_team_name',
        'test_set',
        '_source_language',
        '_target_language',
        'file_format',
        '_score',
        '_chrf',
    ]

    list_filter = [
        'test_set',
        'test_set__source_language',
        'test_set__target_language',
        'submitted_by__publication_name',
        'file_format',
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


def download_team_file(modeladmin, request, queryset):
    """Creates JSON file with team information for queryset."""
    del modeladmin  # unused
    del request  # unused

    team_list = []
    for team in queryset:
        team_data = model_to_dict(
            team,
            fields=[
                'description',
                'email',
                'institution_name',
                'name',
                'publication_name',
                'publication_url',
            ],
        )

        primary_submissions = team.submission_set.filter(
            is_primary=True, score__gte=0
        )
        team_data['number_of_primary_submissions'] = len(
            primary_submissions
        )

        submission_list = []
        for submission in primary_submissions:
            submission_data = model_to_dict(
                submission,
                fields=[
                    'is_constrained',
                    'is_primary',
                    'is_removed',
                    'score',
                    'score_chrf',
                ],
            )
            submission_data[
                'competition'
            ] = submission.test_set.competition.name
            submission_data['file_name'] = _make_submission_filename(
                submission
            )
            submission_data['submission_id'] = submission.id
            submission_data['test_set'] = submission.test_set.name
            language_pair = "{0}-{1}".format(
                submission.test_set.source_language.code,
                submission.test_set.target_language.code,
            )
            submission_data['language_pair'] = language_pair
            submission_list.append(submission_data)
        team_data['primary_submissions'] = submission_list

        team_list.append(team_data)
    team_json = json.dumps(list(team_list), indent=2, sort_keys=True)

    tmp_file = NamedTemporaryFile(delete=False)
    with ZipFile(tmp_file, 'w', ZIP_DEFLATED) as zip_file:
        zip_file.writestr('teams.json', team_json)

    tmp_file.seek(0)
    response = FileResponse(
        open(tmp_file.name, 'rb'),
        as_attachment=True,
        content_type='application/x-zip-compressed',
        filename='teams.zip',
    )
    return response


download_team_file.short_description = (  # type: ignore
    "Download JSON file with primary submissions for selected teams"
)


class TeamAdmin(admin.ModelAdmin):
    """Model admin for Team objects."""

    actions = [download_team_file]

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
        'is_verified',
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
        'collection',
        'competition',
        'is_active',
        'is_public',
        'compute_scores',
    ]

    list_display = [
        '__str__',
        'source_language',
        'target_language',
        'competition',
    ]

    list_filter = [
        'is_active',
        'is_public',
        'compute_scores',
        'file_format',
        'competition',
    ]

    ordering = ('-name', 'source_language', 'target_language')


class CompetitionAdmin(admin.ModelAdmin):
    """Model admin for Competition objects."""

    fields = [
        'name',
        'description',
        'start_time',
        'deadline',
        'is_active',
        'is_public',
    ]

    list_display = [
        '__str__',
        'start_time',
        'deadline',
    ]

    list_filter = [
        'is_active',
        'is_public',
    ]

    ordering = ('-name',)


admin.site.register(Language, LanguageAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TestSet, TestSetAdmin)
admin.site.register(Competition, CompetitionAdmin)
