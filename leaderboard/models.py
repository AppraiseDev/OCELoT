"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import re
import xml
import tempfile
from gzip import BadGzipFile
from pathlib import Path
from uuid import uuid4

import json
import jsonschema
import lxml.etree as ET
import logging  # noqa: F401
import xmlschema

# Logger for leaderboard models
logger = logging.getLogger(__name__)  # noqa: F821
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS
from django.db import models
from sacrebleu import corpus_bleu  # type: ignore
from sacrebleu import corpus_chrf  # type: ignore
from sacrebleu.utils import smart_open

from leaderboard.utils import analyze_xml_file
from leaderboard.utils import process_to_text  # type: ignore
from leaderboard.utils import process_xml_to_text
from leaderboard.utils import analyze_jsonl_file, process_jsonl_to_text
from leaderboard.utils import analyze_json_file, process_json_to_text
from ocelot.settings import MEDIA_ROOT

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

SGML_XSD_SCHEMA = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="tstset" type="TestSetType"/>

  <xs:complexType name="ParagraphType">
    <xs:sequence>
      <xs:element name="seg" maxOccurs="unbounded">
        <xs:complexType>
          <xs:simpleContent>
            <xs:extension base="xs:string">
              <xs:attribute name="id" type="xs:string"/>
            </xs:extension>
          </xs:simpleContent>
        </xs:complexType>
      </xs:element>
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="DocumentType">
    <xs:sequence>
      <xs:element name="p" type="ParagraphType" maxOccurs="unbounded"/>
    </xs:sequence>
    <xs:attribute name="docid" type="xs:string"/>
    <xs:attribute name="sysid" type="xs:string"/>
    <xs:attribute name="genre" type="xs:string"/>
    <xs:attribute name="origlang" type="xs:string"/>
  </xs:complexType>

  <xs:complexType name="TestSetType">
    <xs:sequence>
      <xs:element name="doc" type="DocumentType" maxOccurs="unbounded"/>
    </xs:sequence>
    <xs:attribute name="setid" type="xs:string"/>
    <xs:attribute name="srclang" type="xs:string"/>
    <xs:attribute name="trglang" type="xs:string"/>
  </xs:complexType>

</xs:schema>
"""

XML_RNG_SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0"
         datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
  <define name="Segment">
    <element>
      <name ns="">seg</name>
      <attribute>
        <name ns="">id</name>
        <data type="positiveInteger"/>
      </attribute>
      <optional>
        <attribute>
          <name ns="">type</name>
          <data type="string"/>
        </attribute>
      </optional>
      <text/>
    </element>
  </define>
  <define name="Paragraph">
    <element>
      <name ns="">p</name>
      <zeroOrMore>
        <ref name="Segment"/>
      </zeroOrMore>
    </element>
  </define>
  <define name="Source">
    <element>
      <name ns="">src</name>
      <attribute>
        <name ns="">lang</name>
        <data type="language"/>
      </attribute>
      <optional>
        <attribute>
          <name ns="">translator</name>
          <data type="string"/>
        </attribute>
      </optional>
      <oneOrMore>
        <ref name="Paragraph"/>
      </oneOrMore>
    </element>
  </define>
  <define name="Reference">
    <element>
      <name ns="">ref</name>
      <attribute>
        <name ns="">lang</name>
        <data type="language"/>
      </attribute>
      <optional>
        <attribute>
          <name ns="">translator</name>
          <data type="string"/>
        </attribute>
      </optional>
      <oneOrMore>
        <ref name="Paragraph"/>
      </oneOrMore>
    </element>
  </define>
  <define name="System">
    <element>
      <name ns="">hyp</name>
      <attribute>
        <name ns="">lang</name>
        <data type="language"/>
      </attribute>
      <attribute>
        <name ns="">system</name>
        <data type="string"/>
      </attribute>
      <oneOrMore>
        <ref name="Paragraph"/>
      </oneOrMore>
    </element>
  </define>
  <define name="Document">
    <element>
      <name ns="">doc</name>
      <attribute>
        <name ns="">id</name>
        <data type="string"/>
      </attribute>
      <attribute>
        <name ns="">origlang</name>
        <data type="language"/>
      </attribute>
      <optional>
        <attribute>
          <name ns="">testsuite</name>
          <data type="string"/>
        </attribute>
      </optional>
      <optional>
        <attribute>
          <name ns="">domain</name>
          <data type="string"/>
        </attribute>
      </optional>
      <ref name="Source"/>
      <zeroOrMore>
        <ref name="Reference"/>
      </zeroOrMore>
      <zeroOrMore>
        <ref name="System"/>
      </zeroOrMore>
    </element>
  </define>
  <define name="Collection">
    <element>
      <name ns="">collection</name>
      <attribute>
        <name ns="">id</name>
        <data type="string"/>
      </attribute>
      <oneOrMore>
        <ref name="Document"/>
      </oneOrMore>
    </element>
  </define>
  <define name="Dataset">
    <element>
      <name ns="">dataset</name>
      <attribute>
        <name ns="">id</name>
        <data type="string"/>
      </attribute>
      <zeroOrMore>
        <ref name="Collection"/>
      </zeroOrMore>
      <zeroOrMore>
        <ref name="Document"/>
      </zeroOrMore>
    </element>
  </define>
  <start>
    <ref name="Dataset"/>
  </start>
</grammar>
"""

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
        "dataset_id","doc_id","tgt_lang"
    ],
    #"anyOf": [
    #    { "required": ["src_text"] },
    #    { "required": ["hypothesis"] }
    #],
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
        "dataset_id",
    ],
    "anyOf": [
        { "required": ["source"] },
        { "required": ["pred"] }
    ],
    "additionalProperties": True
}

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


def validate_sgml_schema(hyp_file):
    """Validates SGML file based on XSD schema."""
    if not hyp_file.name.endswith('.sgm'):
        return  # Skip validation for other format files.

    schema = xmlschema.XMLSchema(SGML_XSD_SCHEMA)

    try:
        schema.validate(hyp_file)
    except (
        xmlschema.XMLSchemaValidationError,
        xml.etree.ElementTree.ParseError,
    ) as error:
        _msg = 'SGML file invalid: {0}'.format(error)
        raise ValidationError(_msg)


def validate_xml_src_testset(xml_file):
    """Validate source texts in XML file."""
    if not xml_file.name.endswith('.xml'):
        return  # Skip validation for other formats

    _, src_langs, _, _, _ = analyze_xml_file(xml_file)
    if len(src_langs) == 0:
        _msg = 'No source language found in the XML file {0}'.format(
            xml_file.name
        )
        raise ValidationError(_msg)

    # Two source languages in XML files are allowed since WMT22 Chat Task
    if len(src_langs) > 1:
        _msg = 'XML files with 2+ source languages are not supported'
        raise ValidationError(_msg)


