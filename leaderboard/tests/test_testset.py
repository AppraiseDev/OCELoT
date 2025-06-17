"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
TestSet model tests.
"""
import os
from pathlib import Path

from .common import (
    TestCase, TESTDATA_DIR, TestSet, SGML_FILE, XML_FILE, JSONL_FILE
)


class TestSetTests(TestCase):
    """Tests TestSet model."""

    def test_create_test_set_with_sgml_files(self):
        """Checks that a test set can be created from SGML files."""

        TestSet.objects.create(
            name='TestSetA',
            file_format=SGML_FILE,
            src_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-src.en.sgm'
            ),
            ref_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-ref.de.sgm'
            ),
        )

        tst = TestSet.objects.get(name='TestSetA')
        self.assertEqual(tst.name, 'TestSetA')
        self.assertTrue(tst.src_file.name.endswith('.sgm'))
        self.assertTrue(tst.ref_file.name.endswith('.sgm'))
        self.assertTrue(tst.has_references())

    def test_create_test_set_with_text_files(self):
        """Checks that a test set can be created from text files."""
        TestSet.objects.create(
            name='TestSetB',
            file_format=SGML_FILE,
            src_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-src.en.txt'
            ),
            ref_file=os.path.join(
                TESTDATA_DIR, 'newstest2019-ende-ref.de.txt'
            ),
        )

        tst = TestSet.objects.get(name='TestSetB')
        self.assertEqual(tst.name, 'TestSetB')
        self.assertTrue(tst.src_file.name.endswith('.txt'))
        self.assertTrue(tst.ref_file.name.endswith('.txt'))
        self.assertTrue(tst.has_references())

    def test_create_test_set_with_xml_files(self):
        """Checks that a test set can be created from XML files."""

        TestSet.objects.create(
            name='TestSetC',
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/sample-src.xml'),
            ref_file=os.path.join(TESTDATA_DIR, 'xml/sample-src-ref.xml'),
        )

        tst = TestSet.objects.get(name='TestSetC')
        self.assertEqual(tst.name, 'TestSetC')
        self.assertTrue(tst.src_file.name.endswith('.xml'))
        self.assertTrue(tst.ref_file.name.endswith('.xml'))
        self.assertTrue(tst.has_references())

        # Check if text files has been created and are non empty
        src_txt_file = Path(tst.src_file.name.replace('.xml', '.txt'))
        ref_txt_file = Path(tst.ref_file.name.replace('.xml', '.txt'))
        self.assertTrue(src_txt_file.exists())
        self.assertTrue(ref_txt_file.exists())
        self.assertTrue(src_txt_file.stat().st_size > 0)
        self.assertTrue(ref_txt_file.stat().st_size > 0)

        # Clean up created files
        src_txt_file.unlink()
        ref_txt_file.unlink()

    def test_create_test_set_with_jsonl_files(self):
        """Checks that a test set can be created from JSONL files."""

        TestSet.objects.create(
            name='TestSetJsonl',
            file_format=JSONL_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'jsonl/sample-src.jsonl'),
            ref_file=os.path.join(TESTDATA_DIR, 'jsonl/sample-src-ref.jsonl'),
        )

        tst = TestSet.objects.get(name='TestSetJsonl')
        self.assertEqual(tst.name, 'TestSetJsonl')
        self.assertTrue(tst.src_file.name.endswith('.jsonl'))
        self.assertTrue(tst.ref_file.name.endswith('.jsonl'))
        self.assertTrue(tst.has_references())

        # Check if text files has been created and are non empty
        src_txt_file = Path(tst.src_file.name.replace('.jsonl', '.txt'))
        ref_txt_file = Path(tst.ref_file.name.replace('.jsonl', '.txt'))
        self.assertTrue(src_txt_file.exists())
        self.assertTrue(ref_txt_file.exists())
        self.assertTrue(src_txt_file.stat().st_size > 0)
        self.assertTrue(ref_txt_file.stat().st_size > 0)

        # Clean up created files
        src_txt_file.unlink()
        ref_txt_file.unlink()

    def test_create_test_set_with_collections(self):
        """Checks that a test set can be created from a single collection."""

        TestSet.objects.create(
            name='TestSetD',
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/multi-src-ref.xml'),
            ref_file=os.path.join(TESTDATA_DIR, 'xml/multi-src-ref.xml'),
            collection='B',
        )

        tst = TestSet.objects.get(name='TestSetD')
        self.assertEqual(tst.name, 'TestSetD')
        self.assertTrue(tst.src_file.name.endswith('.xml'))
        self.assertTrue(tst.ref_file.name.endswith('.xml'))
        self.assertEqual(tst.collection, 'B')
        self.assertTrue(tst.has_references())

        # Check if text files has been created and have only 12 segments from
        # the collection 'B'
        src_txt_file = Path(tst.src_file.name.replace('.xml', '.txt'))
        ref_txt_file = Path(tst.ref_file.name.replace('.xml', '.txt'))
        self.assertTrue(src_txt_file.exists())
        self.assertTrue(ref_txt_file.exists())
        self.assertTrue(src_txt_file.stat().st_size > 0)
        self.assertTrue(ref_txt_file.stat().st_size > 0)
        with open(src_txt_file, 'r', encoding='utf8') as cnt:
            self.assertTrue(len(cnt.readlines()) == 12)
        with open(ref_txt_file, 'r', encoding='utf8') as cnt:
            self.assertTrue(len(cnt.readlines()) == 12)

        # Clean up created files
        if src_txt_file.exists():
            src_txt_file.unlink()
        if ref_txt_file.exists():
            ref_txt_file.unlink()

    def test_create_test_set_without_reference(self):
        """Checks that a test set can be created without a reference."""

        TestSet.objects.create(
            name='TestSetE',
            file_format=XML_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'xml/sample-src.xml'),
        )

        tst = TestSet.objects.get(name='TestSetE')
        self.assertEqual(tst.name, 'TestSetE')
        self.assertTrue(tst.src_file.name.endswith('.xml'))
        self.assertFalse(tst.ref_file)
        self.assertFalse(tst.has_references())

        # Check if text files has been created
        src_txt_file = Path(tst.src_file.name.replace('.xml', '.txt'))
        self.assertTrue(src_txt_file.exists())
        self.assertTrue(src_txt_file.stat().st_size > 0)

        # Clean up created files
        if src_txt_file.exists():
            src_txt_file.unlink()
    
    def test_create_test_set_from_jsonl_without_reference(self):
        """Checks that a test set can be created from JSONL without a reference."""

        TestSet.objects.create(
            name='TestSetJsonlNoRef',
            file_format=JSONL_FILE,
            src_file=os.path.join(TESTDATA_DIR, 'jsonl/sample-src.jsonl'),
        )

        tst = TestSet.objects.get(name='TestSetJsonlNoRef')
        self.assertEqual(tst.name, 'TestSetJsonlNoRef')
        self.assertTrue(tst.src_file.name.endswith('.jsonl'))
        self.assertFalse(tst.ref_file)
        self.assertFalse(tst.has_references())

        # Check if text files has been created
        src_txt_file = Path(tst.src_file.name.replace('.jsonl', '.txt'))
        self.assertTrue(src_txt_file.exists())
        self.assertTrue(src_txt_file.stat().st_size > 0)

        # Clean up created files
        if src_txt_file.exists():
            src_txt_file.unlink()
