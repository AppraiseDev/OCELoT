"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from collections import OrderedDict
from datetime import datetime

from django.contrib import messages
from django.shortcuts import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from leaderboard.forms import PublicationNameForm
from leaderboard.forms import SigninForm
from leaderboard.forms import SubmissionForm
from leaderboard.forms import TeamForm
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet


MAX_SUBMISSION_DISPLAY_COUNT = 10
MAX_SUBMISSION_LIMIT = 7


def _get_team_data(request):
    """Returns team name for session token."""
    ocelot_team_name = None
    ocelot_team_email = None
    ocelot_team_token = request.session.get('ocelot_team_token')
    if ocelot_team_token:
        the_team = Team.objects.get(  # pylint: disable=no-member
            token=ocelot_team_token
        )
        ocelot_team_name = the_team.name
        ocelot_team_email = the_team.email
    return (ocelot_team_name, ocelot_team_email, ocelot_team_token)


def frontpage(request):
    """Renders OCELoT frontpage."""

    test_sets = TestSet.objects.filter(  # pylint: disable=no-member
        is_active=True,
    ).order_by('name', 'source_language__code', 'target_language__code',)

    data = OrderedDict()
    for test_set in test_sets:
        submissions = (
            Submission.objects.filter(  # pylint: disable=no-member
                test_set=test_set,
                score__gte=0,  # Ignore invalid submissions
            )
            .order_by('-score',)
            .values_list(
                'id',
                'score',
                'score_chrf',
                'date_created',
                'submitted_by__token',
            )[:MAX_SUBMISSION_DISPLAY_COUNT]
        )
        for submission in submissions:
            key = str(test_set)
            if not key in data.keys():
                data[key] = []
            data[key].append(submission)

    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    context = {
        'data': data.items(),
        'deadline': '7/18/2020 12:00:00 UTC',
        'MAX_SUBMISSION_DISPLAY_COUNT': MAX_SUBMISSION_DISPLAY_COUNT,
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
    }
    return render(request, 'leaderboard/frontpage.html', context=context)


def signin(request):
    """Renders OCELoT team sign-in page."""

    # Already signed in?
    if request.session.get('ocelot_team_token'):
        _msg = 'You are already signed in.'
        messages.info(request, _msg)
        return HttpResponseRedirect(reverse('frontpage-view'))

    if request.method == 'POST':
        form = SigninForm(request.POST)

        if form.is_valid():
            the_team = Team.objects.filter(  # pylint: disable=no-member
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                token=form.cleaned_data['token'],
            )
            if the_team.exists():
                request.session['ocelot_team_token'] = form.cleaned_data[
                    'token'
                ]

            _msg = 'You have successfully signed in.'
            messages.success(request, _msg)
            return HttpResponseRedirect(reverse('frontpage-view'))

    else:
        form = SigninForm()

    context = {'form': form}
    return render(request, 'leaderboard/sign-in.html', context=context)


def signout(request):
    """Clears current OCELoT session."""
    del request.session['ocelot_team_token']
    messages.success(request, 'You have successfully signed out.')
    return HttpResponseRedirect(reverse('frontpage-view'))


def signup(request):
    """Renders OCELoT team signup page."""

    if request.session.get('ocelot_team_token'):
        messages.info(request, 'You are already signed up.')
        return HttpResponseRedirect(reverse('frontpage-view'))

    if request.method == 'POST':
        form = TeamForm(request.POST)

        if form.is_valid():
            new_team = form.save()
            request.session['ocelot_team_token'] = new_team.token
            messages.success(request, 'You have successfully signed up.')
            return HttpResponseRedirect(reverse('welcome-view'))

    else:
        form = TeamForm()

    context = {'form': form}
    return render(request, 'leaderboard/signup.html', context=context)