def validate_xml_ref_testset(xml_file):
    """Validate reference texts in XML file."""
    if not xml_file:  # FileField evaluates as False when None
        return

    if not xml_file.name.endswith('.xml'):
        return  # Skip validation for other formats

    _, _, ref_langs, translators, _ = analyze_xml_file(xml_file)
    if len(ref_langs) == 0 or len(translators) == 0:
        _msg = 'No reference found in the XML file {0}'.format(
            xml_file.name
        )
        raise ValidationError(_msg)

    # Two reference languages in XML files are allowed since WMT22 Chat Task
    if len(ref_langs) > 2:
        _msg = 'XML files with 2+ reference languages are not supported'
        raise ValidationError(_msg)
        # Note that multiple references for a single language are supported


def validate_xml_submission(xml_file):
    """Validate submissions in XML format."""
    if not xml_file.name.endswith('.xml'):
        return  # Skip validation for other formats

    validate_xml_schema(xml_file)
    xml_file.seek(0)  # To be able to read() again

    # Check if the submission has some translations from one system only
    _, _, _, _, systems = analyze_xml_file(xml_file)
    if len(systems) == 0:
        _msg = 'No system found in the XML file {0}'.format(xml_file.name)
        raise ValidationError(_msg)
    if len(systems) > 1:
        _msg = 'XML files with multiple systems are not supported'
        raise ValidationError(_msg)

    # TODO: Validate that the collection (if specified in the test set) is
    # present in the file. Do it here or in full_clean()


def validate_xml_schema(xml_file):
    """Validates XML file based on RNG schema."""

    if not xml_file.name.endswith('.xml'):
        return  # Skip validation for other format files.

    is_valid = False
    relaxng = None
    try:
        # Could not make it working with a RNC schema, so using RNG instead.
        # lxml did not use rnc2rng as described in the documentation:
        # https://lxml.de/validation.html#relaxng
        schema = ET.fromstring(XML_RNG_SCHEMA.encode())
        relaxng = ET.RelaxNG(schema)
        hyp_doc = ET.parse(xml_file)
        is_valid = relaxng.validate(hyp_doc)
    except Exception as error:
        _msg = 'XML file invalid: {0}'.format(error)
        raise ValidationError(_msg)

    if not is_valid:
        _msg = 'XML file invalid: {0}. It does not validate against the XML Schema:'.format(
            xml_file,
        )
        if relaxng:
            # Display only the first error
            for _err in relaxng.error_log[:1]:
                _msg += " Line %s: %s\n" % (_err.line, _err.message)
        raise ValidationError(_msg)


def _detect_jsonl_format(json_file):
    """Detect whether a JSONL file uses the new wmtslavicllm2025_ format."""
    json_file.seek(0)
    
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
            for line in f:
                text = line.strip()
                if text:
                    try:
                        obj = json.loads(text)
                        dataset_id = obj.get('dataset_id', '')
                        json_file.seek(0)
                        return dataset_id.startswith('wmtslavicllm2025_')
                    except json.JSONDecodeError:
                        json_file.seek(0)
                        return False
    else:
        # Handle uncompressed files
        for line in json_file:
            text = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
            if text:
                try:
                    obj = json.loads(text)
                    dataset_id = obj.get('dataset_id', '')
                    json_file.seek(0)
                    return dataset_id.startswith('wmtslavicllm2025_')
                except json.JSONDecodeError:
                    json_file.seek(0)
                    return False
    
    json_file.seek(0)
    return False


def validate_jsonl_schema(json_file):
    """Validates JSONL file based on appropriate schema."""
    # Skip validation for non‐JSONL uploads
    if not (json_file.name.endswith('.jsonl') or json_file.name.endswith('.jsonl.gz')):
        return

    # Detect format and choose appropriate schema
    is_st_mt_format = _detect_jsonl_format(json_file)
    schema = JSONL_WMT25_ST_MT_SCHEMA if is_st_mt_format else JSONL_WMT25_SCHEMA

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


def validate_jsonl_src_testset(json_file):
    """Validate source texts in JSONL test set."""
    if not (json_file.name.endswith('.jsonl') or json_file.name.endswith('.jsonl.gz')):
        return

    json_file.seek(0)
    src_langs = set()
    
    # Detect format
    is_st_mt_format = _detect_jsonl_format(json_file)

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
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError as e:
                    raise ValidationError(f'JSONL src test set invalid JSON at line {lineno}: {e}')
                
                if is_st_mt_format:
                    # For ST MT format, check for "source" field
                    if not obj.get('source'):
                        raise ValidationError(f'Missing "source" field at line {lineno} in JSONL src test set')
                    # For ST MT format, we don't have explicit language fields
                    # but we can derive from dataset_id
                    dataset_id = obj.get('dataset_id', '')
                    if dataset_id.startswith('wmtslavicllm2025_'):
                        # Extract language pair from dataset_id (e.g., wmtslavicllm2025_de-dsb)
                        lang_pair = dataset_id.replace('wmtslavicllm2025_', '')
                        if '-' in lang_pair:
                            src_lang = lang_pair.split('-')[0]
                            src_langs.add(src_lang)
                else:
                    # For standard WMT25 format
                    lang = obj.get('src_lang')
                    if lang is None:
                        raise ValidationError(f'Missing src_lang at line {lineno} in JSONL src test set')
                    src_langs.add(lang)
    else:
        # Handle uncompressed files
        for lineno, line in enumerate(json_file, start=1):
            text = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as e:
                raise ValidationError(f'JSONL src test set invalid JSON at line {lineno}: {e}')
            
            if is_st_mt_format:
                # For ST MT format, check for "source" field
                if not obj.get('source'):
                    raise ValidationError(f'Missing "source" field at line {lineno} in JSONL src test set')
                # For ST MT format, we don't have explicit language fields
                # but we can derive from dataset_id
                dataset_id = obj.get('dataset_id', '')
                if dataset_id.startswith('wmtslavicllm2025_'):
                    # Extract language pair from dataset_id (e.g., wmtslavicllm2025_de-dsb)
                    lang_pair = dataset_id.replace('wmtslavicllm2025_', '')
                    if '-' in lang_pair:
                        src_lang = lang_pair.split('-')[0]
                        src_langs.add(src_lang)
            else:
                # For standard WMT25 format
                lang = obj.get('src_lang')
                if lang is None:
                    raise ValidationError(f'Missing src_lang at line {lineno} in JSONL src test set')
                src_langs.add(lang)

    if not src_langs:
        raise ValidationError(f'No source language found in JSONL file {json_file.name}')
    json_file.seek(0)


