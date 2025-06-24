"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import os.path
import re
from typing import Optional
import json

import lxml.etree as ET
from sacrebleu.utils import smart_open


MISSING_TRANSLATION_MESSAGE = "NO TRANSLATION AVAILABLE"


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
    # Read the JSONL file and extract the required information
    with smart_open(jsonl_path, 'rt', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
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

    # Read and collect JSONL entries
    entries = []
    with smart_open(jsonl_path, 'rt', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
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
        if source:
            sent = obj.get('src_text', MISSING_TRANSLATION_MESSAGE)
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
