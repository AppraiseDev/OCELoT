"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

Per-format schemas and validators. Each module under this package owns
everything about one file format: its schema constant(s) and the validators
that use it.
"""
from .sgml import SGML_XSD_SCHEMA
from .sgml import validate_sgml_schema
from .xml import XML_RNG_SCHEMA
from .xml import validate_xml_schema
from .xml import validate_xml_src_testset
from .xml import validate_xml_ref_testset
from .xml import validate_xml_submission
from .jsonl import JSONL_WMT25_SCHEMA
from .jsonl import JSONL_WMT25_ST_QA_SCHEMA
from .jsonl import JSONL_WMT25_ST_MT_SCHEMA
from .jsonl import JSONL_WMT26_LR_MT_SCHEMA
from .jsonl import JSONL_WMT26_LR_QA_SCHEMA
from .jsonl import JSONL_WMT26_LR_MR_SCHEMA
from .jsonl import JSONL_WMT26_LR_SCGC_SCHEMA
from .jsonl import validate_jsonl_schema
from .jsonl import validate_jsonl_src_testset
from .jsonl import validate_jsonl_ref_testset
from .jsonl import validate_jsonl_submission
from .json import JSON_SCHEMA
from .json import validate_json_schema
from .json import validate_json_src_testset
from .json import validate_json_ref_testset
from .json import validate_json_submission

__all__ = [
    'SGML_XSD_SCHEMA',
    'validate_sgml_schema',
    'XML_RNG_SCHEMA',
    'validate_xml_schema',
    'validate_xml_src_testset',
    'validate_xml_ref_testset',
    'validate_xml_submission',
    'JSONL_WMT25_SCHEMA',
    'JSONL_WMT25_ST_QA_SCHEMA',
    'JSONL_WMT25_ST_MT_SCHEMA',
    'JSONL_WMT26_LR_MT_SCHEMA',
    'JSONL_WMT26_LR_QA_SCHEMA',
    'JSONL_WMT26_LR_MR_SCHEMA',
    'JSONL_WMT26_LR_SCGC_SCHEMA',
    'validate_jsonl_schema',
    'validate_jsonl_src_testset',
    'validate_jsonl_ref_testset',
    'validate_jsonl_submission',
    'JSON_SCHEMA',
    'validate_json_schema',
    'validate_json_src_testset',
    'validate_json_ref_testset',
    'validate_json_submission',
]