def validate_jsonl_ref_testset(json_file):
    """Validate reference texts in JSONL test set."""
    if not json_file:  # FileField evaluates as False when None
        return
    if not (json_file.name.endswith('.jsonl') or json_file.name.endswith('.jsonl.gz')):
        return

    json_file.seek(0)
    ref_langs = set()
    
    # Detect format
    is_st_mt_format = _detect_jsonl_format(json_file)

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
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError as e:
                    raise ValidationError(f'JSONL ref test set invalid JSON at line {lineno}: {e}')
                
                if is_st_mt_format:
                    # For ST MT format, check for "target" field
                    if not obj.get('target'):
                        raise ValidationError(f'Missing "target" field at line {lineno} in JSONL ref test set')
                    # For ST MT format, we don't have explicit language fields
                    # but we can derive from dataset_id
                    dataset_id = obj.get('dataset_id', '')
                    if dataset_id.startswith('wmtslavicllm2025_'):
                        # Extract language pair from dataset_id (e.g., wmtslavicllm2025_de-dsb)
                        lang_pair = dataset_id.replace('wmtslavicllm2025_', '')
                        if '-' in lang_pair:
                            tgt_lang = lang_pair.split('-')[1]
                            ref_langs.add(tgt_lang)
                else:
                    # For standard WMT25 format
                    refs = obj.get('refs')
                    if not refs:
                        raise ValidationError(f'No refs array at line {lineno} in JSONL ref test set')
                    for ref in refs:
                        lang = ref.get('tgt_lang')
                        if lang is None:
                            raise ValidationError(f'Missing tgt_lang in refs at line {lineno}')
                        ref_langs.add(lang)
    else:
        # Handle uncompressed files
        for lineno, line in enumerate(json_file, start=1):
            text = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as e:
                raise ValidationError(f'JSONL ref test set invalid JSON at line {lineno}: {e}')
            
            if is_st_mt_format:
                # For ST MT format, check for "target" field
                if not obj.get('target'):
                    raise ValidationError(f'Missing "target" field at line {lineno} in JSONL ref test set')
                # For ST MT format, we don't have explicit language fields
                # but we can derive from dataset_id
                dataset_id = obj.get('dataset_id', '')
                if dataset_id.startswith('wmtslavicllm2025_'):
                    # Extract language pair from dataset_id (e.g., wmtslavicllm2025_de-dsb)
                    lang_pair = dataset_id.replace('wmtslavicllm2025_', '')
                    if '-' in lang_pair:
                        tgt_lang = lang_pair.split('-')[1]
                        ref_langs.add(tgt_lang)
            else:
                # For standard WMT25 format
                refs = obj.get('refs')
                if not refs:
                    raise ValidationError(f'No refs array at line {lineno} in JSONL ref test set')
                for ref in refs:
                    lang = ref.get('tgt_lang')
                    if lang is None:
                        raise ValidationError(f'Missing tgt_lang in refs at line {lineno}')
                    ref_langs.add(lang)

    if not ref_langs:
        raise ValidationError(f'No reference languages found in JSONL file {json_file.name}')
    json_file.seek(0)


def validate_jsonl_submission(json_file):
    """Validate submissions in JSONL format."""
    if not (json_file.name.endswith('.jsonl') or json_file.name.endswith('.jsonl.gz')):
        return

    validate_jsonl_schema(json_file)
    json_file.seek(0)
    has_hyps = False
    
    # Detect format
    is_st_mt_format = _detect_jsonl_format(json_file)

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
                obj = json.loads(text)
                
                if is_st_mt_format:
                    # For ST MT format, check for "pred" field
                    hyps = obj.get('pred', "")
                else:
                    # For standard WMT25 format
                    hyps = obj.get('hypothesis') or obj.get('hyps') or ""
                
                if hyps:
                    has_hyps = True
                    break
    else:
        # Handle uncompressed files
        for lineno, line in enumerate(json_file, start=1):
            text = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
            if not text:
                continue
            obj = json.loads(text)
            
            if is_st_mt_format:
                # For ST MT format, check for "pred" field
                hyps = obj.get('pred', "")
            else:
                # For standard WMT25 format
                hyps = obj.get('hypothesis') or obj.get('hyps') or ""
            
            if hyps:
                has_hyps = True
                break

    if not has_hyps:
        field_name = "pred" if is_st_mt_format else "hypothesis"
        raise ValidationError(f'Could not find "{field_name}" node anywhere in the JSONL submission')
    json_file.seek(0)



def validate_team_name(value):
    """Validates team name matches r'^[a-zA-Z0-9_\\- ]{2,32}$'."""
    valid_name = re.compile(r'^[a-zA-Z0-9_\- ]{2,32}$')
    if not valid_name.match(value):
        _msg = 'Team name must match regexp r"^[a-zA-Z0-9_\\- ]{2,32}$"'
        raise ValidationError(_msg)


def validate_institution_name(value):
    """Validates institution name: UTF-8 Latin script or LaTeX escape
    sequences.
    """
    valid_name = re.compile(r'^[\u0000-\u017F]{2,32}$')
    if not valid_name.match(value):
        _msg = (
            'Institution name must consist only of UTF-8 Latin script '
            'or LaTeX escape sequences, and max 32 characters.'
        )
        raise ValidationError(_msg)


def validate_publication_name(value):
    """Validates short publication name: ASCII letters, digits, dot, dash
    and underscore, no whitespace.
    """
    # Keeping max 32 characters for backward compatibility
    valid_name = re.compile(r'^[a-zA-Z0-9_\-.]{2,32}$')
    if not valid_name.match(value):
        _msg = 'Short publication name must match regexp r"^[a-zA-Z0-9._\\-.]{2,12}$"'
        raise ValidationError(_msg)


def validate_token(value):
    """Validates token matches r'[a-f0-9]{10}'."""
    valid_token = re.compile(r'[a-f0-9]{10}')
    if not valid_token.match(value):
        _msg = 'Token must match regexp r"[a-f0-9]{10}"'
        raise ValidationError(_msg)


class Competition(models.Model):
    """Models a competition."""

    is_active = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is active competition?',
    )

    # True or False overrides the setting from TestSet and Submission.
    # Set to None to fallback to TestSet.is_public
    is_public = models.BooleanField(
        blank=True,
        db_index=True,
        default=None,
        help_text='Are submissions publicly visible? '
        'Overwrites settings in test sets and submissions unless Unknown',
        null=True,
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        help_text=(
            'Competition name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
        max_length=MAX_NAME_LENGTH,
        unique=True,
    )

    description = models.TextField(
        blank=False,
        help_text=(
            'Competition description (max {0} characters)'.format(
                MAX_DESCRIPTION_LENGTH
            )
        ),
        max_length=MAX_DESCRIPTION_LENGTH,
    )

    # Date and time when the competition starts
    start_time = models.DateTimeField(
        blank=True,
        help_text='Competition start time (an empty value means no start time)',
        null=True,
    )

    # Date and time when the competition ends
    deadline = models.DateTimeField(
        blank=True,
        help_text='Competition deadline (an empty value means no deadline)',
        null=True,
    )

    def __repr__(self):
        return (
            'Competition(name={0}, start_time={1}, deadline={2})'.format(
                self.name, self.start_time, self.deadline
            )
        )

    def __str__(self):
        return self.name


class Language(models.Model):
    """Models a language."""

    code = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_CODE_LENGTH,
        help_text=(
            'ISO 639 code (max {0} characters)'.format(MAX_CODE_LENGTH)
        ),
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Language name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
    )

    def __repr__(self):
        return 'Language(code={0}, name={1})'.format(self.code, self.name)

    def __str__(self):
        return '{0} ({1})'.format(self.name, self.code)


