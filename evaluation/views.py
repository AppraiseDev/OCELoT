"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from difflib import SequenceMatcher

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import HttpResponseRedirect
from django.shortcuts import render

from leaderboard.models import Submission
from leaderboard.views import _get_team_data

SEGMENTS_PER_PAGE = 20

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


def submission(request, sub_id=None):
    """Shows submission output."""

    try:
        sub = Submission.objects.get(id=sub_id)
    except Submission.DoesNotExist:
        raise Http404('Submission #{0} does not exist'.format(sub_id))

    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    # Submission must be public unless it's yours
    if sub.is_anonymous() and not sub.is_yours(ocelot_team_token):
        _msg = 'Submission #{0} is not public.'.format(sub_id)
        messages.warning(request, _msg)
        return HttpResponseRedirect('/')

    # A list of submissions which the current submission can be compared with
    _subs = Submission.objects.filter(
        test_set=sub.test_set,
        score__gte=0,  # Ignore invalid submissions
    ).exclude(id=sub_id)

    compare_with = [
        (sub.id, str(sub))
        for sub in _subs
        # Exclude anonymous submissions that are not yours
        if not sub.is_anonymous() or sub.is_yours(ocelot_team_token)
    ]

    context = {
        'segments': zip(sub.get_src_text(), sub.get_hyp_text()),
        'submission_id': sub.id,
        'submission': str(sub),
        'compare_with': compare_with,
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
    }
    return render(request, 'comparison/submission.html', context=context)


def compare(request, sub_a_id=None, sub_b_id=None):
    """Renders vertical or horizontal comparison between two submissions."""

    try:
        sub_a = Submission.objects.get(id=sub_a_id)
        sub_b = Submission.objects.get(id=sub_b_id)
    except Submission.DoesNotExist:
        raise Http404(
            'Submission #{0} or #{1} does not exist'.format(
                sub_a_id, sub_b_id
            )
        )

    # Submissions from different test sets cannot be compared
    if sub_a.test_set != sub_b.test_set:
        _msg = (
            'Submissions #{0} and #{1} cannot be compared,'.format(
                sub_a_id, sub_b_id
            )
            + ' because they do not belong to the same test set.'
        )
        messages.warning(request, _msg)
        return HttpResponseRedirect('/')

    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    # Submissions that are not public cannot be compared
    if (
        sub_a.is_anonymous() and not sub_a.is_yours(ocelot_team_token)
    ) or (sub_b.is_anonymous() and not sub_b.is_yours(ocelot_team_token)):
        _msg = (
            'Submissions #{0} and #{1} cannot be compared.'.format(
                sub_a_id, sub_b_id
            )
            + ' Both submission outputs must be public.'
        )
        messages.warning(request, _msg)
        return HttpResponseRedirect('/')

    text1 = sub_a.get_hyp_text()
    text2 = sub_b.get_hyp_text()
    data = []
    # TODO: Annotate with span diffs only the current page
    for sent1, sent2 in zip(text1, text2):
        data.append(_annotate_texts_with_span_diffs(sent1, sent2))

    # Paginate
    paginator = Paginator(data, SEGMENTS_PER_PAGE)
    page_num = request.GET.get('page', 1)
    page_data = paginator.get_page(page_num)

    context = {
        'page': page_data,
        'page_size': SEGMENTS_PER_PAGE,
        'submission_a': str(sub_a),
        'submission_b': str(sub_b),
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
        # 'comparison_options': [(0, '...'), (1, 'A>B'), (2, 'A<B'), (3, 'A=B')],
    }
    if 'h' in request.GET:
        template = 'comparison/compare_horizontal.html'
    else:
        template = 'comparison/compare_vertical.html'
    return render(request, template, context=context)
