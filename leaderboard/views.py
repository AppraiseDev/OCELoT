"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from collections import OrderedDict

from django.contrib import messages
from django.db.models import Count
from django.http import Http404
from django.shortcuts import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from leaderboard.forms import PublicationNameForm
from leaderboard.forms import SigninForm
from leaderboard.forms import SubmissionForm
from leaderboard.forms import TeamForm
from leaderboard.models import Competition
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
        the_team = Team.objects.get(token=ocelot_team_token)
        ocelot_team_name = the_team.name
        ocelot_team_email = the_team.email
    return (ocelot_team_name, ocelot_team_email, ocelot_team_token)


def _format_datetime_for_js(stamp):
    """Formats time stamp for Javascript."""
    if not stamp:
        return None
    return stamp.strftime("%Y-%m-%d %H:%M:%S")  # JS will assume it's UTC


def leaderboard(request, competition_id=None):
    """Renders leaderboard for a competition."""

    # Get the competition by its ID or render 404
    try:
        competition = Competition.objects.get(id=competition_id)
    except Competition.DoesNotExist:
        raise Http404(
            'Campaign with ID {0} does not exists'.format(competition_id)
        )

    # Do not show the leaderboard if the competition is currenlty inactive
    if not competition.is_active:
        _msg = 'Competition {0} is currently inactive.'.format(
            competition.name
        )
        messages.warning(request, _msg)
        return HttpResponseRedirect('/')

    # Competition context
    comp_info = {
        'name': competition.name,
        'description': competition.description,
        'start_time': _format_datetime_for_js(competition.start_time),
        'deadline': _format_datetime_for_js(competition.deadline),
    }

    # Collect all test sets for the competition
    data = OrderedDict()
    test_sets = TestSet.objects.filter(competition=competition).order_by(
        'name'
    )

    for test_set in test_sets:
        submissions = Submission.objects.filter(
            test_set=test_set,
            score__gte=0,  # Ignore invalid submissions
        ).order_by('-score',)[:MAX_SUBMISSION_DISPLAY_COUNT]

        for submission in submissions:
            key = str(test_set)
            if not key in data.keys():
                data[key] = []

            data[key].append(
                {
                    "id": submission.id,
                    "name": str(submission),
                    "score_bleu": submission.score,
                    "score_chrf": submission.score_chrf,
                    "date_created": submission.date_created,
                    # TODO: Double check if this foreign key reference does not
                    # generate an extra query. Optimize otherwise.
                    "team_token": submission.submitted_by.token,
                    "is_anonymous": submission.is_anonymous(),
                }
            )
    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    context = {
        'competition': comp_info,
        'data': data.items(),
        'MAX_SUBMISSION_DISPLAY_COUNT': MAX_SUBMISSION_DISPLAY_COUNT,
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
    }
    return render(request, 'leaderboard/competition.html', context=context)


def frontpage(request):
    """Renders OCELoT frontpage with a list of competitions."""

    competitions = (
        Competition.objects.filter(
            is_active=True,
        )
        .order_by(
            '-deadline',
        )
        .annotate(
            # Number of test sets assigned to a competition
            num_test_sets=Count('test_sets', distinct=True),
            # The total number of submissions from all assigned test sets
            num_submissions=Count('test_sets__submission'),
        )
        .values(
            'id',
            'name',
            'num_test_sets',
            'num_submissions',
            'description',
            'start_time',
            'deadline',
        )
    )

    (
        ocelot_team_name,
        ocelot_team_email,
        ocelot_team_token,
    ) = _get_team_data(request)

    context = {
        'competitions': competitions,
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
            the_team = Team.objects.filter(
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

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)

        if form.is_valid():
            current_team = Team.objects.get(token=ocelot_team_token)

            # Check if the competition deadline has not passed yet.
            # This is a second level of validation, because test sets from
            # unstarted or closed competitions are not added to the select box
            # of the submission form. It covers a case when the user first
            # renders the form, then the deadline passes (e.g. a long idle
            # time), and after that the submission is made.
            current_time = timezone.now()
            test_set = form.cleaned_data['test_set']
            comp = test_set.competition

            if comp.deadline and current_time >= comp.deadline:
                _msg = '{0} submission has closed.'.format(comp.name)
                messages.warning(request, _msg)
                return HttpResponseRedirect('/')
            if comp.start_time and current_time <= comp.start_time:
                _msg = '{0} submission has not started.'.format(comp.name)
                messages.warning(request, _msg)
                return HttpResponseRedirect('/')

            # Check if the number of submissions for this team and test set
            # does not exceed the limit
            number_of_submissions = Submission.objects.filter(
                submitted_by=current_team,
                test_set=test_set,
                score__gte=0,  # Ignore invalid submissions for limit check
            ).count()

            if number_of_submissions >= MAX_SUBMISSION_LIMIT:
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
            # TODO: add logging message with form.errors
            pass

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

    current_team = Team.objects.get(
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
            submission = Submission.objects.get(id=int(primary_id))
            if submission.submitted_by.token == ocelot_team_token:
                submission.is_constrained = bool(int(constrained))
                submission.set_primary()  # This implicitly calls save()

    else:
        context = {'publication_name': current_team.publication_name}
        publication_name_form = PublicationNameForm(context)

    data = OrderedDict()
    primary = OrderedDict()
    submissions = Submission.objects.filter(
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

    data_triples = []  # (test set, primary submission, all submissions)
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
