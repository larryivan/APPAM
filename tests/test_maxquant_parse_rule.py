"""MaxQuant reads a protein's identifier from the first capture group of
`identifierParseRule`. A rule whose first group is the optional `sp|`/`tr|`
prefix gives every UniProt protein the identifier `sp|`, which merges distinct
proteins into one protein group and silently corrupts protein counts.
"""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PALEO_ROOT = REPO_ROOT / 'appam-paleoproteomics-main'


def default_rules():
    config = yaml.safe_load((PALEO_ROOT / 'config' / 'config.yaml').read_text(encoding='utf-8'))
    template = ET.parse(PALEO_ROOT / 'workflow' / 'templates' / 'mqpar.template.xml').getroot()
    renderer = (PALEO_ROOT / 'workflow' / 'scripts' / 'render_mqpar.py').read_text(encoding='utf-8')
    backend = (REPO_ROOT / 'backend' / 'app' / 'services' / 'pipeline_execution.py').read_text(encoding='utf-8')
    return {
        'workflow config': config['identifier_parse_rule'],
        'mqpar template': template.findtext('.//identifierParseRule'),
        'renderer default': re.search(r'"identifier_parse_rule", r"([^"]+)"', renderer).group(1),
        'backend default': re.search(r"'identifier_parse_rule', r'([^']+)'", backend).group(1),
    }


class MaxQuantIdentifierRuleTests(unittest.TestCase):
    def test_every_default_uses_the_same_rule(self):
        rules = default_rules()
        self.assertEqual(len(set(rules.values())), 1, rules)

    def test_first_group_is_the_protein_accession(self):
        rule = re.compile(default_rules()['workflow config'])
        headers = {
            '>sp|P02452|CO1A1_HUMAN Collagen alpha-1(I) chain OS=Homo sapiens': 'P02452',
            '>tr|A0A024R161|A0A024R161_HUMAN Guanine nucleotide-binding protein': 'A0A024R161',
            '>CON__P00761 Trypsin (porcine)': 'CON__P00761',
            '>AMELX_Hsap amelogenin, custom ancient-protein database': 'AMELX_Hsap',
        }
        for header, accession in headers.items():
            with self.subTest(header=header):
                self.assertEqual(rule.match(header).group(1), accession)


if __name__ == '__main__':
    unittest.main()