class TestSet(models.Model):
    """Models a test set."""

    is_active = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is active test set?',
    )

    # True or False overrides the setting from Submission.
    # Set to None to fallback to Submission.is_public
    is_public = models.BooleanField(
        blank=True,
        db_index=True,
        default=None,
        help_text='Are submissions publicly visible? '
        'Overwrite settings from submissions unless Unknown',
        null=True,
    )

    compute_scores = models.BooleanField(
        blank=False,
        db_index=True,
        default=True,
        help_text='Compute automatic scores?',
    )

    validate = models.BooleanField(
        blank=False,
        db_index=True,
        default=True,
        help_text='Validate submissions for this test set? Set to False to skip validation',
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Test set name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
    )

    source_language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name='source_language_set',
        null=True,
        blank=True,
        help_text='Source language (optional for multi-language test sets)',
    )

    target_language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name='target_language_set',
        null=True,
        blank=True,
        help_text='Target language (optional for multi-language test sets)',
    )

    file_format = models.CharField(
        choices=FILE_FORMAT_CHOICES,
        default=XML_FILE,
        max_length=MAX_FORMAT_LENGTH,
    )

    src_file = models.FileField(
        blank=True,
        upload_to='testsets',
        help_text='XML, JSONL (optionally compressed as .jsonl.gz), JSON (optionally compressed as .json.gz) or text file containing test set source',
        null=True,
        validators=[
            validate_xml_src_testset,
            validate_jsonl_src_testset,
            validate_json_src_testset,
        ],
    )

    ref_file = models.FileField(
        blank=True,
        upload_to='testsets',
        help_text='XML, JSONL (optionally compressed as .jsonl.gz), JSON (optionally compressed as .json.gz) or text file containing test set reference(s)',
        null=True,
        validators=[
            validate_xml_ref_testset,
            validate_jsonl_ref_testset,
            validate_json_ref_testset,
        ],
    )

    competition = models.ForeignKey(
        Competition,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='test_sets',
        related_query_name='test_sets',
    )

    # If a collection ID is provided, automatic scores are computed only on the
    # data from that collection
    collection = models.CharField(
        blank=True,
        null=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Optional collection name (max {0} characters)'.format(
                MAX_NAME_LENGTH
            )
        ),
    )

    def __repr__(self):
        source_code = self.source_language.code if self.source_language else 'multi'
        target_code = self.target_language.code if self.target_language else 'multi'
        return 'TestSet(name={0}, source={1}, target={2}, src={3}, ref={4}, collection={5})'.format(
            self.name,
            source_code,
            target_code,
            self.src_file.name,
            self.ref_file.name,
            self.collection,
        )

    def __str__(self):
        source_code = self.source_language.code if self.source_language else '*'
        target_code = self.target_language.code if self.target_language else '*'
        return '{0} test set ({1}-{2})'.format(
            self.name,
            source_code,
            target_code,
        )

    def _create_text_files(self):
        """
        Creates test set text files from SGML, XML, JSONL or JSON files.
        If files are already in text format, do nothing.
        For XML/JSONL/JSON formats, it extracts data only from the collection if defined.
        """
        if self.file_format == TEXT_FILE:
            return

        if self.file_format == SGML_FILE:
            for sgml_file in (self.ref_file, self.src_file):
                sgml_path = str(sgml_file.name)
                text_path = sgml_path.replace('.sgm', '.txt')
                if not Path(text_path).exists():
                    process_to_text(sgml_path, text_path)

        elif self.file_format == XML_FILE:
            # Extract source text
            src_path = str(self.src_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in src_path:
                src_path = str(Path(MEDIA_ROOT) / src_path)

            txt_path = src_path.replace('.xml', '.txt')

            if not Path(txt_path).exists():
                # After validation it's guaranteed that src_langs has only one element
                _, src_langs, _, _, _ = analyze_xml_file(src_path)
                process_xml_to_text(
                    src_path,
                    txt_path,
                    source=src_langs.pop(),
                    collection=self.collection,
                )

            if not self.has_references():  # Reference file may not exist
                return

            # Extract reference texts; multiple references will be tab-separated
            ref_path = str(self.ref_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in ref_path:
                ref_path = str(Path(MEDIA_ROOT) / ref_path)
            txt_path = ref_path.replace('.xml', '.txt')

            if not Path(txt_path).exists():
                _, _, _, translators, _ = analyze_xml_file(ref_path)
                # Sort to guarantee reproducibility
                # Scores will be computed against the first reference only
                translator = sorted(list(translators))[0]
                process_xml_to_text(
                    ref_path,
                    txt_path,
                    reference=translator,
                    collection=self.collection,
                )

        elif self.file_format == JSONL_FILE:
            # Extract source text
            src_path = str(self.src_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in src_path:
                src_path = str(Path(MEDIA_ROOT) / src_path)
            # Handle both .jsonl and .jsonl.gz files
            if src_path.endswith('.jsonl.gz'):
                txt_src = src_path.replace('.jsonl.gz', '.txt')
            else:
                txt_src = src_path.replace('.jsonl', '.txt')

            # use the shared JSONL‐to‐text processor
            process_jsonl_to_text(
                jsonl_path=src_path,
                txt_path=txt_src,
                source=True,
                collection=self.collection,
            )

            if not self.has_references():
                return

            # Extract reference texts
            ref_path = str(self.ref_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in ref_path:
                ref_path = str(Path(MEDIA_ROOT) / ref_path)
            # Handle both .jsonl and .jsonl.gz files
            if ref_path.endswith('.jsonl.gz'):
                txt_ref = ref_path.replace('.jsonl.gz', '.txt')
            else:
                txt_ref = ref_path.replace('.jsonl', '.txt')

            # pick first translator for reference extraction
            translators = analyze_jsonl_file(ref_path).get('translators', [])
            translator = sorted(translators)[0] if translators else None

            process_jsonl_to_text(
                jsonl_path=ref_path,
                txt_path=txt_ref,
                reference=translator,
                collection=self.collection,
            )

        elif self.file_format == JSON_FILE:
            # Extract source text
            src_path = str(self.src_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in src_path:
                src_path = str(Path(MEDIA_ROOT) / src_path)
            # Handle both .json and .json.gz files
            if src_path.endswith('.json.gz'):
                txt_src = src_path.replace('.json.gz', '.txt')
            else:
                txt_src = src_path.replace('.json', '.txt')

            # use the shared JSON‐to‐text processor
            process_json_to_text(
                json_path=src_path,
                txt_path=txt_src,
                source=True,
            )

            if not self.has_references():
                return

            # Extract reference texts
            ref_path = str(self.ref_file.name)
            if MEDIA_ROOT and MEDIA_ROOT not in ref_path:
                ref_path = str(Path(MEDIA_ROOT) / ref_path)
            # Handle both .json and .json.gz files
            if ref_path.endswith('.json.gz'):
                txt_ref = ref_path.replace('.json.gz', '.txt')
            else:
                txt_ref = ref_path.replace('.json', '.txt')

            process_json_to_text(
                json_path=ref_path,
                txt_path=txt_ref,
                system=True,  # Extract answers as references
            )

        # if we reach here, file_format was neither TEXT, SGML, XML, JSONL nor JSON…
        return

    def has_references(self):
        """Returns True when self.ref_file is not None."""
        return bool(self.ref_file)

    def full_clean(self, exclude=None, validate_unique=True):
        """Validates test set files."""
        for current_file in (self.ref_file, self.src_file):
            if not self.has_references():  # Reference file may not exist
                continue

            current_path = str(current_file.name)

            if self.file_format == SGML_FILE:
                if not current_path.endswith('.sgm'):
                    _msg = 'Invalid SGML file name {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

            elif self.file_format == XML_FILE:
                if not current_path.endswith('.xml'):
                    _msg = 'Invalid XML file named {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

                # TODO: Validate that a collection (if requested) is present in
                # the XML file. Do it here or in validate_xml_submission()

            elif self.file_format == JSONL_FILE:
                if not (current_path.endswith('.jsonl') or current_path.endswith('.jsonl.gz')):
                    _msg = 'Invalid JSONL file name {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

            elif self.file_format == JSON_FILE:
                if not (current_path.endswith('.json') or current_path.endswith('.json.gz')):
                    _msg = 'Invalid JSON file name {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

            elif self.file_format == TEXT_FILE:
                if not current_path.endswith('.txt'):
                    _msg = 'Invalid text file name {0}'.format(
                        current_path
                    )
                    raise ValidationError(_msg)

        super().full_clean(
            exclude=exclude, validate_unique=validate_unique
        )

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=DEFAULT_DB_ALIAS,
        update_fields=None,
    ):
        """Creates test set text files on save()."""
        super().save(force_insert, force_update, using, update_fields)
        if self.id:
            self._create_text_files()


class Team(models.Model):
    """Models a team."""

    is_active = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is active?',
    )

    is_flagged = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is flagged?',
    )

    is_removed = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is removed?',
    )

    is_verified = models.BooleanField(
        blank=False,
        db_index=True,
        default=True,  # make the team verified by default, changed from WMT25
        help_text='Is verified?',
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Team name (max {0} characters)'.format(32)  # see validation
        ),
        unique=True,
        validators=[validate_team_name],
    )

    email = models.EmailField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text='Team email',
    )

    institution_name = models.CharField(
        blank=True,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Institution name (max {0} characters)'.format(
                32
            )  # see validation
        ),
        validators=[validate_institution_name],
    )

    publication_name = models.CharField(
        blank=True,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Team short name (max {0} characters)'.format(
                32
            )  # see validation
        ),
        validators=[validate_publication_name],
    )

    publication_url = models.CharField(
        blank=True,
        max_length=MAX_NAME_LENGTH,
        help_text='Publication URL or citation',
    )

    description = models.TextField(
        blank=True,
        max_length=MAX_DESCRIPTION_LENGTH,
        help_text=(
            'Team description (max {0} characters)'.format(
                MAX_DESCRIPTION_LENGTH
            )
        ),
    )

    token = models.CharField(
        blank=True,
        db_index=True,
        max_length=MAX_TOKEN_LENGTH,
        unique=True,
        validators=[validate_token],
    )

    def __repr__(self):
        return 'Team(name={0}, email={1}, token={2})'.format(
            self.name, self.email, self.token
        )

    def __str__(self):
        return '{0} ({1})'.format(self.name, self.email)

    def _submissions(self):
        return Submission.objects.filter(submitted_by=self).count()

    def _primary_submissions(self):
        return Submission.objects.filter(
            submitted_by=self,
            is_primary=True,
        ).count()

    def _compute_token(self):
        token = uuid4().hex[:MAX_TOKEN_LENGTH]
        self.token = token
        self.save()

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=DEFAULT_DB_ALIAS,
        update_fields=None,
    ):
        """Compute token on save()."""
        super().save(force_insert, force_update, using, update_fields)
        if not self.token and self.id:
            self._compute_token()


