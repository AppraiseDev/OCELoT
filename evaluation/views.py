"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from difflib import SequenceMatcher

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import HttpResponseRedirect
from django.shortcuts import render

from evaluation.models import PairwiseRanking

from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.views import _get_team_data

SEGMENTS_PER_PAGE = 100


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

    # Paginate
    data = list(zip(sub.get_src_text(), sub.get_hyp_text()))
    paginator = Paginator(data, SEGMENTS_PER_PAGE)
    page_num = request.GET.get('page', 1)
    page_data = paginator.get_page(page_num)

    context = {
        'page': page_data,
        'page_size': SEGMENTS_PER_PAGE,
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

    if request.method == "POST" and sub_a_id is None and sub_b_id is None:
        return submit_rank(request)

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
    # TODO: Annotate with span diffs only the current page, for example try to
    # change page_data.object_list
    # TODO: Check if there are some PairwiseRanking objects for each line and
    # if so, select them in the select box. Should this be specific to the user
    # or global?
    for sent1, sent2 in zip(text1, text2):
        sent1_spans, sent2_spans = _annotate_texts_with_span_diffs(
            sent1, sent2
        )
        data.append(
            (sent1.strip(), sent2.strip(), sent1_spans, sent2_spans)
        )

    # Paginate
    paginator = Paginator(data, SEGMENTS_PER_PAGE)
    page_num = request.GET.get('page', 1)
    page_data = paginator.get_page(page_num)

    context = {
        'page': page_data,
        'page_size': SEGMENTS_PER_PAGE,
        'submission_a': sub_a,
        'submission_b': sub_b,
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
        'comparison_options': PairwiseRanking.RANK_CHOICES,
    }
    if 'h' in request.GET:
        template = 'comparison/compare_horizontal.html'
    else:
        template = 'comparison/compare_vertical.html'
    return render(request, template, context=context)


def submit_rank(request):
    """Handles Ajax request to create a PairwiseRanking object."""
    # Accept POST requests only
    if request.method != "POST":
        return

    msg = []

    _, _, ocelot_team_token = _get_team_data(request)
    sub_a_id = int(request.POST.get('submission_a_id'))
    sub_b_id = int(request.POST.get('submission_b_id'))

    try:
        rank_obj = PairwiseRanking.objects.create(
            rank=request.POST.get('rank'),
            submitted_by=Team.objects.get(token=ocelot_team_token),
            submission_A=Submission.objects.get(id=sub_a_id),
            submission_B=Submission.objects.get(id=sub_b_id),
            line_number=int(request.POST.get('line_number')),
            segment_A=request.POST.get('segment_a'),
            segment_B=request.POST.get('segment_b'),
        )
        rank_obj.save()

    except Exception as e:
        # TODO: Better message
        msg.append("Something went wrong...")
        msg.append(e.message)

    context = {'success': True, 'messages': msg}
    return JsonResponse(context)
