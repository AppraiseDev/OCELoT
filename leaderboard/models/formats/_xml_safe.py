"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

Hardened lxml parsing helpers shared by the format validators.

These guard against XXE (external entity / DTD resolution, SSRF) and
entity-expansion ("billion laughs") denial-of-service attacks when parsing
untrusted, user-uploaded XML/SGML documents.
"""
import lxml.etree as ET


def safe_xml_parser():
    """Return an lxml parser hardened against XXE and entity-expansion DoS.

    A fresh parser is returned on each call because lxml parsers should not be
    shared between threads.
    """
    return ET.XMLParser(
        resolve_entities=False,  # do not expand entities (billion laughs / XXE)
        no_network=True,         # never fetch remote DTDs/entities (SSRF)
        load_dtd=False,          # do not load external DTDs
        dtd_validation=False,
        huge_tree=False,         # keep libxml2's built-in size/expansion limits
    )
