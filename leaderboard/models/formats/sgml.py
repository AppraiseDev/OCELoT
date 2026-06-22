"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

SGML format schema and validators.
"""
import lxml.etree as ET
import xmlschema
from django.core.exceptions import ValidationError

from ._xml_safe import safe_xml_parser

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


def validate_sgml_schema(hyp_file):
    """Validates SGML file based on XSD schema."""
    if not hyp_file.name.endswith('.sgm'):
        return  # Skip validation for other format files.

    schema = xmlschema.XMLSchema(SGML_XSD_SCHEMA)

    try:
        # Parse the untrusted upload with a hardened parser first (preventing
        # XXE and entity-expansion attacks), then validate the resulting tree.
        document = ET.parse(hyp_file, parser=safe_xml_parser())
        schema.validate(document)
    except (
        xmlschema.XMLSchemaValidationError,
        ET.XMLSyntaxError,
    ) as error:
        _msg = 'SGML file invalid: {0}'.format(error)
        raise ValidationError(_msg)
