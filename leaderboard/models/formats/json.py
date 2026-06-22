"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

JSON format schema and validators.
"""
import json
import tempfile

import jsonschema
from django.core.exceptions import ValidationError
from sacrebleu.utils import smart_open

JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "WMT25 MIST JSON entry",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "prompt": { "type": "string" },
            "taskid": { "type": "string" },
            "answer": { "type": "string" }
        },
    },
    "required": ["taskid"],
    "anyOf": [
        { "required": ["prompt"] },
        { "required": ["answer"] }
    ],
    "additionalProperties": True
}


def validate_json_schema(json_file):
    """Validates JSON file based on JSON_SCHEMA."""
    # Skip validation for non-JSON uploads
    if not (json_file.name.endswith('.json') or json_file.name.endswith('.json.gz')):
        return

    try:
        # Ensure we start at the beginning of the file
        json_file.seek(0)

        # Handle compressed files by using smart_open with file path
        if json_file.name.endswith('.json.gz'):
            if hasattr(json_file, 'temporary_file_path'):
                file_path = json_file.temporary_file_path()
            else:
                # For in-memory files, write to temp file first
                with tempfile.NamedTemporaryFile(delete=False, suffix='.json.gz') as temp_file:
                    json_file.seek(0)
                    temp_file.write(json_file.read())
                    file_path = temp_file.name

            with smart_open(file_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # Handle uncompressed files
            content = json_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            data = json.loads(content)

        # Validate against JSON schema
        jsonschema.validate(data, JSON_SCHEMA)

    except json.JSONDecodeError as e:
        raise ValidationError(f'Invalid JSON format in file {json_file.name}: {e}')
    except jsonschema.ValidationError as e:
        raise ValidationError(f'JSON schema validation failed for file {json_file.name}: {e.message}')
    finally:
        # Reset file pointer so further processing can read it again
        json_file.seek(0)


def validate_json_src_testset(json_file):
    """Validate source texts in JSON test set."""
    if not (json_file.name.endswith('.json') or json_file.name.endswith('.json.gz')):
        return

    json_file.seek(0)
    taskids = set()

    # Handle compressed files
    if json_file.name.endswith('.json.gz'):
        if hasattr(json_file, 'temporary_file_path'):
            file_path = json_file.temporary_file_path()
        else:
            # For in-memory files, write to temp file first
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json.gz') as temp_file:
                json_file.seek(0)
                temp_file.write(json_file.read())
                file_path = temp_file.name

        with smart_open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
    else:
        # Handle uncompressed files
        content = json_file.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        data = json.loads(content)

    if not isinstance(data, list):
        raise ValidationError(f'JSON file {json_file.name} must contain an array')

    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            raise ValidationError(f'Item {i} in JSON file {json_file.name} must be an object')
        
        taskid = obj.get('taskid')
        if not taskid:
            raise ValidationError(f'Item {i} in JSON file {json_file.name} is missing required "taskid" field')
        taskids.add(taskid)

        # Check for prompts (source texts)
        if not obj.get('prompt'):
            raise ValidationError(f'Item {i} in JSON file {json_file.name} is missing "prompt" field for source text')

    if not taskids:
        raise ValidationError(f'No task IDs found in JSON file {json_file.name}')
    json_file.seek(0)


def validate_json_ref_testset(json_file):
    """Validate reference texts in JSON test set."""
    if not json_file:  # FileField evaluates as False when None
        return
    if not (json_file.name.endswith('.json') or json_file.name.endswith('.json.gz')):
        return

    json_file.seek(0)
    taskids = set()

    # Handle compressed files
    if json_file.name.endswith('.json.gz'):
        if hasattr(json_file, 'temporary_file_path'):
            file_path = json_file.temporary_file_path()
        else:
            # For in-memory files, write to temp file first
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json.gz') as temp_file:
                json_file.seek(0)
                temp_file.write(json_file.read())
                file_path = temp_file.name

        with smart_open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
    else:
        # Handle uncompressed files
        content = json_file.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        data = json.loads(content)

    if not isinstance(data, list):
        raise ValidationError(f'JSON file {json_file.name} must contain an array')

    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            raise ValidationError(f'Item {i} in JSON file {json_file.name} must be an object')
        
        taskid = obj.get('taskid')
        if not taskid:
            raise ValidationError(f'Item {i} in JSON file {json_file.name} is missing required "taskid" field')
        taskids.add(taskid)

        # Check for answers (reference texts)
        if not obj.get('answer'):
            raise ValidationError(f'Item {i} in JSON file {json_file.name} is missing "answer" field for reference text')

    if not taskids:
        raise ValidationError(f'No task IDs found in JSON file {json_file.name}')
    json_file.seek(0)


def validate_json_submission(json_file):
    """Validate submissions in JSON format."""
    if not (json_file.name.endswith('.json') or json_file.name.endswith('.json.gz')):
        return

    validate_json_schema(json_file)
    json_file.seek(0)
    has_answers = False

    # Handle compressed files
    if json_file.name.endswith('.json.gz'):
        if hasattr(json_file, 'temporary_file_path'):
            file_path = json_file.temporary_file_path()
        else:
            # For in-memory files, write to temp file first
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json.gz') as temp_file:
                json_file.seek(0)
                temp_file.write(json_file.read())
                file_path = temp_file.name

        with smart_open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
    else:
        # Handle uncompressed files
        content = json_file.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        data = json.loads(content)

    if not isinstance(data, list):
        raise ValidationError(f'JSON submission file {json_file.name} must contain an array')

    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            continue
        answer = obj.get('answer')
        if answer:
            has_answers = True
            break

    if not has_answers:
        raise ValidationError(f'Could not find "answer" field anywhere in the JSON submission')
    json_file.seek(0)
