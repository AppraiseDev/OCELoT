"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

JSONL format schemas and validators.
"""
import json
import tempfile
from gzip import BadGzipFile

import jsonschema
from django.core.exceptions import ValidationError
from sacrebleu.utils import smart_open

from leaderboard.utils import detect_jsonl_format
from leaderboard.utils import JSONL_WMT_ST_MT_FORMAT
from leaderboard.utils import JSONL_WMT_ST_QA_FORMAT
from leaderboard.utils import JSONL_WMT_GENMT_FORMAT

JSONL_WMT25_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "WMT25 JSONL entry",
    "type": "object",
    "properties": {
        "dataset_id":   { "type": "string" },
        "collection_id":{ "type": "string" },
        "doc_id":       { "type": "string" },
        "domain":       { "type": ["string", "null"] },
        "src_lang":     { "type": "string" },
        "tgt_lang":     { "type": "string" },
        "src_text":     { "type": "string" },
        "hypothesis":   { "type": "string" },
    },
    "required": [
        "doc_id","tgt_lang"
    ],
    #"anyOf": [
    #    { "required": ["src_text"] },
    #    { "required": ["hypothesis"] }
    #],
    "additionalProperties": True
}

# requires "dataset_id" to start with "wmtslavicllm2025_" 
JSONL_WMT25_ST_QA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "WMT25-ST QA JSONL entry",
    "type": "object",
    "properties": {
        "dataset_id":      { "type": "string" },
        "correct_answer":  { "type": ["string", "integer"] },
        "pred":            { "type": ["string", "integer"] },
    },
    "required": [
        "dataset_id",
    ],
    "anyOf": [
        { "required": ["correct_answer"] },
        { "required": ["pred"] }
    ],
    "additionalProperties": True
}

# requires "dataset_id" to start with "wmtslavicllm2025_" 
JSONL_WMT25_ST_MT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "WMT25-ST MT JSONL entry",
    "type": "object",
    "properties": {
        "dataset_id": { "type": "string" },
        "sent_id":    { "type": "string" },
        "source":     { "type": "string" },
        "target":     { "type": "string" },
        "pred":       { "type": "string" },
    },
    "required": [
        "dataset_id", "sent_id"
    ],
    "anyOf": [
        { "required": ["source"] },
        { "required": ["pred"] }
    ],
    "additionalProperties": True
}


def validate_jsonl_schema(json_file):
    """Validates JSONL file based on appropriate schema."""
    # Skip validation for non‐JSONL uploads
    if not (json_file.name.endswith('.jsonl') or json_file.name.endswith('.jsonl.gz')):
        return

    # Detect format and choose appropriate schema
    jsonl_format = detect_jsonl_format(json_file)
    if jsonl_format == JSONL_WMT_ST_MT_FORMAT:
        schema = JSONL_WMT25_ST_MT_SCHEMA
    elif jsonl_format == JSONL_WMT_ST_QA_FORMAT:
        schema = JSONL_WMT25_ST_QA_SCHEMA
    else:
        schema = JSONL_WMT25_SCHEMA

    try:
        # Ensure we start at the beginning of the file
        json_file.seek(0)

        # Handle compressed files by using smart_open with file path
        if json_file.name.endswith('.jsonl.gz'):
            # For compressed files, we need to read via file path, not the file object directly
            if hasattr(json_file, 'temporary_file_path'):
                file_path = json_file.temporary_file_path()
            else:
                # For in-memory files, write to temp file first
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl.gz') as temp_file:
                    json_file.seek(0)
                    temp_file.write(json_file.read())
                    file_path = temp_file.name

            try:
                with smart_open(file_path, 'rt', encoding='utf-8') as f:
                    for lineno, line in enumerate(f, start=1):
                        text = line.strip()
                        _validate_jsonl_schema(text, lineno, schema=schema)
            except BadGzipFile as e:
                raise ValidationError(f'JSONL file is not a valid gzip file: {e}')
        else:
            # Handle uncompressed files directly
            for lineno, line in enumerate(json_file, start=1):
                text = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
                _validate_jsonl_schema(text, lineno, schema=schema)
    finally:
        # Reset file pointer so further processing can read it again
        json_file.seek(0)


def _validate_jsonl_schema(text, lineno, schema):
    """Validate a single line of JSONL against the WMT25 JSONL schema."""
    if not text:
        pass  # skip blank lines
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValidationError(f'JSONL file invalid JSON at line {lineno}: {e}')
    try:
        jsonschema.validate(instance=obj, schema=schema)
    except jsonschema.ValidationError as e:
        # Report the first schema violation
        raise ValidationError(f'JSONL file invalid at line {lineno}: {e.message}')


def validate_jsonl_src_testset(json_file):
    """Validate source texts in JSONL test set."""
    if not (json_file.name.endswith('.jsonl') or json_file.name.endswith('.jsonl.gz')):
        return

    json_file.seek(0)
    src_langs = set()

    def _validate_jsonl_src(text, lineno, format):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValidationError(f'JSONL src test set invalid JSON at line {lineno}: {e}')

        if format == JSONL_WMT_ST_MT_FORMAT:
            if not obj.get('source', ""):
                raise ValidationError(f'Missing "source" field at line {lineno} in JSONL src test set')
        elif format == JSONL_WMT_ST_QA_FORMAT:
            if not obj.get('correct_answer', []):
                raise ValidationError(f'Missing "correct_answer" field at line {lineno} in JSONL src test set')
        else:
            # src_lang is optional (WMT26 GenMT blindsets do not provide it)
            lang = obj.get('src_lang')
            if lang is not None:
                src_langs.add(lang)

    jsonl_format = detect_jsonl_format(json_file)

    # Handle compressed files
    if json_file.name.endswith('.jsonl.gz'):
        if hasattr(json_file, 'temporary_file_path'):
            file_path = json_file.temporary_file_path()
        else:
            # For in-memory files, write to temp file first
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl.gz') as temp_file:
                json_file.seek(0)
                temp_file.write(json_file.read())
                file_path = temp_file.name

        with smart_open(file_path, 'rt', encoding='utf-8') as f:
            for lineno, line in enumerate(f, start=1):
                text = line.strip()
                if not text:
                    continue
                _validate_jsonl_src(text, lineno, jsonl_format)
                
    else:
        # Handle uncompressed files
        for lineno, line in enumerate(json_file, start=1):
            text = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
            if not text:
                continue
            _validate_jsonl_src(text, lineno, jsonl_format)

    # src_lang is optional (e.g. WMT26 GenMT blindsets have no src_lang), so it
    # is no longer required to be present.
    json_file.seek(0)


def validate_jsonl_ref_testset(json_file):
    """Validate reference texts in JSONL test set."""
    if not json_file:  # FileField evaluates as False when None
        return
    if not (json_file.name.endswith('.jsonl') or json_file.name.endswith('.jsonl.gz')):
        return

    json_file.seek(0)
    ref_langs = set()

    def _validate_jsonl_ref(text, lineno, format):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValidationError(f'JSONL ref test set invalid JSON at line {lineno}: {e}')

        if format == JSONL_WMT_ST_MT_FORMAT:
            if not obj.get('target', ""):
                raise ValidationError(f'Missing "target" field at line {lineno} in JSONL ref test set')
        elif format == JSONL_WMT_ST_QA_FORMAT:
            if not obj.get('correct_answer', []):
                raise ValidationError(f'Missing "correct_answer" field at line {lineno} in JSONL ref test set')
        else:
            refs = obj.get('refs', [])
            if not refs:
                raise ValidationError(f'No refs array at line {lineno} in JSONL ref test set')
            for ref in refs:
                lang = ref.get('tgt_lang')
                if lang is None:
                    raise ValidationError(f'Missing tgt_lang in refs at line {lineno}')
                ref_langs.add(lang)
    
    # Detect format
    jsonl_format = detect_jsonl_format(json_file)

    # Handle compressed files
    if json_file.name.endswith('.jsonl.gz'):
        if hasattr(json_file, 'temporary_file_path'):
            file_path = json_file.temporary_file_path()
        else:
            # For in-memory files, write to temp file first
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl.gz') as temp_file:
                json_file.seek(0)
                temp_file.write(json_file.read())
                file_path = temp_file.name

        with smart_open(file_path, 'rt', encoding='utf-8') as f:
            for lineno, line in enumerate(f, start=1):
                text = line.strip()
                if not text:
                    continue
                _validate_jsonl_ref(text, lineno, jsonl_format)
                
    else:
        # Handle uncompressed files
        for lineno, line in enumerate(json_file, start=1):
            text = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
            if not text:
                continue
            _validate_jsonl_ref(text, lineno, jsonl_format)

    if (jsonl_format not in [JSONL_WMT_ST_MT_FORMAT, JSONL_WMT_ST_QA_FORMAT] and not ref_langs):
        raise ValidationError(f'No reference languages found in JSONL file {json_file.name}')
    json_file.seek(0)


def validate_jsonl_submission(json_file):
    """Validate submissions in JSONL format."""
    if not (json_file.name.endswith('.jsonl') or json_file.name.endswith('.jsonl.gz')):
        return

    validate_jsonl_schema(json_file)
    json_file.seek(0)
    has_hyps = False

    def _validate_jsonl_hyps(text, lineno, format):
        obj = json.loads(text)
        if format == JSONL_WMT_ST_MT_FORMAT or format == JSONL_WMT_ST_QA_FORMAT:
            hyps = obj.get('pred', "")
            if not hyps:
                raise ValidationError(f'Missing "pred" field at line {lineno} in JSONL submission')
        else:
            hyps = obj.get('hypothesis') or obj.get('hyps') or ""
        return bool(hyps)

    # Detect format
    jsonl_format = detect_jsonl_format(json_file)

    # Handle compressed files
    if json_file.name.endswith('.jsonl.gz'):
        if hasattr(json_file, 'temporary_file_path'):
            file_path = json_file.temporary_file_path()
        else:
            # For in-memory files, write to temp file first
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl.gz') as temp_file:
                json_file.seek(0)
                temp_file.write(json_file.read())
                file_path = temp_file.name

        with smart_open(file_path, 'rt', encoding='utf-8') as f:
            for lineno, line in enumerate(f, start=1):
                text = line.strip()
                if not text:
                    continue
                if _validate_jsonl_hyps(text, lineno, jsonl_format):
                    has_hyps = True
                    break
    else:
        # Handle uncompressed files
        for lineno, line in enumerate(json_file, start=1):
            text = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
            if not text:
                continue
            if _validate_jsonl_hyps(text, lineno, jsonl_format):
                has_hyps = True
                break

    if not has_hyps:
        field_name = "hypothesis" if jsonl_format is JSONL_WMT_GENMT_FORMAT else "pred"
        raise ValidationError(f'Could not find "{field_name}" node anywhere in the JSONL submission')
    json_file.seek(0)
