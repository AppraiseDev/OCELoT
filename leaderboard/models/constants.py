"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

Shared constants for the leaderboard models package.
"""

MAX_CODE_LENGTH = 10  # ISO 639 codes need 3 chars, but better add buffer
MAX_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000
MAX_TOKEN_LENGTH = 10
MAX_FORMAT_LENGTH = 5  # SGML, XML, TEXT, JSONL

SGML_FILE = 'SGML'  # supported extensions: .sgm
TEXT_FILE = 'TEXT'  # supported extensions: .txt
XML_FILE = 'XML'  # supported extensions: .xml
JSONL_FILE = 'JSONL'  # supported extensions: .jsonl
JSON_FILE = 'JSON'  # supported extensions: .json

FILE_FORMAT_CHOICES = (
    (SGML_FILE, 'SGML format'),
    (TEXT_FILE, 'Text format'),
    (XML_FILE, 'XML format'),
    (JSONL_FILE, 'JSONL format'),
    (JSON_FILE, 'JSON format'),
)

__all__ = [
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
]
