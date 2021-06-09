"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations
"""

import lxml.etree as ET


def analyze_xml_file(xml_path):
    """
    Return all source languages, reference languages, translators, and systems found in the XML file.
    Code extracted from https://github.com/wmt-conference/wmt-format-tools/blob/main/wmtformat/unwrap.py
    """
    src_langs, ref_langs, translators, systems = set(), set(), set(), set()
    tree = ET.parse(xml_path)

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

    return src_langs, ref_langs, translators, systems


def process_xml_to_text(
    xml_path, txt_path, source=None, reference=None, system=None
):
    """
    Extract source, reference(s) or system texts from the XML file.
    Multiple references will be separated by a tab.
    """

    MISSING_TRANSLATION_MESSAGE = "NO TRANSLATION AVAILABLE"

    # TODO: ignore test suites
    # TODO: check if only one is requested: source or ref or sys
    # TODO: support multiple references
    # TODO: support systems

    tree = ET.parse(xml_path)
    src_sents, ref_sents, sys_sents = [], [], []
    out_sents = []

    for doc in tree.getroot().findall(".//doc"):
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
                    for seg in ref_doc.findall(f".//seg")
                }
                if ref_doc is not None
                else {}
            )

        if system:
            raise NotImplementedError(
                'Extracting system translation from XML is not implemented yet'
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
                pass

    with open(txt_path, 'w') as txt_file:
        for sent in out_sents:
            txt_file.write("{}\n".format(sent))
