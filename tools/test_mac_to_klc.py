"""Regression tests for Linux-derived mappings and byte formats."""
from pathlib import Path
import hashlib,json,re,unittest
from mac_to_klc import ROOT
from generate_from_linux import reference,xml_attr

class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records,cls.compose,cls.terms,_=reference()
        cls.report=json.loads((ROOT/'linux/comparison.json').read_text(encoding='utf-8'))
        cls.klc=(ROOT/'windows/us-intl-altgr.klc').read_bytes()
        lines=cls.klc.decode('utf-16').splitlines();cls.rows={};cls.dead={};section=None
        for line in lines:
            if line=='LAYOUT':section='layout';continue
            if line.startswith('DEADKEY\t'):section=line.split()[1];cls.dead[section]={};continue
            if line=='KEYNAME':section=None
            p=line.split('\t')
            if section=='layout'and len(p)==8 and re.fullmatch('[0-9a-f]{2}',p[0]):cls.rows[int(p[0],16)]=p
            elif section in cls.dead and len(p)==2:cls.dead[section][chr(int(p[0],16))]=chr(int(p[1],16))
    def test_direct_linux_audit(self):
        self.assertEqual(self.report['cells_per_platform'],192)
        self.assertEqual(self.report['direct_difference_counts'],{'mac':0,'windows':0})
        self.assertEqual(self.report['compose_difference_counts']['mac'],0)
    def test_windows_explicit_compositions(self):
        missing=[]
        for state,table in self.compose.items():
            actual=self.dead[f'{ord(self.terms[state]):04x}']
            for base,result in table.items():
                if len(result)==1 and ord(result)<=0xffff and ord(base)<=0xffff:self.assertEqual(actual[base],result)
                else:missing.append((state,base,result))
        limits=json.loads((ROOT/'windows/us-intl-altgr.report.json').read_text(encoding='utf-8'))['limitations']
        self.assertEqual(set(missing),{(e['state'],e['input'],e['linux'])for e in limits})
        self.assertEqual(len(missing),self.report['compose_difference_counts']['windows'])
    def test_spanish_and_linux_corrections(self):
        by_vk={r['vk']:r['symbols']for r in self.records}
        self.assertEqual(by_vk['A'],['a','A','á','Á'])
        self.assertEqual(by_vk['N'],['n','N','ñ','Ñ'])
        self.assertEqual(by_vk['1'][2:],['¹','¡'])
        self.assertEqual(by_vk['V'][3],'™');self.assertEqual(by_vk['M'][3],'±')
        self.assertEqual(by_vk['B'][2:],['·','dead_stroke'])
        self.assertEqual(by_vk['SPACE'],[' ']*4)
        self.assertEqual(self.compose['dead_acute']['a'],'á')
        self.assertEqual(self.compose['dead_acute'][' '],"'")
    def test_formats(self):
        self.assertTrue(self.klc.startswith(b'\xff\xfe'))
        self.assertNotIn('\n',self.klc[2:].decode('utf-16-le').replace('\r\n',''))
        mac=(ROOT/'mac/us-intl-altgr.keylayout').read_bytes()
        mac.decode('utf-8');self.assertNotIn(b'\r',mac)
    def test_mac_numeric_character_references(self):
        # A generic XML parser accepts named entities that macOS silently drops.
        self.assertEqual(xml_attr('&<>"\'\n\r\t'),
                         '&#x0026;&#x003C;&#x003E;&#x0022;&#x0027;&#x000A;&#x000D;&#x0009;')
        self.assertEqual(xml_attr('áÑ'), 'áÑ')
        mac=(ROOT/'mac/us-intl-altgr.keylayout').read_text(encoding='utf-8')
        self.assertIsNone(re.search(r'&[A-Za-z][A-Za-z0-9]*;',mac))
        self.assertIn('<key code="26" output="&#x0026;"/>',mac)
        self.assertIn('<key code="39" output="&#x0022;"/>',mac)
        for action,output in [('linux_u003c','&#x003C;'),
                              ('linux_u003e','&#x003E;')]:
            self.assertIn(f'<action id="{action}">\n            <when state="none" output="{output}"/>',mac)

    def test_generated_hashes_current(self):
        for rel,wanted in self.report['compared_files'].items():self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),wanted)

if __name__=='__main__':unittest.main()
