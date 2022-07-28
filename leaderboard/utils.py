"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""
import os.path

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


# Taken from sacrebleu which removed this with v2.2
#
# https://github.com/mjpost/sacrebleu/blob/65a8a9eeccd8c0c7875e875e12edf10db33ab0ba/sacrebleu/utils.py#L277
def process_to_text(rawfile, txtfile, field: int = None):
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
            'Exactly one of source, reference or system must be provided'
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
