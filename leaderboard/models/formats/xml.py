"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

XML format schema and validators.
"""
import lxml.etree as ET
from django.core.exceptions import ValidationError

from leaderboard.utils import analyze_xml_file

from ._xml_safe import safe_xml_parser

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
        # Parse the untrusted upload with a hardened parser to prevent XXE and
        # entity-expansion (billion laughs) attacks.
        hyp_doc = ET.parse(xml_file, parser=safe_xml_parser())
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
