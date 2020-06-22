"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
from collections import defaultdict
from pathlib import Path
from django.shortcuts import render, HttpResponseRedirect

from leaderboard.forms import SubmissionForm
from leaderboard.models import Submission, TestSet


MAX_SUBMISSION_DISPLAY_COUNT = 10

def frontpage(request):
    """Renders OCELoT frontpage."""

    data = defaultdict(list)
    submissions = Submission.objects.filter(test_set__is_active=True)
    for submission in submissions.order_by(
        'test_set', '-score'
    ):
        data[str(submission.test_set)].append(submission)

    context = {
        'data': data.items(),
        'MAX_SUBMISSION_DISPLAY_COUNT': MAX_SUBMISSION_DISPLAY_COUNT,
    }
    return render(request, 'leaderboard/frontpage.html', context=context)


def submit(request):
    """Renders OCELoT submission page."""

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)

        if form.is_valid:
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

    # pylint: disable=no-member
    context = {'form': form}
    return render(request, 'leaderboard/submission.html', context=context)
