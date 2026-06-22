"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Regression tests for XXE / entity-expansion hardening of XML and SGML parsing.
"""
import os
import tempfile

import lxml.etree as ET
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from leaderboard.models import Submission
from leaderboard.models import ValidationError
from leaderboard.models import validate_sgml_schema
from leaderboard.models import validate_xml_schema
from leaderboard.models.formats._xml_safe import safe_xml_parser


# A billion-laughs (exponential entity expansion) payload. The entities are
# declared in an internal DTD; a hardened parser must not expand them.
BILLION_LAUGHS = """<?xml version="1.0"?>
<!DOCTYPE dataset [
  <!ENTITY lol "lol">
  <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<dataset id="x"><seg id="1">&lol4;</seg></dataset>
"""


def _xxe_payload(secret_path):
    """Build an XML doc that, if entities were resolved, would leak a file."""
    return (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE dataset [\n'
        '  <!ENTITY xxe SYSTEM "file://{0}">\n'
        ']>\n'
        '<dataset id="x"><seg id="1">&xxe;</seg></dataset>\n'
    ).format(secret_path)


class SafeXmlParserTests(SimpleTestCase):
    """Tests the hardened lxml parser configuration directly."""

    def test_external_entity_is_not_resolved(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        ) as secret:
            secret.write('TOP_SECRET_VALUE')
            secret_path = secret.name
        try:
            payload = _xxe_payload(secret_path).encode('utf-8')
            # A hardened parser rejects the undefined/external entity outright;
            # either way the secret must never be read into the tree.
            try:
                tree = ET.fromstring(payload, parser=safe_xml_parser())
            except ET.XMLSyntaxError:
                return  # rejected before any entity resolution - safe
            self.assertNotIn('TOP_SECRET_VALUE', ET.tostring(tree, encoding='unicode'))
        finally:
            os.unlink(secret_path)

    def test_billion_laughs_is_not_expanded(self):
        try:
            tree = ET.fromstring(BILLION_LAUGHS.encode('utf-8'), parser=safe_xml_parser())
        except ET.XMLSyntaxError:
            return  # rejected outright - safe
        # If it parsed, the entities must not have been expanded into 10k chars.
        self.assertLess(len(ET.tostring(tree, encoding='unicode')), 1000)

    def test_benign_xml_still_parses(self):
        tree = ET.fromstring(
            b'<dataset id="x"><seg id="1">hello</seg></dataset>',
            parser=safe_xml_parser(),
        )
        self.assertEqual(tree.get('id'), 'x')


class XmlValidatorHardeningTests(SimpleTestCase):
    """End-to-end hardening tests via the XML/SGML schema validators."""

    def test_validate_xml_schema_rejects_billion_laughs(self):
        upload = SimpleUploadedFile('evil.xml', BILLION_LAUGHS.encode('utf-8'))
        with self.assertRaises(ValidationError):
            validate_xml_schema(upload)

    def test_validate_xml_schema_rejects_xxe(self):
        upload = SimpleUploadedFile('evil.xml', _xxe_payload('/etc/hostname').encode('utf-8'))
        with self.assertRaises(ValidationError):
            validate_xml_schema(upload)

    def test_validate_sgml_schema_rejects_billion_laughs(self):
        upload = SimpleUploadedFile('evil.sgm', BILLION_LAUGHS.encode('utf-8'))
        with self.assertRaises(ValidationError):
            validate_sgml_schema(upload)

    def test_validate_sgml_schema_rejects_xxe(self):
        upload = SimpleUploadedFile('evil.sgm', _xxe_payload('/etc/hostname').encode('utf-8'))
        with self.assertRaises(ValidationError):
            validate_sgml_schema(upload)


class SgmlDocidParsingHardeningTests(SimpleTestCase):
    """Tests that Submission's SGML helpers do not leak files via XXE."""

    def test_parse_sgml_safely_does_not_leak_external_entity(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        ) as secret:
            secret.write('TOP_SECRET_VALUE')
            secret_path = secret.name

        sgm_fd, sgm_path = tempfile.mkstemp(suffix='.sgm')
        with os.fdopen(sgm_fd, 'w') as handle:
            handle.write(_xxe_payload(secret_path))

        try:
            try:
                soup = Submission._parse_sgml_safely(sgm_path)
            except ET.XMLSyntaxError:
                return  # rejected outright - safe
            self.assertNotIn('TOP_SECRET_VALUE', str(soup))
        finally:
            os.unlink(secret_path)
            os.unlink(sgm_path)
