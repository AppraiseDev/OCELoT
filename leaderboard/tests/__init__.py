"""
Tests package for the leaderboard app.
"""

# Import all test classes to maintain backwards compatibility
from .test_utils import UtilsTests
from .test_submission import SubmissionTests
from .test_xml_submission import XMLSubmissionTests
from .test_jsonl_submission import JSONLSubmissionTests
from .test_testset import TestSetTests
from .test_competition import CompetitionTests
from .test_leaderboard import LeaderboardTests
from .test_admin import AdminActionsTests

__all__ = [
    'UtilsTests',
    'SubmissionTests', 
    'XMLSubmissionTests',
    'JSONLSubmissionTests',
    'TestSetTests',
    'CompetitionTests',
    'LeaderboardTests',
    'AdminActionsTests',
]
