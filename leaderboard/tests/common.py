"""
Common imports and constants for leaderboard tests.
"""
import json
import os
import sys
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from shutil import copyfile

from django.test import TestCase
from django.utils import timezone

from leaderboard.admin import _create_team_json
from leaderboard.models import Competition
from leaderboard.models import JSONL_FILE
from leaderboard.models import JSON_FILE
from leaderboard.models import Language
from leaderboard.models import SGML_FILE
from leaderboard.models import Submission
from leaderboard.models import TEXT_FILE
from leaderboard.models import Team
from leaderboard.models import TestSet
from leaderboard.models import XML_FILE
from leaderboard.utils import analyze_xml_file
from leaderboard.utils import process_xml_to_text
from leaderboard.utils import analyze_jsonl_file
from leaderboard.utils import process_jsonl_to_text
from leaderboard.utils import analyze_json_file
from leaderboard.utils import process_json_to_text
from ocelot.settings import BASE_DIR
from ocelot.settings import MEDIA_ROOT

TESTDATA_DIR = os.path.join(BASE_DIR, 'leaderboard/testdata')
