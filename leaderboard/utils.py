"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import os.path
import re
from typing import Optional
import json
import tempfile

import lxml.etree as ET
from sacrebleu.utils import smart_open

MISSING_TRANSLATION_MESSAGE = "NO TRANSLATION AVAILABLE"

JSONL_WMT_GENMT_FORMAT = 'WMT25'  # WMT 2025 General MT format
JSONL_WMT_ST_MT_FORMAT = 'WMT-ST-MT'  # WMT 2025 Slavic Translation MT format
JSONL_WMT_ST_QA_FORMAT = 'WMT-ST-QA'  # WMT 2025 Slavic Translation QA format

# WMT 2026 low-resource LLM task formats. One file per task; a single file may
# contain several dataset_id values (e.g. all MT language pairs). The task is
# encoded in the dataset_id as wmt2026_lrllm_test_{task}_{lang|pair}.
JSONL_WMT26_LR_PREFIX = 'wmt2026_lrllm_test_'
JSONL_WMT26_LR_MT_FORMAT = 'WMT26-LR-MT'  # Machine Translation (BLEU + chrF++)
JSONL_WMT26_LR_QA_FORMAT = 'WMT26-LR-QA'  # Question Answering (accuracy)
JSONL_WMT26_LR_SC_FORMAT = 'WMT26-LR-SC'  # Spell Checking (two-output accuracy)
JSONL_WMT26_LR_GC_FORMAT = 'WMT26-LR-GC'  # Grammar Checking (two-output accuracy)
JSONL_WMT26_LR_MR_FORMAT = 'WMT26-LR-MR'  # Maths Reasoning (accuracy)

# Maps the task token in dataset_id to the corresponding format constant.
_WMT26_LR_TASK_FORMATS = {
    'mt': JSONL_WMT26_LR_MT_FORMAT,
    'qa': JSONL_WMT26_LR_QA_FORMAT,
    'sc': JSONL_WMT26_LR_SC_FORMAT,
    'gc': JSONL_WMT26_LR_GC_FORMAT,
    'mr': JSONL_WMT26_LR_MR_FORMAT,
}

# All WMT26 low-resource formats, and the subset scored by exact-match accuracy.
JSONL_WMT26_LR_FORMATS = frozenset(_WMT26_LR_TASK_FORMATS.values())
JSONL_WMT26_LR_ACCURACY_FORMATS = frozenset({
    JSONL_WMT26_LR_QA_FORMAT,
    JSONL_WMT26_LR_SC_FORMAT,
    JSONL_WMT26_LR_GC_FORMAT,
    JSONL_WMT26_LR_MR_FORMAT,
})

# Reference (gold) and prediction (submission) fields per WMT26 low-resource
# format, used to detect whether a JSONL file provides references or system
# outputs.
_WMT26_LR_REF_FIELDS = {
    JSONL_WMT26_LR_MT_FORMAT: ('target',),
    JSONL_WMT26_LR_QA_FORMAT: ('correct_answer_num',),
    JSONL_WMT26_LR_MR_FORMAT: ('answer',),
    JSONL_WMT26_LR_SC_FORMAT: ('incorrect_word', 'correct_word'),
    JSONL_WMT26_LR_GC_FORMAT: ('incorrect_word', 'correct_word'),
}
_WMT26_LR_PRED_FIELDS = {
    JSONL_WMT26_LR_MT_FORMAT: ('pred',),
    JSONL_WMT26_LR_QA_FORMAT: ('pred',),
    JSONL_WMT26_LR_MR_FORMAT: ('pred',),
    JSONL_WMT26_LR_SC_FORMAT: ('pred_incorrect', 'pred_corrected'),
    JSONL_WMT26_LR_GC_FORMAT: ('pred_incorrect', 'pred_corrected'),
}


