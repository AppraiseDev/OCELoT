"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
Tests for utils functions.
"""
from pathlib import Path

from .common import TestCase, TESTDATA_DIR, analyze_xml_file, analyze_jsonl_file, process_xml_to_text, process_jsonl_to_text
from leaderboard.utils import detect_jsonl_format


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

    def test_detect_jsonl_format_standard_wmt25(self):
        """Checks if standard WMT25 JSONL format is detected correctly."""
        import io
        
        # Create a file-like object with standard WMT25 format
        jsonl_content = '{"dataset_id": "newssample2021", "src_text": "Hello", "doc_id": "test", "src_lang": "en", "segment_id": "1"}\n'
        jsonl_file = io.BytesIO(jsonl_content.encode('utf-8'))
        jsonl_file.name = 'test.jsonl'
        
        result = detect_jsonl_format(jsonl_file)
        self.assertFalse(result)

    def test_detect_jsonl_format_st_mt_format(self):
        """Checks if ST MT JSONL format is detected correctly."""
        import io
        
        # Create a file-like object with ST MT format
        jsonl_content = '{"dataset_id": "wmtslavicllm2025_de-dsb", "sent_id": "de-dsb-00001", "source": "Source text", "target": "Target text"}\n'
        jsonl_file = io.BytesIO(jsonl_content.encode('utf-8'))
        jsonl_file.name = 'test.jsonl'
        
        result = detect_jsonl_format(jsonl_file)
        self.assertTrue(result)

    def test_detect_jsonl_format_compressed_st_mt(self):
        """Checks if compressed ST MT JSONL format is detected correctly."""
        import io
        import gzip
        
        # Create a compressed file-like object with ST MT format
        jsonl_content = '{"dataset_id": "wmtslavicllm2025_de-dsb", "sent_id": "de-dsb-00001", "source": "Source text", "target": "Target text"}\n'
        
        # Create a temporary file for testing compressed format
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jsonl.gz', delete=False) as tmp:
            with gzip.open(tmp.name, 'wt', encoding='utf-8') as gz_file:
                gz_file.write(jsonl_content)
            
            # Open the compressed file for testing
            with open(tmp.name, 'rb') as f:
                jsonl_file = io.BytesIO(f.read())
                jsonl_file.name = 'test.jsonl.gz'
                
                result = detect_jsonl_format(jsonl_file)
                self.assertTrue(result)
        
        # Clean up
        import os
        os.unlink(tmp.name)

    def test_detect_jsonl_format_empty_file(self):
        """Checks if empty JSONL file is handled correctly."""
        import io
        
        # Create an empty file-like object
        jsonl_file = io.BytesIO(b'')
        jsonl_file.name = 'empty.jsonl'
        
        result = detect_jsonl_format(jsonl_file)
        self.assertFalse(result)

    def test_detect_jsonl_format_invalid_json(self):
        """Checks if invalid JSON in JSONL file is handled correctly."""
        import io
        
        # Create a file-like object with invalid JSON
        jsonl_content = '{"dataset_id": "test", invalid json}\n'
        jsonl_file = io.BytesIO(jsonl_content.encode('utf-8'))
        jsonl_file.name = 'invalid.jsonl'
        
        result = detect_jsonl_format(jsonl_file)
        self.assertFalse(result)


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
