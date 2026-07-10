"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

The leaderboard models package. This module re-exports the full public API
that used to live in the monolithic ``leaderboard/models.py`` so that existing
migrations (which reference symbols by import path, e.g.
``leaderboard.models.validate_xml_submission`` and
``leaderboard.models._get_submission_upload_path``) and external imports keep
working unchanged.
"""
from django.core.exceptions import ValidationError  # re-exported for tests

from .constants import FILE_FORMAT_CHOICES
from .constants import JSON_FILE
from .constants import JSONL_FILE
from .constants import MAX_CODE_LENGTH
from .constants import MAX_DESCRIPTION_LENGTH
from .constants import MAX_FORMAT_LENGTH
from .constants import MAX_NAME_LENGTH
from .constants import MAX_TOKEN_LENGTH
from .constants import SGML_FILE
from .constants import TEXT_FILE
from .constants import XML_FILE
from .formats.json import JSON_SCHEMA
from .formats.json import validate_json_ref_testset
from .formats.json import validate_json_schema
from .formats.json import validate_json_src_testset
from .formats.json import validate_json_submission
from .formats.jsonl import JSONL_WMT25_SCHEMA
from .formats.jsonl import JSONL_WMT25_ST_MT_SCHEMA
from .formats.jsonl import JSONL_WMT25_ST_QA_SCHEMA
from .formats.jsonl import JSONL_WMT26_LR_MT_SCHEMA
from .formats.jsonl import JSONL_WMT26_LR_QA_SCHEMA
from .formats.jsonl import JSONL_WMT26_LR_MR_SCHEMA
from .formats.jsonl import JSONL_WMT26_LR_SCGC_SCHEMA
from .formats.jsonl import validate_jsonl_ref_testset
from .formats.jsonl import validate_jsonl_schema
from .formats.jsonl import validate_jsonl_src_testset
from .formats.jsonl import validate_jsonl_submission
from .formats.sgml import SGML_XSD_SCHEMA
from .formats.sgml import validate_sgml_schema
from .formats.xml import XML_RNG_SCHEMA
from .formats.xml import validate_xml_ref_testset
from .formats.xml import validate_xml_schema
from .formats.xml import validate_xml_src_testset
from .formats.xml import validate_xml_submission
from .validators import validate_institution_name
from .validators import validate_publication_name
from .validators import validate_team_name
from .validators import validate_token

# Models are imported in dependency order so Django can discover them all and
# so foreign-key target classes load before their referrers.
from .language import Language
from .competition import Competition
from .testset import TestSet
from .team import Team
from .submission import Submission
from .submission import _get_submission_upload_path

__all__ = [
    'ValidationError',
    # constants
    'MAX_CODE_LENGTH',
    'MAX_NAME_LENGTH',
    'MAX_DESCRIPTION_LENGTH',
    'MAX_TOKEN_LENGTH',
    'MAX_FORMAT_LENGTH',
    'SGML_FILE',
    'TEXT_FILE',
    'XML_FILE',
    'JSONL_FILE',
    'JSON_FILE',
    'FILE_FORMAT_CHOICES',
    # schemas
    'SGML_XSD_SCHEMA',
    'XML_RNG_SCHEMA',
    'JSONL_WMT25_SCHEMA',
    'JSONL_WMT25_ST_QA_SCHEMA',
    'JSONL_WMT25_ST_MT_SCHEMA',
    'JSONL_WMT26_LR_MT_SCHEMA',
    'JSONL_WMT26_LR_QA_SCHEMA',
    'JSONL_WMT26_LR_MR_SCHEMA',
    'JSONL_WMT26_LR_SCGC_SCHEMA',
    'JSON_SCHEMA',
    # format validators
    'validate_sgml_schema',
    'validate_xml_schema',
    'validate_xml_src_testset',
    'validate_xml_ref_testset',
    'validate_xml_submission',
    'validate_jsonl_schema',
    'validate_jsonl_src_testset',
    'validate_jsonl_ref_testset',
    'validate_jsonl_submission',
    'validate_json_schema',
    'validate_json_src_testset',
    'validate_json_ref_testset',
    'validate_json_submission',
    # field validators
    'validate_team_name',
    'validate_institution_name',
    'validate_publication_name',
    'validate_token',
    # models
    'Competition',
    'Language',
    'TestSet',
    'Team',
    'Submission',
    '_get_submission_upload_path',
]
