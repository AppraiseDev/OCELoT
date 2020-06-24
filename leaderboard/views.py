"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from collections import defaultdict
from pathlib import Path

from django.shortcuts import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from leaderboard.forms import SigninForm
from leaderboard.forms import SubmissionForm
from leaderboard.forms import TeamForm
from leaderboard.models import Submission
from leaderboard.models import Team
from leaderboard.models import TestSet


MAX_SUBMISSION_DISPLAY_COUNT = 10
MAX_SUBMISSION_PERTEAM_COUNT = 7


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


def frontpage(request):
    """Renders OCELoT frontpage."""

    data = defaultdict(list)
    submissions = Submission.objects.filter(test_set__is_active=True)
    for submission in submissions.order_by('test_set', '-score'):
        data[str(submission.test_set)].append(submission)

    ocelot_team_name, ocelot_team_email, ocelot_team_token = _get_team_data(
        request
    )

    context = {
        'data': data.items(),
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
            return HttpResponseRedirect(reverse('frontpage-view'))

    else:
        form = SigninForm()

    context = {'form': form}
    return render(request, 'leaderboard/sign-in.html', context=context)


def signout(request):
    """Clears current OCELoT session."""
    del request.session['ocelot_team_token']
    return HttpResponseRedirect(reverse('frontpage-view'))


def signup(request):
    """Renders OCELoT team signup page."""

    print(request.session.get('ocelot_team_token'))

    if request.session.get('ocelot_team_token'):
        return HttpResponseRedirect(reverse('frontpage-view'))

    if request.method == 'POST':
        form = TeamForm(request.POST)

        if form.is_valid():
            new_team = form.save()
            request.session['ocelot_team_token'] = new_team.token
            print(new_team.token)
            return HttpResponseRedirect(reverse('welcome-view'))

    else:
        form = TeamForm()

    context = {'form': form}
    return render(request, 'leaderboard/signup.html', context=context)


def submit(request):
    """Renders OCELoT submission page."""

    ocelot_team_name, ocelot_team_email, ocelot_team_token = _get_team_data(
        request
    )

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)

        if form.is_valid():
            current_team = Team.objects.get(token=ocelot_team_token)
            print(current_team)

            submissions_for_team = Submission.objects.filter(
                submitted_by=current_team
            ).count()
            print(submissions_for_team)

            if submissions_for_team + 1 > MAX_SUBMISSION_PERTEAM_COUNT:
                # Bad submission
                return HttpResponseRedirect('/')

            new_submission = form.save(commit=False)
            new_submission.submitted_by = current_team
            new_submission.save()

            if False:
                new_submission.name = '{0}.{1}.{2}.sgm'.format(
                    form.test_set.name,
                    ocelot_team_token,
                    submissions_for_team + 1,
                )
                new_submission.save()

            if False:
                test_set = TestSet.objects.get(
                    pk=int(request.POST['test_set'])
                )
                sgml_file = request.FILES['sgml_file']

                sgml_name = sgml_file.name
                sgml_path = Path('submissions') / sgml_name
                with open(sgml_path, 'wb+') as sgml_out:
                    for chunk in sgml_file.chunks():
                        sgml_out.write(chunk)

                new_submission = Submission()
                new_submission.sgml_file = sgml_file
                new_submission.test_set = test_set
                new_submission.name = 'TBA'
                new_submission.save()

            return HttpResponseRedirect('/')

    else:
        form = SubmissionForm()

    context = {
        'form': form,
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
    }
    return render(request, 'leaderboard/submission.html', context=context)


def welcome(request):
    """Renders OCELoT welcome (registration confirmation) page."""

    ocelot_team_name, ocelot_team_email, ocelot_team_token = _get_team_data(
        request
    )

    context = {
        'ocelot_team_name': ocelot_team_name,
        'ocelot_team_email': ocelot_team_email,
        'ocelot_team_token': ocelot_team_token,
    }
    return render(request, 'leaderboard/welcome.html', context=context)