def _get_submission_upload_path(instance, filename):
    """Construct upload path based on test set and team data."""
    # Use filename to determine if it's compressed
    is_compressed = filename and filename.endswith('.gz')

    submissions_count = 0
    submissions_for_team = Submission.objects.filter(
        submitted_by=instance.submitted_by.id,
        test_set=instance.test_set,
    )
    if submissions_for_team.exists():
        submissions_count = submissions_for_team.count()

    if instance.file_format == SGML_FILE:
        file_extension = 'sgm'

    elif instance.file_format == XML_FILE:
        file_extension = 'xml'

    elif instance.file_format == JSONL_FILE:
        file_extension = 'jsonl.gz' if is_compressed else 'jsonl'

    elif instance.file_format == JSON_FILE:
        file_extension = 'json.gz' if is_compressed else 'json'

    elif instance.file_format == TEXT_FILE:
        file_extension = 'txt'

    source_code = instance.test_set.source_language.code if instance.test_set.source_language else 'multi'
    target_code = instance.test_set.target_language.code if instance.test_set.target_language else 'multi'

    new_filename = 'submissions/{0}.{1}-{2}.{3}.{4}.{5}'.format(
        instance.test_set.name,
        source_code,
        target_code,
        instance.submitted_by.name,
        submissions_count + 1,
        file_extension,
    )
    new_filename = new_filename.replace(' ', '_').lower()
    return new_filename


