"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.contrib import admin

from evaluation.models import PairwiseRanking


class PairwiseRankingAdmin(admin.ModelAdmin):
    """Model admin for PairwiseRanking objects."""

    fields = [
        'rank',
        'submission_A',
        'submission_B',
        'submitted_by',
        'line_number',
        'segment_A',
        'segment_B',
        'src_segment',
        'ref_segment',
    ]

    list_display = [
        '__str__',
        'rank',
        '_submission_A_name',
        '_submission_B_name',
        'get_test_set',
        'line_number',
    ]

    list_filter = [
        'rank',
        'submission_A__test_set__name',
        'submitted_by',
    ]

    ordering = ('date_created',)


admin.site.register(PairwiseRanking, PairwiseRankingAdmin)
