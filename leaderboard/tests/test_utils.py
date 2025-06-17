"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for utils functions.
"""
from pathlib import Path

from .common import TestCase, TESTDATA_DIR, analyze_xml_file, analyze_jsonl_file, process_xml_to_text, process_jsonl_to_text


class UtilsTests(TestCase):
    """Tests for utils."""

    def tearDown(self):
        file_paths = (
            '/xml/sample-hyp.xml.temp.txt',
            '/xml/multi-src-ref.xml.temp.txt',
            '/jsonl/sample-hyp.jsonl.temp.txt',
            '/jsonl/multi-src-ref.jsonl.temp.txt',
        )
        for file_path in file_paths:
            txt_path = Path(TESTDATA_DIR + file_path)
            if txt_path.exists():
                txt_path.unlink()

    #################################################################
    # Tests for analyze_xyz_file functions

    def test_analyze_xml_file_with_testset(self):
        """Checks if source and reference can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/sample-src-ref.xml'
        _, src_langs, ref_langs, translators, _ = analyze_xml_file(
            xml_path
        )

        self.assertSetEqual(src_langs, set(['en']))
        self.assertSetEqual(ref_langs, set(['ha']))
        self.assertSetEqual(translators, set(['A']))

    def test_analyze_xml_file_with_multi_reference_testset(self):
        """Checks if multiple references can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/sample-src-multirefs.xml'
        _, src_langs, ref_langs, translators, _ = analyze_xml_file(
            xml_path
        )

        self.assertSetEqual(src_langs, set(['en']))
        self.assertSetEqual(ref_langs, set(['ha']))
        self.assertSetEqual(translators, set(['A', 'B']))

    def test_analyze_xml_file_with_hypothesis(self):
        """Checks if systems can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/sample-hyp.xml'
        _, src_langs, _, _, systems = analyze_xml_file(xml_path)

        self.assertSetEqual(src_langs, set(['en']))
        self.assertSetEqual(systems, set(['test-team']))

    def test_analyze_xml_file_with_multiple_datasets(self):
        """Checks if multile data set IDs can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/multi-src-ref.xml'
        collections, _, _, _, _ = analyze_xml_file(xml_path)

        self.assertSetEqual(collections, set(['A', 'B', 'C']))

    def test_analyze_jsonl_file_with_testset(self):
        """Checks if source and reference can be found in JSONL format."""
        jsonl_path = TESTDATA_DIR + '/jsonl/sample-src-ref.jsonl'
        output = analyze_jsonl_file(jsonl_path)
        src_langs = output.get('src_langs')
        ref_langs = output.get('ref_langs')
        translators = output.get('translators')

        self.assertSetEqual(src_langs, set(['en']))
        self.assertSetEqual(ref_langs, set(['ha']))
        self.assertSetEqual(translators, set(['A']))

    def test_analyze_jsonl_file_with_multi_reference_testset(self):
        """Checks if multiple references can be found in JSONL format."""
        jsonl_path = TESTDATA_DIR + '/jsonl/sample-src-multirefs.jsonl'
        output = analyze_jsonl_file(jsonl_path)
        src_langs = output.get('src_langs')
        ref_langs = output.get('ref_langs')
        translators = output.get('translators')

        self.assertSetEqual(src_langs, set(['en']))
        self.assertSetEqual(ref_langs, set(['ha']))
        self.assertSetEqual(translators, set(['A', 'B']))

    def test_analyze_jsonl_file_with_hypothesis(self):
        """Checks if systems can be found in JSONL format."""
        jsonl_path = TESTDATA_DIR + '/jsonl/sample-hyp.jsonl'
        output = analyze_jsonl_file(jsonl_path)
        src_langs = output.get('src_langs')
        systems = output.get('systems')

        self.assertSetEqual(src_langs, set(['en']))
        self.assertSetEqual(systems, set(['test-team']))

    def test_analyze_jsonl_file_with_multiple_languages(self):
        """Checks if multiple source languages can be found in JSONL format."""
        jsonl_path = TESTDATA_DIR + '/jsonl/wmt-hyp-a.jsonl'
        output = analyze_jsonl_file(jsonl_path)
        src_langs = output.get('src_langs')
        ref_langs = output.get('ref_langs')
        tgt_langs = output.get('tgt_langs')

        self.assertSetEqual(src_langs, set(['Czech', 'English']))
        self.assertSetEqual(ref_langs, set([]))
        expected_langs = [
            'Ukrainian',
            'Turkish',
            'Lithuanian',
            'Chinese (Simplified)',
            'Serbian (Cyrillics)',
            'Arabic (Egyptian)',
            'Estonian',
            'Czech',
            'German',
            'Maasai',
            'Bengali',
            'Serbian (Latin script)',
            'Indonesian',
        ]
        self.assertSetEqual(tgt_langs, set(expected_langs))


    #################################################################
    # Tests for process_xyz_to_text functions

    def test_process_xml_to_text_with_hypothesis(self):
        """Checks if system segments can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/sample-hyp.xml'
        txt_path = xml_path + '.temp.txt'
        process_xml_to_text(xml_path, txt_path, system='test-team')

        txt_file = Path(txt_path)
        self.assertTrue(txt_file.exists())
        self.assertTrue(txt_file.stat().st_size > 0)

    def test_process_xml_to_text_from_one_collection(self):
        """Checks if source segments from a collection can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/multi-src-ref.xml'

        txt_path = xml_path + '.temp.txt'
        process_xml_to_text(
            xml_path, txt_path, source=True, collection='B'
        )
        txt_file = Path(txt_path)
        self.assertTrue(txt_file.exists())
        with open(txt_file, 'r', encoding='utf8') as content:
            self.assertTrue(len(content.readlines()) == 12)

    def test_process_xml_to_text_from_all_collections(self):
        """Checks if reference segments from all collections can be found in XML format."""
        xml_path = TESTDATA_DIR + '/xml/multi-src-ref.xml'

        txt_path = xml_path + '.temp.txt'
        process_xml_to_text(
            xml_path, txt_path, reference=True, collection=None
        )
        txt_file = Path(txt_path)
        self.assertTrue(txt_file.exists())
        with open(txt_file, 'r', encoding='utf8') as content:
            self.assertTrue(len(content.readlines()) == 56)

    def test_process_jsonl_to_text_with_hypothesis(self):
        """Checks if system segments can be found in JSONL format."""
        jsonl_path = TESTDATA_DIR + '/jsonl/sample-hyp.jsonl'
        txt_path = jsonl_path + '.temp.txt'
        process_jsonl_to_text(jsonl_path, txt_path, system='test-team')

        txt_file = Path(txt_path)
        self.assertTrue(txt_file.exists())
        self.assertTrue(txt_file.stat().st_size > 0)

    def test_process_jsonl_to_text_from_one_collection(self):
        """Checks if source segments from a collection can be found in JSONL format."""
        jsonl_path = TESTDATA_DIR + '/jsonl/multi-src-ref.jsonl'

        txt_path = jsonl_path + '.temp.txt'
        process_jsonl_to_text(
            jsonl_path, txt_path, source=True, collection='B'
        )
        txt_file = Path(txt_path)
        self.assertTrue(txt_file.exists())
        with open(txt_file, 'r', encoding='utf8') as content:
            self.assertTrue(len(content.readlines()) == 12)
