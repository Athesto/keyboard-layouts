"""Audit local Mac and KLC layouts against a pinned Linux XKB reference.
Only parses the simple us(intl)/us(altgr-intl) symbol definitions; it is
not a general XKB compiler. Dead-key comparison covers explicit two-key
Compose sequences, not toolkit-specific fallback or longer sequences.
"""
from pathlib import Path
import ast,hashlib,json,re,unicodedata as ud,xml.etree.ElementTree as ET
from mac_to_klc import KEYS,ROOT
REF=ROOT/'linux/reference'
STATES=['normal','Shift','AltGr','Shift+AltGr']

def run():
    source_manifest=json.loads((REF/'sources.json').read_text(encoding='utf-8'))
    for name,info in source_manifest['files'].items():
        assert hashlib.sha256((REF/name).read_bytes()).hexdigest()==info['sha256'],name
    header=(REF/'xkbcommon-keysyms.h').read_text(encoding='utf-8')
    syms={}
    for line in header.splitlines():
        m=re.match(r'#define XKB_KEY_(\w+)\s+0x([0-9a-fA-F]+)',line)
        if not m:continue
        name,num=m[1],int(m[2],16)
        unicode=re.search(r'U\+([0-9A-Fa-f]{4,6})',line)
        if unicode:syms[name]=chr(int(unicode[1],16))
        elif 0x20<=num<=0x7e or 0xa0<=num<=0xff:syms[name]=chr(num)
        elif num&0xff000000==0x01000000:syms[name]=chr(num&0xffffff)
    def symbol(name):
        if name.startswith('dead_'):return name
        if name in syms:return syms[name]
        if re.fullmatch(r'U[0-9A-Fa-f]{4,6}',name):return chr(int(name[1:],16))
        raise ValueError('Unresolved Linux symbol '+name)
    text=re.sub(r'//[^\n]*','',(REF/'us').read_text(encoding='utf-8'))
    def block(name):
        m=re.search(r'xkb_symbols\s+"'+re.escape(name)+r'"\s*\{',text)
        if not m:raise ValueError(name)
        start=m.end();i=start;depth=1
        while depth:
            if text[i]=='{':depth+=1
            elif text[i]=='}':depth-=1
            i+=1
        return text[start:i-1]
    def inherited(name,seen=()):
        assert name not in seen
        content=block(name);result={}
        for parent in re.findall(r'include\s+"us\(([^)]+)\)"',content):result.update(inherited(parent,seen+(name,)))
        for m in re.finditer(r'key\s+<(\w+)>\s*\{\s*\[([^]]+)\]',content):result[m[1]]=[symbol(x.strip()) for x in m[2].split(',')]
        return result
    linux=inherited('altgr-intl')
    # Space is supplied by the PC keymap, not by this alphanumeric variant.
    linux['SPCE']=[' ']*4
    positions={}
    for prefix,scans in [('AE',range(2,14)),('AD',range(16,28)),('AC',range(30,41)),('AB',range(44,54))]:
        for i,scan in enumerate(scans,1):positions[scan]=prefix+f'{i:02d}'
    positions.update({41:'TLDE',43:'BKSL',57:'SPCE'})
    aliases={'dead_diaresis':'dead_diaeresis','dead_circum':'dead_circumflex'}
    raw=(ROOT/'mac/us-intl-altgr.keylayout').read_bytes()
    xml=raw.decode('utf-8-sig').replace('version="1.1"','version="1.0"')
    xml=re.sub(r'&#x([0-9a-fA-F]+);',lambda m:'' if int(m[1],16)<32 else m[0],xml)
    root=ET.fromstring(xml)
    maps={int(m.attrib['index']):{int(k.attrib['code']):k.attrib for k in m}for m in root.find("keyMapSet[@id='ANSI']")}
    actions={a.attrib['id']:{w.attrib['state']:w.attrib for w in a}for a in root.find('actions')}
    terms={w.attrib['state']:w.attrib['output']for w in root.find('terminators')}
    aliases.update({state:state.removeprefix('linux_') for state in terms if state.startswith('linux_')})
    def mac(index,code):
        entry=maps[index][code]
        spec=entry if 'output'in entry else actions[entry['action']]['none']
        state=spec.get('next')
        return aliases.get(state,state) if state else spec.get('output','')
    klc=(ROOT/'windows/us-intl-altgr.klc').read_text(encoding='utf-16')
    rows={};dead={};section=None
    for line in klc.splitlines():
        line=line.split('//')[0].strip();p=line.split()
        if line=='LAYOUT':section='layout';continue
        if line.startswith('DEADKEY'):
            section=p[1];dead[section]={};continue
        if line.startswith(('KEYNAME','LIGATURE','DESCRIPTIONS','LANGUAGENAMES','ENDKBD')):section=None
        if section=='layout'and len(p)==8:rows[int(p[0],16)]=p
        elif section in dead and len(p)==2:dead[section][chr(int(p[0],16))]=chr(int(p[1].rstrip('@'),16))
    dead_ids={}
    for state,term in terms.items():
        char=term if len(term)==1 else ''.join(c for c in term if ud.combining(c))
        dead_ids[f'{ord(char):04x}']=aliases.get(state,state)
    def windows(scan,index):
        token=rows[scan][[3,4,6,7][index]]
        if token=='-1':return ''
        if token.endswith('@'):return dead_ids[token[:-1]]
        return chr(int(token,16))
    differences=[]
    for code,scan,vk in KEYS:
        pos=positions[scan]
        for i,wanted in enumerate(linux[pos]):
            for platform,actual in [('mac',mac(i,code)),('windows',windows(scan,i))]:
                if wanted!=actual:differences.append({'platform':platform,'key':vk,'xkb_position':pos,'level':STATES[i],'linux':wanted,'actual':actual})
    # Explicit Linux Compose pairs for dead keys reachable from this variant.
    reachable={v for levels in linux.values()for v in levels if v.startswith('dead_')}
    compose={}
    for line in (REF/'Compose.pre').read_text(encoding='utf-8').splitlines():
        m=re.match(r'^<(dead_\w+)>\s+<(\w+)>\s*:\s*("(?:[^"\\]|\\.)*")',line)
        if not m or m[1]not in reachable:continue
        try:base=symbol(m[2])
        except ValueError:continue
        if len(base)!=1:continue
        out=ast.literal_eval(m[3]);compose[m[1],base]=ud.normalize('NFC',out)
    mac_pairs={}
    for action in actions.values():
        base=action.get('none',{}).get('output')
        if not base or len(base)!=1:continue
        for state,spec in action.items():
            state=aliases.get(state,state)
            if state in reachable and 'output'in spec:mac_pairs[state,base]=ud.normalize('NFC',spec['output'])
    for state,term in terms.items():
        normalized=aliases.get(state,state)
        mac_pairs[normalized,' ']=term
    win_pairs={(dead_ids[state],base):out for state,table in dead.items()for base,out in table.items()}
    compose_diffs=[]
    for (state,base),wanted in sorted(compose.items()):
        for platform,pairs in [('mac',mac_pairs),('windows',win_pairs)]:
            actual=pairs.get((state,base))
            if actual!=wanted:compose_diffs.append({'platform':platform,'state':state,'input':base,'linux':wanted,'actual':actual})
    counts={p:sum(d['platform']==p for d in differences)for p in ['mac','windows']}
    report={'reference':'xkeyboard-config 2.46 us(altgr-intl)', 'source_manifest':'reference/sources.json',
        'positions':len(KEYS),'levels':STATES,'cells_per_platform':len(KEYS)*4,
        'direct_difference_counts':counts,'direct_differences':differences,
        'explicit_linux_compose_pairs':len(compose),'compose_difference_counts':{p:sum(d['platform']==p for d in compose_diffs)for p in ['mac','windows']},
        'compose_differences':compose_diffs,
        'scope':['Printable ANSI normal/Shift/AltGr/Shift+AltGr; excludes Control/CapsLock/Command/JIS/keypad/ISO extra key',
                 'Explicit two-key en_US.UTF-8 Compose pairs; missing table entries are not proof of missing runtime output: toolkit fallback may apply',
                 'Linux Compose can be customized by locale, toolkit and user; pinned here separately from xkeyboard-config',
                 'No existing Mac/Windows layout or installer has been modified by this audit']}
    report['compared_files']={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in ['mac/us-intl-altgr.keylayout','windows/us-intl-altgr.klc']}
    (ROOT/'linux/comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    def display(s):
        if s is None:return '(no explicit entry)'
        if s=='':return '(empty)'
        if s==' ':return 'Space'
        return s.replace('|','\\|').replace('`','\\`')
    lines=['# Linux reference comparison','','Reference: xkeyboard-config **2.46**, `us(altgr-intl)`.',
        'Pinned sources and hashes: [reference/sources.json](reference/sources.json).','',
        f'Compared {len(KEYS)} ANSI positions × 4 levels = {len(KEYS)*4} cells per platform.',
        f'Direct differences: macOS **{counts["mac"]}**, Windows **{counts["windows"]}**.','',
        '| Key | Level | Linux | macOS | Windows |','| --- | --- | --- | --- | --- |']
    for code,scan,vk in KEYS:
        for i,wanted in enumerate(linux[positions[scan]]):
            m,w=mac(i,code),windows(scan,i)
            if wanted!=m or wanted!=w:lines.append('| '+' | '.join(map(display,[vk,STATES[i],wanted,m,w]))+' |')
    lines+=['','## Dead-key sequences','',f'Compared {len(compose)} explicit Linux Compose pairs. See [comparison.json](comparison.json)',
        'for per-sequence differences. A missing explicit entry may be handled by','runtime fallback; it is not proof that the character cannot be typed.','',
        'Direct mappings and explicit compositions have different compatibility scopes; see the counts above.','Both generated layouts now use the pinned Linux reference; Windows omits unsupported KLC compositions.','',
        '## Scope','']+['- '+s for s in report['scope']]
    (ROOT/'linux/COMPARISON.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items()if k in ['reference','positions','direct_difference_counts','explicit_linux_compose_pairs','compose_difference_counts']},indent=2))
    print('\n'.join(lines[8:]))
if __name__=='__main__':run()
