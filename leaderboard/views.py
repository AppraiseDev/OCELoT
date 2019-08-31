"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.shortcuts import render

from leaderboard.models import Submission


def frontpage(request):
    """Renders OCELoT frontpage."""

    # pylint: disable=no-member
    context = {'submissions': Submission.objects.all().order_by('-score')}
    return render(request, 'leaderboard/frontpage.html', context=context)
