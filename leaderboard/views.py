"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from django.shortcuts import render


def frontpage(request):
    """Renders OCELoT frontpage."""
    return render(request, 'frontpage.html')