def detect_wmt26_lr_format(dataset_id):
    """Return the WMT26 low-resource format for a dataset_id, or None.

    The task is the first token after the wmt2026_lrllm_test_ prefix, e.g.
    'wmt2026_lrllm_test_qa_mmlu_ukr' -> QA and
    'wmt2026_lrllm_test_mt_cs-ukr' -> MT.
    """
    if not dataset_id or not dataset_id.startswith(JSONL_WMT26_LR_PREFIX):
        return None
    task = dataset_id[len(JSONL_WMT26_LR_PREFIX):].split('_', 1)[0]
    return _WMT26_LR_TASK_FORMATS.get(task)


def detect_jsonl_format(json_file_or_path, format=None):
    """
    Detect the format of a JSONL file.
    """

    def _check_format_in_line(line_text):
        if not line_text:
            return None
        
        try:
            obj = json.loads(line_text)
        except json.JSONDecodeError:
            return None

        _format = None
        _wmt26_lr = detect_wmt26_lr_format(obj.get('dataset_id'))
        if _wmt26_lr is not None:
            _format = _wmt26_lr
        elif 'dataset_id' in obj and obj.get('dataset_id').startswith('wmtslavicllm2025_qa'):
            _format = JSONL_WMT_ST_QA_FORMAT
        elif 'dataset_id' in obj and obj.get('dataset_id').startswith('wmtslavicllm2025'):
            _format = JSONL_WMT_ST_MT_FORMAT
        elif 'doc_id' in obj and 'tgt_lang' in obj:
            # General MT format (WMT25 and WMT26). WMT26 blindsets drop
            # 'dataset_id' and use 'source_doc' instead of 'src_text'.
            _format = JSONL_WMT_GENMT_FORMAT
        else:
            _format = None

        if format is not None:
            return _format == format
        return _format
    
    # Handle file path (string)
    if isinstance(json_file_or_path, str):
        with smart_open(json_file_or_path, 'rt', encoding='utf-8') as f:
            first_line = f.readline().strip()
            return _check_format_in_line(first_line)
    
    # Handle file object
    json_file = json_file_or_path
    json_file.seek(0)
    
    try:
        # Handle compressed files
        if json_file.name.endswith('.jsonl.gz'):
            if hasattr(json_file, 'temporary_file_path'):
                file_path = json_file.temporary_file_path()
            else:
                # For in-memory files, write to temp file first
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl.gz') as temp_file:
                    json_file.seek(0)
                    temp_file.write(json_file.read())
                    file_path = temp_file.name

            with smart_open(file_path, 'rt', encoding='utf-8') as f:
                first_line = f.readline().strip()
                return _check_format_in_line(first_line)
        else:
            # Handle uncompressed files
            for line in json_file:
                text = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
                if text:
                    return _check_format_in_line(text)
    finally:
        json_file.seek(0)
    
    return False if format else None


def analyze_xml_file(xml_path):
    """
    Return all collection names, source languages, reference languages,
    translators, and systems found in the XML file. Code extracted from
    https://github.com/wmt-conference/wmt-format-tools/blob/main/wmtformat/unwrap.py
    """
    collections, src_langs, ref_langs, translators, systems = (
        set(),
        set(),
        set(),
        set(),
        set(),
    )
    tree = ET.parse(xml_path)

    for collection in tree.getroot().findall(".//collection"):
        collections.add(collection.get("id"))

    for src_doc in tree.getroot().findall(".//src"):
        src_langs.add(src_doc.get("lang"))

    for ref_doc in tree.getroot().findall(".//ref"):
        ref_langs.add(ref_doc.get("lang"))
        translator = ref_doc.get("translator")
        if translator:
            translators.add(translator)

    for hyp_doc in tree.getroot().findall(".//hyp"):
        # hyp_langs.add(hyp_doc.get("lang"))  # Not used in the XML format?
        system = hyp_doc.get("system")
        if system:
            systems.add(system)

    return collections, src_langs, ref_langs, translators, systems


