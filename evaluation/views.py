"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from difflib import SequenceMatcher

from django.http import Http404
from django.shortcuts import render

from leaderboard.models import Submission
from leaderboard.views import _get_team_data


def _annotate_texts_with_span_diffs(text1, text2, char_based=False):
    """
    Returns pair of texts annotated with HTML tags highlighting word-level differences.
    Both texts must be non empty.

    For example,
        'a b c d e' and 'a B c e f'
    will become:
        'a <span class="diff diff-sub">b</span> c <span class="diff diff-del">d</span> e',
        'a <span class="diff diff-sub">B</span> c e <span class="diff diff-ins">f</span>'
    """
    if not text1 or not text2 or (text1 == text2):
        return (text1, text2)

    toks1 = list(text1) if char_based else text1.split()
    toks2 = list(text2) if char_based else text2.split()
    matcher = SequenceMatcher(None, toks1, toks2)

    sep = '' if char_based else ' '

    text1 = ''
    text2 = ''
    # pylint: disable=invalid-name
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            text1 += sep + sep.join(toks1[i1:i2])
            text2 += sep + sep.join(toks2[j1:j2])
        elif tag == 'replace':
            text1 += (
                sep
                + '<span class="diff diff-sub">'
                + sep.join(toks1[i1:i2])
                + '</span>'
            )
            text2 += (
                sep
                + '<span class="diff diff-sub">'
                + sep.join(toks2[j1:j2])
                + '</span>'
            )
        elif tag == 'insert':
            text2 += (
                sep
                + '<span class="diff diff-ins">'
                + sep.join(toks2[j1:j2])
                + '</span>'
            )
        elif tag == 'delete':
            text1 += (
                sep
                + '<span class="diff diff-del">'
                + sep.join(toks1[i1:i2])
                + '</span>'
            )
    return (text1.strip(), text2.strip())


def compare(request, sub_a_id=None, sub_b_id=None):
    """Renders vertical or horizontal comparison between two submissions."""

    try:
        sub_a = Submission.objects.get(id=sub_a_id)
        sub_b = Submission.objects.get(id=sub_b_id)
    except Submission.DoesNotExist:
        raise Http404(
            'Submission with ID {0} or {1} does not exists'.format(
                sub_a_id, sub_b_id
            )
        )

    # TODO: raise an error if two submissions are from different test sets
    # TODO: disallow comparison of an anonymous test sets
    # TODO: paginate

    text1 = sub_a.get_hyp_text()
    text2 = sub_b.get_hyp_text()
    data = []
    for sent1, sent2 in zip(text1, text2):
        data.append(_annotate_texts_with_span_diffs(sent1, sent2))

    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    context = {
        'data': data,
        'submission_a': str(sub_a),
        'submission_b': str(sub_b),
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
    }
    if 'h' in request.GET:
        template = 'comparison/compare_horizontal.html'
    else:
        template = 'comparison/compare_vertical.html'
    return render(request, template, context=context)