class Submission(models.Model):
    """Models a submission."""

    date_created = models.DateTimeField(
        auto_now_add=True,
        null=True,
        help_text='Creation date of this submission',
    )

    is_constrained = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is constrained submission?',
    )

    is_open_source = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is open-source submission?',
    )

    is_contrastive = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is contrastive submission?',
    )

    is_flagged = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is flagged?',
    )

    is_primary = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is primary sumission?',
    )

    is_public = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is publicly visible? '
        'Can be overwritten by settings of the test set or competition',
    )

    is_removed = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is removed?',
    )

    is_valid = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is valid?',
    )

    is_withdrawn = models.BooleanField(
        blank=False,
        db_index=True,
        default=False,
        help_text='Is withdrawn?',
    )

    name = models.CharField(
        blank=False,
        db_index=True,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Submission name (max {0} characters)'.format(MAX_NAME_LENGTH)
        ),
    )

    # TODO: This field is not used? Fix or remove.
    original_name = models.CharField(
        blank=False,
        editable=False,
        max_length=MAX_NAME_LENGTH,
        help_text=(
            'Original file name (max {0} characters)'.format(
                MAX_NAME_LENGTH
            )
        ),
    )

    score = models.FloatField(
        blank=True, db_index=True, help_text='SacreBLEU score', null=True
    )

    score_chrf = models.FloatField(
        blank=True, db_index=True, help_text='chrF score', null=True
    )

    file_format = models.CharField(
        choices=FILE_FORMAT_CHOICES,
        default=XML_FILE,
        max_length=MAX_FORMAT_LENGTH,
    )

    hyp_file = models.FileField(
        upload_to=_get_submission_upload_path,
        help_text='Submission file containing system output',
        null=True,
        validators=[
            validate_sgml_schema,
            validate_xml_submission,
            validate_jsonl_submission,
            validate_json_submission,
        ],
    )

    test_set = models.ForeignKey(TestSet, on_delete=models.PROTECT)

    submitted_by = models.ForeignKey(
        Team, on_delete=models.PROTECT, blank=True, null=True
    )

    def is_anonymous(self):
        """Checks if the submission is not publicly visible, taking into
        account settings at test set and competition levels."""
        # If the submission's test set is a part of a competition and the
        # competition has public visibility set (i.e. is not Unknown)
        if (
            self.test_set.competition
            and self.test_set.competition.is_public is not None
        ):
            return not self.test_set.competition.is_public
        # If the submission's test set has public visibility set (i.e. is not
        # Unknown)
        if self.test_set.is_public is not None:
            return not self.test_set.is_public
        # Otherwise, look at the submission public visibility only
        return not self.is_public

    def __repr__(self):
        return 'Submission(name={0}, is_primary={1})'.format(
            self.name, self.is_primary
        )

    def __str__(self):
        _name = 'Anonymous' if self.is_anonymous() else self.name
        return '{0} submission #{1}'.format(_name, self.id)

    def get_hyp_text(self, path_only=False):
        """Returns a list of hypothesis segments.

        Args:
            path_only (bool): Return a path to the hypothesis file instead of
                a list of hypothesis segments

        Returns:
            list/str: A list of segments unless path_only and a file path
                otherwise
        """

        # later it will throw OSError if the file does not exist
        hyp_path = self.hyp_file.path

        if self.file_format == SGML_FILE:
            if self.test_set.file_format == SGML_FILE:
                hyp_filtered_path = hyp_path.replace(
                    '.sgm', '.filtered.sgm'
                )
                if not Path(hyp_filtered_path).exists():
                    # Get docids from ref SGML path -- these are non "testsuite-"
                    ref_docids = Submission._get_docids_from_path(
                        self.test_set.ref_file.name
                    )

                    # Filter hyp SGML in matching order, skipping testsuite-* docs
                    hyp_filtered_path = Submission._filter_sgml_by_docids(
                        self.hyp_file.name,
                        ref_docids,
                    )
            else:
                hyp_filtered_path = hyp_path

            # Create text version of (possibly filtered) hyp SGML
            hyp_text_path = hyp_filtered_path.replace('.sgm', '.txt')
            if not Path(hyp_text_path).exists():
                process_to_text(hyp_filtered_path, hyp_text_path)

        elif self.file_format == XML_FILE:
            # Use resolved path
            hyp_text_path = hyp_path.replace('.xml', '.txt')
            if not Path(hyp_text_path).exists():
                _, _, _, _, sys_names = analyze_xml_file(hyp_path)
                # There will be no text version if no collection found
                # if self.test_set.collection and self.test_set.collection not in collections:
                # hyp_text_path = None
                # It should never happen that there is no system translations
                # thanks to validation, but better to check
                if len(sys_names) > 0:
                    process_xml_to_text(
                        hyp_path,
                        hyp_text_path,
                        system=sys_names.pop(),
                        collection=self.test_set.collection,
                    )

        elif self.file_format == JSONL_FILE:
            # Use resolved hyp_path
            # Handle both .jsonl and .jsonl.gz files
            if hyp_path.endswith('.jsonl.gz'):
                hyp_text_path = hyp_path.replace('.jsonl.gz', '.txt')
            else:
                hyp_text_path = hyp_path.replace('.jsonl', '.txt')

            if not Path(hyp_text_path).exists():
                output = analyze_jsonl_file(hyp_path)
                sys_names = output.get('systems', [])

                # use the shared JSONL‐to‐text processor
                process_jsonl_to_text(
                    jsonl_path=hyp_path,
                    txt_path=hyp_text_path,
                    system=sys_names.pop() if sys_names else True,
                    collection=self.test_set.collection,
                )

        elif self.file_format == JSON_FILE:
            # Use resolved hyp_path
            # Handle both .json and .json.gz files
            if hyp_path.endswith('.json.gz'):
                hyp_text_path = hyp_path.replace('.json.gz', '.txt')
            else:
                hyp_text_path = hyp_path.replace('.json', '.txt')

            if not Path(hyp_text_path).exists():
                # use the shared JSON‐to‐text processor
                process_json_to_text(
                    json_path=hyp_path,
                    txt_path=hyp_text_path,
                    system=True,  # Extract answers from JSON
                )

        elif self.file_format == TEXT_FILE:
            hyp_text_path = hyp_path

        if path_only:
            return hyp_text_path
        hyp_stream = (r for r in open(hyp_text_path, encoding='utf-8'))
        return hyp_stream


    def get_ref_text(self, path_only=False):
        """Returns a list of reference segments.

        Args:
            path_only (bool): Return a path to the reference file instead of
                a list of hypothesis segments

        Returns:
            list/str: A list of segments unless path_only and a file path
                otherwise
        """
        # Reference file may not exist
        if not self.test_set.has_references():
            return

        if self.test_set.file_format == SGML_FILE:
            # By design, the reference only contains valid docids
            ref_sgml_path = self.test_set.ref_file.name
            ref_text_path = ref_sgml_path.replace('.sgm', '.txt')

        elif self.test_set.file_format == XML_FILE:
            # By design, the reference only contains valid docids
            ref_xml_path = self.test_set.ref_file.name
            ref_text_path = ref_xml_path.replace('.xml', '.txt')

        elif self.test_set.file_format == JSONL_FILE:
            ref_jsonl_path = self.test_set.ref_file.name
            # Handle both .jsonl and .jsonl.gz files
            if ref_jsonl_path.endswith('.jsonl.gz'):
                ref_text_path = ref_jsonl_path.replace('.jsonl.gz', '.txt')
            else:
                ref_text_path = ref_jsonl_path.replace('.jsonl', '.txt')

        elif self.test_set.file_format == JSON_FILE:
            ref_json_path = self.test_set.ref_file.name
            # Handle both .json and .json.gz files
            if ref_json_path.endswith('.json.gz'):
                ref_text_path = ref_json_path.replace('.json.gz', '.txt')
            else:
                ref_text_path = ref_json_path.replace('.json', '.txt')

        elif self.test_set.file_format == TEXT_FILE:
            ref_text_path = self.test_set.ref_file.name

        if MEDIA_ROOT:
            ref_text_path = str(Path(MEDIA_ROOT) / ref_text_path)

        if path_only:
            return ref_text_path
        return (r for r in open(ref_text_path, encoding='utf-8'))

    def get_src_text(self):
        """Returns a list of source segments."""
        if self.test_set.file_format == SGML_FILE:
            src_sgml_path = self.test_set.src_file.name
            src_text_path = src_sgml_path.replace('.sgm', '.txt')

        elif self.test_set.file_format == XML_FILE:
            src_xml_path = self.test_set.src_file.name
            src_text_path = src_xml_path.replace('.xml', '.txt')

        elif self.test_set.file_format == JSONL_FILE:
            src_jsonl_path = self.test_set.src_file.name
            # Handle both .jsonl and .jsonl.gz files
            if src_jsonl_path.endswith('.jsonl.gz'):
                src_text_path = src_jsonl_path.replace('.jsonl.gz', '.txt')
            else:
                src_text_path = src_jsonl_path.replace('.jsonl', '.txt')

        elif self.test_set.file_format == JSON_FILE:
            src_json_path = self.test_set.src_file.name
            # Handle both .json and .json.gz files
            if src_json_path.endswith('.json.gz'):
                src_text_path = src_json_path.replace('.json.gz', '.txt')
            else:
                src_text_path = src_json_path.replace('.json', '.txt')

        elif self.test_set.file_format == TEXT_FILE:
            src_text_path = self.test_set.src_file.name

        if MEDIA_ROOT:
            src_text_path = str(Path(MEDIA_ROOT) / src_text_path)

        src_stream = (r for r in open(src_text_path, encoding='utf-8'))
        return src_stream

    def is_yours(self, ocelot_team_token):
        """Checks if the submission is from the specific team."""
        return (
            ocelot_team_token is not None
            and self.submitted_by.token == ocelot_team_token
        )

    @staticmethod
    def _get_docids_from_path(sgml_path, encoding='utf-8'):
        """Gets list of docids from SGML path."""

        with open(sgml_path, encoding=encoding) as sgml_handle:
            sgml_soup = BeautifulSoup(sgml_handle, 'lxml-xml')

        sgml_docids = []
        sgml_regexp = re.compile('doc', re.IGNORECASE)
        for doc in sgml_soup.find_all(sgml_regexp):
            docid = doc.attrs.get('docid')
            sgml_docids.append(docid)

        return sgml_docids

    @staticmethod
    def _filter_sgml_by_docids(sgml_path, docids, encoding='utf-8'):
        """Creates filtered SGML file which contains only docids."""

        valid_docids = [x.lower() for x in docids]

        with open(sgml_path, encoding=encoding) as sgml_handle:
            sgml_soup = BeautifulSoup(sgml_handle, 'lxml-xml')

        sgml_docs = {}
        sgml_regexp = re.compile('doc', re.IGNORECASE)
        for doc in sgml_soup.find_all(sgml_regexp):
            docid = doc.attrs.get('docid', '').lower()
            if not docid in valid_docids:
                doc.extract()
                continue
            sgml_docs[docid] = doc.extract()

        for docid in valid_docids:
            if docid in sgml_docs.keys() and sgml_soup.tstset:
                sgml_soup.tstset.append(sgml_docs[docid])

        sgml_filtered_path = sgml_path.replace('.sgm', '.filtered.sgm')
        with open(sgml_filtered_path, 'w', encoding=encoding) as out_file:
            out_soup = str(sgml_soup)
            out_soup = out_soup.replace(
                '<?xml version="1.0" encoding="utf-8"?>', ''
            )
            out_file.write(out_soup.strip())

        return sgml_filtered_path

    def _compute_score(self):
        """Computes sacreBLEU scores for current submission."""

        # Reference file may not exist
        if not self.test_set.has_references():
            return

        # Do not compute scores if instructed not to do so
        if not self.test_set.compute_scores:
            return

        tokenize = '13a'
        if self.test_set.target_language:
            target_language_code = self.test_set.target_language.code
            if target_language_code == 'ja':
                # We use char-based tokenizer as MeCab was slow/unstable
                tokenize = 'char'
            elif target_language_code == 'km':
                tokenize = 'char'
            elif target_language_code == 'zh':
                tokenize = 'zh'

        # _msg = 'language: {0}, tokenize: {1}'.format(
        # target_language_code, tokenize
        # )
        # print(_msg)

        hyp_text_path = self.get_hyp_text(path_only=True)
        ref_text_path = self.get_ref_text(path_only=True)

        try:
            hyp_stream = [x for x in open(hyp_text_path, encoding='utf-8')]
            ref_stream = [r for r in open(ref_text_path, encoding='utf-8')]

            bleu = corpus_bleu(hyp_stream, [ref_stream], tokenize=tokenize)
            self.score = bleu.score

            chrf = corpus_chrf(hyp_stream, [ref_stream])
            self.score_chrf = chrf.score

        except Exception:
            # Don't set score to None, as that would trigger infinite loop
            # TODO: this should provide an error message to the user
            # TODO: the error message should be specific. A simple yet ugly
            # solution would be to use self.score as error codes to propagate
            # the source of the error
            self.score = -1
            self.score_chrf = None

        finally:
            if not self.score:  # temporary fix to check if this may prevent infinite loop
                self.score = -2
            self.save()

    def _score(self):
        """Returns human-readable SacreBLEU score."""
        try:
            if self.score:
                return round(self.score, 1)
            return '---'

        except TypeError:
            return '---'

    def _chrf(self):
        """Returns human-readable chrF score."""
        try:
            if self.score_chrf:
                return round(self.score_chrf, 1)
            return '---'

        except TypeError:
            return '---'

    def _source_language(self):
        """Returns test set source language or None for multi-language test sets."""
        return self.test_set.source_language

    def _target_language(self):
        """Returns test set target language or None for multi-language test sets."""
        return self.test_set.target_language

    def _team_name(self):
        """Returns team publication name if set, or the original name otherwise."""
        return self.submitted_by.publication_name or self.submitted_by.name

    def _validate_hyp_length(self, raise_exception=True):
        """Checks if the hyp file matches the test set's number of segments."""
        try:
            src_segments = len(list(self.get_src_text()))
            hyp_segments = len(list(self.get_hyp_text()))

            if hyp_segments != src_segments:
                if not raise_exception:
                    return False
                raise ValidationError(
                    f"Submission invalid: hyp length ({hyp_segments}) != src segments ({src_segments})"
                )
            return True
        except (OSError, IOError, ValueError):
            # File doesn't exist yet (during full_clean) or other file access issues
            # We'll validate this later in save() when the file is properly saved
            return True if not raise_exception else None

    def _validate_hyp_file_content(self):
        """Validates the content of the uploaded hyp file during full_clean()."""
        if not self.hyp_file:
            return

        # Validate the number of lines for JSONL format: non-empty or same as source
        if self.file_format == JSONL_FILE:
            try:
                # Check if the file is empty
                if self.hyp_file.size == 0:
                    raise ValidationError("Hypothesis file is empty.")

                # Count source lines - handle both compressed and uncompressed
                src_file_name = self.test_set.src_file.name
                if src_file_name.endswith('.jsonl.gz'):
                    # Handle compressed source file
                    if hasattr(self.test_set.src_file, 'temporary_file_path'):
                        src_file_path = self.test_set.src_file.temporary_file_path()
                    else:
                        # For in-memory files, write to temp file first
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl.gz') as temp_file:
                            self.test_set.src_file.seek(0)
                            temp_file.write(self.test_set.src_file.read())
                            src_file_path = temp_file.name

                    with smart_open(src_file_path, 'rt', encoding='utf-8') as f:
                        src_lines = len(f.readlines())
                else:
                    # Handle uncompressed source file
                    self.test_set.src_file.seek(0)
                    src_lines = len(self.test_set.src_file.read().splitlines())

                # Count hypothesis lines - handle both compressed and uncompressed
                hyp_file_name = self.hyp_file.name
                if hyp_file_name.endswith('.jsonl.gz'):
                    # Handle compressed hypothesis file
                    if hasattr(self.hyp_file, 'temporary_file_path'):
                        hyp_file_path = self.hyp_file.temporary_file_path()
                    else:
                        # For in-memory files, write to temp file first
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl.gz') as temp_file:
                            self.hyp_file.seek(0)
                            temp_file.write(self.hyp_file.read())
                            hyp_file_path = temp_file.name

                    with smart_open(hyp_file_path, 'rt', encoding='utf-8') as f:
                        hyp_lines = len(f.readlines())
                else:
                    # Handle uncompressed hypothesis file
                    self.hyp_file.seek(0)
                    hyp_lines = len(self.hyp_file.read().splitlines())

                if hyp_lines != src_lines:
                    raise ValidationError(
                        f"Submission invalid: hyp JSONL lines ({hyp_lines}) != src JSONL lines ({src_lines})"
                    )
            except (OSError, IOError, ValueError):
                # If we can't read the file, skip validation - other validators will catch issues
                return

        # Validate the number of items for JSON format: non-empty or same as source
        elif self.file_format == JSON_FILE:
            try:
                # Check if the file is empty
                if self.hyp_file.size == 0:
                    raise ValidationError("Hypothesis file is empty.")

                # Count source items - handle both compressed and uncompressed
                src_file_name = self.test_set.src_file.name
                if src_file_name.endswith('.json.gz'):
                    # Handle compressed source file
                    if hasattr(self.test_set.src_file, 'temporary_file_path'):
                        src_file_path = self.test_set.src_file.temporary_file_path()
                    else:
                        # For in-memory files, write to temp file first
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.json.gz') as temp_file:
                            self.test_set.src_file.seek(0)
                            temp_file.write(self.test_set.src_file.read())
                            src_file_path = temp_file.name

                    with smart_open(src_file_path, 'rt', encoding='utf-8') as f:
                        src_data = json.load(f)
                        src_items = len(src_data) if isinstance(src_data, list) else 0
                else:
                    # Handle uncompressed source file
                    self.test_set.src_file.seek(0)
                    content = self.test_set.src_file.read()
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    src_data = json.loads(content)
                    src_items = len(src_data) if isinstance(src_data, list) else 0

                # Count hypothesis items - handle both compressed and uncompressed
                hyp_file_name = self.hyp_file.name
                if hyp_file_name.endswith('.json.gz'):
                    # Handle compressed hypothesis file
                    if hasattr(self.hyp_file, 'temporary_file_path'):
                        hyp_file_path = self.hyp_file.temporary_file_path()
                    else:
                        # For in-memory files, write to temp file first
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.json.gz') as temp_file:
                            self.hyp_file.seek(0)
                            temp_file.write(self.hyp_file.read())
                            hyp_file_path = temp_file.name

                    with smart_open(hyp_file_path, 'rt', encoding='utf-8') as f:
                        hyp_data = json.load(f)
                        hyp_items = len(hyp_data) if isinstance(hyp_data, list) else 0
                else:
                    # Handle uncompressed hypothesis file
                    self.hyp_file.seek(0)
                    content = self.hyp_file.read()
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    hyp_data = json.loads(content)
                    hyp_items = len(hyp_data) if isinstance(hyp_data, list) else 0

                if hyp_items != src_items:
                    raise ValidationError(
                        f"Submission invalid: hyp JSON items ({hyp_items}) != src JSON items ({src_items})"
                    )
            except (OSError, IOError, ValueError, json.JSONDecodeError):
                # If we can't read the file, skip validation - other validators will catch issues
                return


    def full_clean(self, exclude=None, validate_unique=True):
        """Validates submission SGML, XML, JSONL, JSON or text file."""
        hyp_name = str(self.hyp_file.name)

        if self.file_format == SGML_FILE:
            if not hyp_name.endswith('.sgm'):
                _msg = 'SGML file name must end with {0}'.format(hyp_name)
                raise ValidationError(_msg)

        elif self.file_format == XML_FILE:
            if not hyp_name.endswith('.xml'):
                _msg = 'XML file name must end with {0}'.format(hyp_name)
                raise ValidationError(_msg)

        elif self.file_format == JSONL_FILE:
            if not (hyp_name.endswith('.jsonl') or hyp_name.endswith('.jsonl.gz')):
                _msg = 'JSONL file name must end with .jsonl or .jsonl.gz, got {0}'.format(hyp_name)
                raise ValidationError(_msg)

        elif self.file_format == JSON_FILE:
            if not (hyp_name.endswith('.json') or hyp_name.endswith('.json.gz')):
                _msg = 'JSON file name must end with .json or .json.gz, got {0}'.format(hyp_name)
                raise ValidationError(_msg)

        elif self.file_format == TEXT_FILE:
            if not hyp_name.endswith('.txt'):
                _msg = 'Text file name must end with {0}'.format(hyp_name)
                raise ValidationError(_msg)

        # Skip validation if the test set has validation disabled
        if self.test_set and self.test_set.validate:
            # Validate hyp file content directly from the uploaded file
            self._validate_hyp_file_content()

        super().full_clean(
            exclude=exclude, validate_unique=validate_unique
        )

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=DEFAULT_DB_ALIAS,
        update_fields=None,
    ):
        """Compute sacreBLEU score on save()."""
        self.is_valid = True
        super().save(force_insert, force_update, using, update_fields)

        # TODO: validate only if TestSet does not have skip_validation set to False

        # Final validation after file is saved with proper path
        if self.id and self.test_set and self.test_set.validate and not self._validate_hyp_length(raise_exception=False):
            self.is_valid = False
            # Save again to update the is_valid flag
            super().save(force_insert=False, force_update=True, using=using, update_fields=['is_valid'])

        if not self.score and self.id:
            self._compute_score()

    def set_primary(self):
        """Make this the primary submission for user/test set."""
        self.is_primary = True
        self.is_contrastive = False
        self.save()

        other_submissions = Submission.objects.filter(
            submitted_by=self.submitted_by,
            test_set=self.test_set,
            is_contrastive=False,  # Leave current contrastive submission as-is
        )
        for other_submission in other_submissions:
            if other_submission.id != self.id:
                other_submission.is_contrastive = False
                other_submission.is_primary = False
                other_submission.save()

    def set_contrastive(self):
        """Make this the contrastive submission for user/test set."""
        if self.is_primary:
            return

        self.is_contrastive = True
        self.save()

        other_submissions = Submission.objects.filter(
            submitted_by=self.submitted_by,
            test_set=self.test_set,
            is_primary=False,  # Leave current primary submission as-is
        )
        for other_submission in other_submissions:
            if other_submission.id != self.id:
                other_submission.is_contrastive = False
                other_submission.is_primary = False
                other_submission.save()

    @property
    def get_name(self):
        """Make __str__() accessible in admin listings."""
        return str(self)