def analyze_jsonl_file(jsonl_path):
    """
    Return all collection IDs, source languages, reference languages,
    translators and system names found in a JSONL file.
    """
    output = {
        "collections": set(),
        "src_langs": set(),
        "tgt_langs": set(),
        "ref_langs": set(),
        "translators": set(),
        "hyp_langs": set(),
        "systems": set(),
    }

    jsonl_format = detect_jsonl_format(jsonl_path)
    
    # Read the JSONL file and extract the required information
    with smart_open(jsonl_path, 'rt', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            
            if jsonl_format == JSONL_WMT_ST_MT_FORMAT:
                # Handle ST MT format
                # if "target" is present, add "True" as translator
                if 'target' in obj:
                    output['translators'].add('True')
                # if "pred" is present, add "True" as system
                if 'pred' in obj:
                    output['systems'].add('True')
            
            elif jsonl_format == JSONL_WMT_ST_QA_FORMAT:
                # Handle ST QA format
                # if "correct_answer" is present, add "True" as translator
                if 'correct_answer' in obj:
                    output['translators'].add('True')
                # if "pred" is present, add "True" as system
                if 'pred' in obj:
                    output['systems'].add('True')

            elif jsonl_format in JSONL_WMT26_LR_FORMATS:
                # WMT26 low-resource tasks: reference field presence marks a
                # gold test set ('True' translator); prediction field presence
                # marks a system submission ('True' system).
                if any(f in obj for f in _WMT26_LR_REF_FIELDS[jsonl_format]):
                    output['translators'].add('True')
                if any(f in obj for f in _WMT26_LR_PRED_FIELDS[jsonl_format]):
                    output['systems'].add('True')

            else:
                # Handle standard WMT25 format
                # collection_id
                cid = obj.get('collection_id')
                if cid:
                    output['collections'].add(cid)
                # src_lang
                sl = obj.get('src_lang')
                if sl:
                    output['src_langs'].add(sl)
                # tgt_lang
                tl = obj.get('tgt_lang')
                if tl:
                    output['tgt_langs'].add(tl)
                # references
                for ref in obj.get('refs', []):
                    tl = ref.get('tgt_lang')
                    tr = ref.get('translator')
                    if tl:
                        output['ref_langs'].add(tl)
                    if tr:
                        output['translators'].add(tr)
                # hypotheses
                for hyp in obj.get('hyps', obj.get('hypothesis', [])):
                    if isinstance(hyp, str):
                        # If the hypothesis is a string, it might be an old format
                        # without 'system' or 'tgt_lang' keys.
                        continue
                    sysn = hyp.get('system', None)
                    hl = hyp.get('tgt_lang', None)
                    if hl:
                        output['hyp_langs'].add(hl)
                    if sysn:
                        output['systems'].add(sysn)
                if 'system' in obj:
                    # If the JSONL file has a 'system' key, add it to systems
                    sysn = obj['system']
                    if sysn:
                        output['systems'].add(sysn)
    return output


def analyze_json_file(json_path):
    """
    Return all task IDs, systems, and other metadata found in a JSON file.
    JSON files contain arrays of objects with taskid, prompt, and answer fields.
    """
    output = {
        "taskids": set(),
        "systems": set(),
        "has_prompts": False,
        "has_answers": False,
    }
    
    # Read the JSON file and extract the required information
    with smart_open(json_path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
        
    if not isinstance(data, list):
        return output
        
    for obj in data:
        if not isinstance(obj, dict):
            continue
            
        # taskid
        taskid = obj.get('taskid')
        if taskid:
            output['taskids'].add(taskid)
            
        # Check for prompts and answers
        if obj.get('prompt'):
            output['has_prompts'] = True
        if obj.get('answer'):
            output['has_answers'] = True
            
        # System information (if available)
        system = obj.get('system')
        if system:
            output['systems'].add(system)
            
    return output


# Taken from sacrebleu which removed this with v2.2
#
# https://github.com/mjpost/sacrebleu/blob/65a8a9eeccd8c0c7875e875e12edf10db33ab0ba/sacrebleu/utils.py#L277
def process_to_text(rawfile, txtfile, field: Optional[int] = None):
    """Processes raw files to plain text files. Can handle SGML, XML, TSV files, and plain text.
    Called after downloading datasets.
    :param rawfile: the input file (possibly SGML)
    :param txtfile: the plaintext file
    :param field: For TSV files, which field to extract.
    """

    def _clean(s):
        """
        Removes trailing and leading spaces and collapses multiple consecutive internal spaces to a single one.
        :param s: The string.
        :return: A cleaned-up string.
        """
        return re.sub(r'\s+', ' ', s.strip())

    if not os.path.exists(txtfile) or os.path.getsize(txtfile) == 0:
        if rawfile.endswith('.sgm') or rawfile.endswith('.sgml'):
            with smart_open(rawfile) as fin, smart_open(
                txtfile, 'wt'
            ) as fout:
                for line in fin:
                    if line.startswith('<seg '):
                        print(
                            _clean(
                                re.sub(
                                    r'<seg.*?>(.*)</seg>.*?', '\\1', line
                                )
                            ),
                            file=fout,
                        )
        # IWSLT
        elif rawfile.endswith('.xml'):
            with smart_open(rawfile) as fin, smart_open(
                txtfile, 'wt'
            ) as fout:
                for line in fin:
                    if line.startswith('<seg '):
                        print(
                            _clean(
                                re.sub(
                                    r'<seg.*?>(.*)</seg>.*?', '\\1', line
                                )
                            ),
                            file=fout,
                        )
        # MTNT
        elif rawfile.endswith('.tsv'):
            with smart_open(rawfile) as fin, smart_open(
                txtfile, 'wt'
            ) as fout:
                for line in fin:
                    print(line.rstrip().split('\t')[field], file=fout)
        # PLAIN TEXT
        else:
            with smart_open(rawfile) as fin, smart_open(
                txtfile, 'wt'
            ) as fout:
                for line in fin:
                    print(line.rstrip(), file=fout)


def process_xml_to_text(
    xml_path,
    txt_path,
    source=None,
    reference=None,
    system=None,
    collection=None,
):
    """
    Extract source, reference(s) or system texts from the XML file.
    Segments from test suites are ignored.
    Multiple references are not supported.
    """

    if [source, reference, system].count(None) != 2:
        raise ValueError(
            f'Exactly one of source, reference or system must be provided, but got: '
            f'source={source}, reference={reference}, system={system}'
        )

    tree = ET.parse(xml_path)
    src_sents, ref_sents = [], []
    out_sents = []

    root = tree.getroot()
    if collection:  # Restrict to the given collection if requested
        root = root.find(f".//collection[@id='{collection}']")
        if root is None:
            # Create an empty hypothesis file as this case is catched later
            with open(txt_path, 'w') as txt_file:
                pass
            return False

    for doc in root.findall(".//doc"):
        if 'testsuite' in doc.attrib:  # Skip testsuites
            continue

        src_sents = {
            int(seg.get("id")): seg.text
            for seg in doc.findall(".//src//seg")
        }

        if reference:
            ref_docs = doc.findall(".//ref")
            trans_to_ref = {ref.get("translator"): ref for ref in ref_docs}
            ref_doc = trans_to_ref.get(reference, None)
            ref_sents = (
                {
                    int(seg.get("id")): seg.text
                    for seg in ref_doc.findall(".//seg")
                }
                if ref_doc is not None
                else {}
            )

        if system:
            hyp_docs = doc.findall(".//hyp")
            sys_to_hyp = {hyp.get("system"): hyp for hyp in hyp_docs}
            hyp_doc = sys_to_hyp.get(system, None)
            hyp_sents = (
                {
                    int(seg.get("id")): seg.text
                    for seg in hyp_doc.findall(".//seg")
                }
                if hyp_doc is not None
                else {}
            )

        for seg_id in sorted(src_sents.keys()):
            if source:
                out_sents.append(src_sents[seg_id])
            elif reference:
                ref_sent = ref_sents.get(
                    seg_id, MISSING_TRANSLATION_MESSAGE
                )
                out_sents.append(ref_sent)
            elif system:
                hyp_sent = hyp_sents.get(
                    seg_id, MISSING_TRANSLATION_MESSAGE
                )
                out_sents.append(hyp_sent)

    with open(txt_path, 'w') as txt_file:
        for sent in out_sents:
            txt_file.write("{}\n".format(sent))
    return True


def process_jsonl_to_text(
    jsonl_path,
    txt_path,
    source=None,
    reference=None,
    system=None,
    collection=None,
):
    """
    Extract source, reference(s) or system texts from a JSONL file.
    Segments from other collections are ignored if `collection` is given.
    Multiple references are not supported.
    If system is a string, it will be used to filter hypotheses.
    If system is True, the first system found in the JSONL file will be used.
    """
    # Must specify exactly one of source, reference or system
    if [source, reference, system].count(None) != 2:
        raise ValueError(
            f'Exactly one of source, reference or system must be provided, but got: '
            f'source={source}, reference={reference}, system={system}'
        )

    # First, detect format by checking the first line
    jsonl_format = detect_jsonl_format(jsonl_path)

    # Read and collect JSONL entries
    entries = []
    with smart_open(jsonl_path, 'rt', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            
            if jsonl_format == JSONL_WMT_ST_MT_FORMAT:
                # Use sent_id instead of segment_id for WMT ST MT format
                sid = obj.get('sent_id', None)
            elif jsonl_format == JSONL_WMT_ST_QA_FORMAT:
                # Use sent_id instead of segment_id for WMT ST QA format
                sid = obj.get('question_id', None)
            elif jsonl_format in JSONL_WMT26_LR_FORMATS:
                # Preserve file order; the id field varies by task.
                sid = obj.get('sent_id') or obj.get('question_id') or obj.get('id')
            else:
                # For standard WMT25 format
                # Filter by collection if requested
                if collection and obj.get('collection_id') != collection:
                    continue
                # Skip if collection_id is "testsuites"
                if obj.get('collection_id') == 'testsuites':
                    continue
                sid = obj.get('segment_id')
            
            try:
                sid = int(sid)
            except Exception:
                pass
            entries.append((sid, obj))

    # If no entries matched, write empty file and bail
    if not entries:
        with smart_open(txt_path, 'wt', encoding='utf-8'):
            pass
        return False

    # Build output sentences
    out_sents = []
    for _, obj in entries:
        if jsonl_format == JSONL_WMT_ST_MT_FORMAT:
            # Handle ST MT format
            if source:
                sent = obj.get('source', MISSING_TRANSLATION_MESSAGE)
            elif reference:
                sent = obj.get('target', MISSING_TRANSLATION_MESSAGE)
            else:  # system
                sent = obj.get('pred', MISSING_TRANSLATION_MESSAGE)
            sent = sent.replace('\n', '\\n').replace('\r', '\\r')
        
        elif jsonl_format == JSONL_WMT_ST_QA_FORMAT:
            # Handle ST QA format
            if source:
                sent = str(obj.get('question_id', "")) + ": " + obj.get('question', MISSING_TRANSLATION_MESSAGE)
            elif reference:
                sent = str(obj.get('correct_answer', MISSING_TRANSLATION_MESSAGE))
            else:  # system
                sent = str(obj.get('pred', MISSING_TRANSLATION_MESSAGE))
            sent = sent.replace('\n', '\\n').replace('\r', '\\r')

        elif jsonl_format == JSONL_WMT26_LR_MT_FORMAT:
            # Low-resource MT: source/target/pred plain text.
            if source:
                sent = obj.get('source', MISSING_TRANSLATION_MESSAGE)
            elif reference:
                sent = obj.get('target', MISSING_TRANSLATION_MESSAGE)
            else:  # system
                sent = obj.get('pred', MISSING_TRANSLATION_MESSAGE)
            sent = str(sent).replace('\n', '\\n').replace('\r', '\\r')

        elif jsonl_format in (JSONL_WMT26_LR_QA_FORMAT, JSONL_WMT26_LR_MR_FORMAT):
            # QA/Maths Reasoning: single answer scored by exact match.
            if source:
                sent = obj.get('question', MISSING_TRANSLATION_MESSAGE)
            elif reference:
                ref_field = ('correct_answer_num'
                             if jsonl_format == JSONL_WMT26_LR_QA_FORMAT
                             else 'answer')
                sent = str(obj.get(ref_field, MISSING_TRANSLATION_MESSAGE))
            else:  # system
                sent = str(obj.get('pred', MISSING_TRANSLATION_MESSAGE))
            sent = str(sent).replace('\n', '\\n').replace('\r', '\\r')

        elif jsonl_format in (JSONL_WMT26_LR_SC_FORMAT, JSONL_WMT26_LR_GC_FORMAT):
            # Spell/Grammar checking: two outputs joined with a tab so a line is
            # correct only when both fields match (joint-pair accuracy).
            if source:
                sent = obj.get('input_sentence', MISSING_TRANSLATION_MESSAGE)
            elif reference:
                sent = '{0}\t{1}'.format(
                    obj.get('incorrect_word', MISSING_TRANSLATION_MESSAGE),
                    obj.get('correct_word', MISSING_TRANSLATION_MESSAGE),
                )
            else:  # system
                sent = '{0}\t{1}'.format(
                    obj.get('pred_incorrect', MISSING_TRANSLATION_MESSAGE),
                    obj.get('pred_corrected', MISSING_TRANSLATION_MESSAGE),
                )
            sent = str(sent).replace('\n', '\\n').replace('\r', '\\r')

        else:
            # Handle standard WMT25 format
            if source:
                # WMT26 uses 'source_doc' instead of 'src_text'
                sent = obj.get('src_text') or obj.get('source_doc') or MISSING_TRANSLATION_MESSAGE
            elif reference:
                sent = MISSING_TRANSLATION_MESSAGE
                for ref in obj.get('refs', []):
                    if ref.get('translator') == reference:
                        sent = ref.get('text', MISSING_TRANSLATION_MESSAGE)
                        break
            else:  # system
                sent = MISSING_TRANSLATION_MESSAGE
                hyps = obj.get('hyps', obj.get('hypothesis', []))
                if len(hyps) > 0:
                    if isinstance(hyps, str):
                        sent = hyps or MISSING_TRANSLATION_MESSAGE
                    elif isinstance(hyps, list):
                        for hyp in hyps:
                            # if system is Boolean, not a string, take first system
                            if isinstance(system, bool) and system:
                                system = hyp.get('system')
                            if hyp.get('system') == system:
                                sent = hyp.get('text', MISSING_TRANSLATION_MESSAGE)
                                break
        out_sents.append(sent)

    # Write to txt file
    with smart_open(txt_path, 'wt', encoding='utf-8') as fout:
        for s in out_sents:
            fout.write(f"{s}\n")
    return True


def process_json_to_text(
    json_path,
    txt_path,
    source=None,
    system=None,
):
    """
    Extract source prompts or system answers from a JSON file.
    If source is True, extract prompts.
    If system is True, extract answers (first system found).
    If system is a string, it will be used to filter answers by system.
    """
    # Must specify exactly one of source or system
    if [source, system].count(None) != 1:
        raise ValueError(
            f'Exactly one of source or system must be provided, but got: '
            f'source={source}, system={system}'
        )

    # Read JSON file
    with smart_open(json_path, 'rt', encoding='utf-8') as fin:
        data = json.load(fin)
        
    if not isinstance(data, list):
        # If no entries, write empty file and bail
        with smart_open(txt_path, 'wt', encoding='utf-8'):
            pass
        return False

    # Build output sentences
    out_sents = []
    for obj in data:
        if not isinstance(obj, dict):
            continue
            
        if source:
            sent = obj.get('prompt', MISSING_TRANSLATION_MESSAGE)
        elif system:
            # For JSON, answers are directly in the object
            sent = obj.get('answer', MISSING_TRANSLATION_MESSAGE)
        
        # Escape newline characters to ensure each JSON object results in exactly one line
        sent = sent.replace('\n', '\\n').replace('\r', '\\r')
        out_sents.append(sent)

    # Write to txt file
    with smart_open(txt_path, 'wt', encoding='utf-8') as fout:
        for s in out_sents:
            fout.write(f"{s}\n")
    return True