def submit(request):
    """Renders OCELoT submission page."""

    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    if not ocelot_team_token:
        _msg = 'You need to be signed in to access this page.'
        messages.warning(request, _msg)
        return HttpResponseRedirect('/')

    deadline = datetime(2020, 7, 18, 12, 0, 0, tzinfo=timezone.utc)
    current = timezone.now()
    if current >= deadline:
        _msg = 'WMT20 submission has closed.'
        messages.warning(request, _msg)
        return HttpResponseRedirect('/')

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)

        if form.is_valid():
            current_team = Team.objects.get(  # pylint: disable=no-member
                token=ocelot_team_token
            )
            print(current_team)

            submissions_for_team_and_test_set = Submission.objects.filter(  # pylint: disable=no-member
                submitted_by=current_team,
                test_set=form.cleaned_data['test_set'],
                score__gte=0,  # Ignore invalid submissions for limit check
            ).count()
            print(submissions_for_team_and_test_set)

            if submissions_for_team_and_test_set >= MAX_SUBMISSION_LIMIT:
                _msg = 'You have reached the submission limit for {0}.'.format(
                    form.cleaned_data['test_set']
                )
                messages.warning(request, _msg)
                return HttpResponseRedirect('/')

            new_submission = form.save(commit=False)
            new_submission.name = form.cleaned_data['hyp_file'].name
            new_submission.file_format = form.cleaned_data['file_format']
            new_submission.submitted_by = current_team
            new_submission.save()

            _msg = 'You have successfully submitted {0}'.format(
                new_submission.hyp_file.name
            )
            messages.success(request, _msg)
            return HttpResponseRedirect(reverse('teampage-view'))

    else:
        form = SubmissionForm()

    context = {
        'form': form,
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
    }
    return render(request, 'leaderboard/submission.html', context=context)


def teampage(request):
    """Renders OCELoT team page."""

    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    if not ocelot_team_token:
        _msg = 'You need to be signed in to access this page.'
        messages.warning(request, _msg)
        return HttpResponseRedirect('/')

    current_team = Team.objects.get(  # pylint: disable=no-member
        name=ocelot_team_name,
        email=ocelot_team_email,
        token=ocelot_team_token,
    )

    if request.method == 'POST':
        publication_name_form = PublicationNameForm(request.POST)

        if publication_name_form.is_valid():
            publication_name = publication_name_form.cleaned_data[
                'publication_name'
            ]
            if publication_name != current_team.publication_name:
                current_team.publication_name = publication_name
                current_team.save()

        primary_ids_and_constrainedness = zip(
            request.POST.getlist('primary'),
            request.POST.getlist('constrained'),
        )
        for primary_id, constrained in primary_ids_and_constrainedness:
            submission = Submission.objects.get(  # pylint: disable=no-member
                id=int(primary_id)
            )
            if submission.submitted_by.token == ocelot_team_token:
                submission.is_constrained = bool(int(constrained))
                submission.set_primary()  # This implicitly calls save()

    else:
        context = {'publication_name': current_team.publication_name}
        publication_name_form = PublicationNameForm(context)

    data = OrderedDict()
    primary = OrderedDict()
    submissions = Submission.objects.filter(  # pylint: disable=no-member
        score__gte=0,  # Ignore invalid submissions
        submitted_by__token=ocelot_team_token,
    )
    ordering = (
        'test_set__name',
        'test_set__source_language__code',
        'test_set__target_language__code',
        '-score',
    )
    for submission in submissions.order_by(*ordering):
        key = submission.test_set
        if not key in data.keys():
            data[key] = []
        data[key].append(submission)

        if not key in primary.keys():
            primary[key] = None

        if submission.is_primary:
            primary[key] = submission

    data_triples = []
    for key in data.keys():
        data_triples.append((key, primary[key], data[key]))

    context = {
        'data': data_triples,
        'MAX_SUBMISSION_LIMIT': MAX_SUBMISSION_LIMIT,
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
        'publication_name_form': publication_name_form,
    }
    return render(request, 'leaderboard/teampage.html', context=context)


def updates(request):
    """Renders OCELoT updates page."""

    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    context = {
        'MAX_SUBMISSION_LIMIT': MAX_SUBMISSION_LIMIT,
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
    }
    return render(request, 'leaderboard/updates.html', context=context)


def welcome(request):
    """Renders OCELoT welcome (registration confirmation) page."""

    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    if not ocelot_team_token:
        _msg = 'You need to be signed in to access this page.'
        messages.warning(request, _msg)
        return HttpResponseRedirect('/')

    context = {
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
    }
    return render(request, 'leaderboard/welcome.html', context=context)
