"""Generate macOS and MSKLC layouts from the pinned Linux reference."""
from pathlib import Path
import ast,hashlib,json,re,unicodedata as ud
from mac_to_klc import KEYS,ROOT
REF=ROOT/'linux/reference'

def reference():
    manifest=json.loads((REF/'sources.json').read_text(encoding='utf-8'))
    for filename,info in manifest['files'].items():
        assert hashlib.sha256((REF/filename).read_bytes()).hexdigest()==info['sha256'],filename
    syms={}
    for line in (REF/'xkbcommon-keysyms.h').read_text(encoding='utf-8').splitlines():
        m=re.match(r'#define XKB_KEY_(\w+)\s+0x([0-9a-fA-F]+)',line)
        if not m:continue
        name,n=m[1],int(m[2],16);cp=re.search(r'U\+([0-9a-fA-F]{4,6})',line)
        if cp:syms[name]=chr(int(cp[1],16))
        elif 32<=n<=126 or 160<=n<=255:syms[name]=chr(n)
        elif n&0xff000000==0x01000000:syms[name]=chr(n&0xffffff)
    def symbol(name):
        if name.startswith('dead_'):return name
        if name in syms:return syms[name]
        if re.fullmatch('U[0-9a-fA-F]{4,6}',name):return chr(int(name[1:],16))
        raise ValueError('Unknown symbol '+name)
    text=re.sub(r'//[^\n]*','',(REF/'us').read_text(encoding='utf-8'))
    def block(name):
        m=re.search(r'xkb_symbols\s+"'+name+r'"\s*\{',text);start=m.end();i=start;depth=1
        while depth:
            if text[i]=='{':depth+=1
            elif text[i]=='}':depth-=1
            i+=1
        return text[start:i-1]
    def load(name,visited=()):
        assert name not in visited
        body=block(name);keys={}
        for parent in re.findall(r'include\s+"us\(([^)]+)\)"',body):keys.update(load(parent,visited+(name,)))
        for m in re.finditer(r'key\s+<(\w+)>\s*\{\s*\[([^]]+)\]',body):keys[m[1]]=[symbol(x.strip())for x in m[2].split(',')]
        return keys
    keys=load('altgr-intl');keys['SPCE']=[' ']*4
    positions={}
    for prefix,scans in [('AE',range(2,14)),('AD',range(16,28)),('AC',range(30,41)),('AB',range(44,54))]:
        positions.update({scan:prefix+f'{i:02d}'for i,scan in enumerate(scans,1)})
    positions.update({41:'TLDE',43:'BKSL',57:'SPCE'})
    dead_states={s for levels in keys.values()for s in levels if s.startswith('dead_')}
    compose={state:{}for state in sorted(dead_states)}
    for line in (REF/'Compose.pre').read_text(encoding='utf-8').splitlines():
        m=re.match(r'^<(dead_\w+)>\s+<(\w+)>\s*:\s*("(?:[^"\\]|\\.)*")',line)
        if not m or m[1]not in dead_states:continue
        try:base=symbol(m[2])
        except ValueError:continue
        if len(base)!=1:continue
        compose[m[1]][base]=ud.normalize('NFC',ast.literal_eval(m[3]))
    for state,table in compose.items():assert ' 'in table and len(table[' '])==1,state
    terms={state:table[' ']for state,table in compose.items()}
    assert len(set(terms.values()))==len(terms),'dead identifiers must be unique'
    records=[{'mac_code':code,'scan':scan,'vk':vk,'xkb':positions[scan],'symbols':keys[positions[scan]]}for code,scan,vk in KEYS]
    return records,compose,terms,manifest

def xml_attr(value):
    # Apple's keylayout compiler supports numeric references, not named entities.
    escaped = {
        "&": "&#x0026;", "<": "&#x003C;", ">": "&#x003E;",
        '"': "&#x0022;", "'": "&#x0027;",
        "\n": "&#x000A;", "\r": "&#x000D;", "\t": "&#x0009;",
    }
    return "".join(escaped.get(char, char) for char in value)


def generate():
    records,compose,terms,manifest=reference()
    # Original Mac file is a preserved template only for special-key maps,
    # Command, Caps Lock and JIS; printable ANSI maps are replaced from XKB.
    template=REF/'mac-template.keylayout'
    if not template.exists():raise RuntimeError('Missing preserved Mac template')
    text=template.read_text(encoding='utf-8-sig')
    text=re.sub(r'(<keyboard\b[^>]*\bname=")[^"]*',r'\g<1>US International — AltGr dead keys',text,count=1)
    all_bases=sorted({base for table in compose.values()for base in table})
    action_ids={base:'linux_u'+format(ord(base),'04x')for base in all_bases}
    state_ids={state:'linux_'+state for state in compose}
    def binding(value):
        if value.startswith('dead_'):return 'action="linux_enter_'+value+'"'
        if value in action_ids:return 'action="'+action_ids[value]+'"'
        return 'output="'+xml_attr(value)+'"'
    def rewrite_ansi(match):
        ansi=match[0]
        for index in range(4):
            def rewrite_map(m,index=index):
                content=m[0]
                for rec in records:
                    code=rec['mac_code'];pattern=r'<key code="'+str(code)+r'"[^>]*/>'
                    content,n=re.subn(pattern,lambda _:f'<key code="{code}" {binding(rec["symbols"][index])}/>',content,count=1)
                    assert n==1,(index,code)
                return content
            ansi,n=re.subn(r'<keyMap index="'+str(index)+r'">.*?</keyMap>',rewrite_map,ansi,count=1,flags=re.S)
            assert n==1
        return ansi
    text=re.sub(r'<keyMapSet id="ANSI">.*?</keyMapSet>',rewrite_ansi,text,count=1,flags=re.S)
    generated=[]
    for state in sorted(compose):
        generated.append(f'        <action id="linux_enter_{state}"><when state="none" next="{state_ids[state]}"/></action>')
    for base in all_bases:
        generated.append(f'        <action id="{action_ids[base]}">')
        generated.append(f'            <when state="none" output="{xml_attr(base)}"/>')
        for state,table in sorted(compose.items()):
            if base in table:generated.append(f'            <when state="{state_ids[state]}" output="{xml_attr(table[base])}"/>')
        generated.append('        </action>')
    text=text.replace('    </actions>','\n'.join(generated)+'\n    </actions>',1)
    new_terms='\n'.join(f'        <when state="{state_ids[s]}" output="{xml_attr(t)}"/>'for s,t in sorted(terms.items()))
    text=text.replace('    </terminators>',new_terms+'\n    </terminators>',1)
    maxout=max(2,max(len(out.encode('utf-16-le'))//2 for table in compose.values()for out in table.values()))
    text=re.sub(r'maxout="\d+"',f'maxout="{maxout}"',text,count=1)
    (ROOT/'mac/us-intl-altgr.keylayout').write_bytes(text.replace('\r\n','\n').encode('utf-8'))
    # Stable KLC dead identifiers use the same literal terminators as Linux.
    limitations=[]
    def cell(symbol):
        if symbol.startswith('dead_'):return f'{ord(terms[symbol]):04x}@'
        if len(symbol)!=1 or ord(symbol)>0xffff:raise ValueError('Unrepresentable direct KLC output')
        return f'{ord(symbol):04x}'
    lines=['KBD\tusagrlx\t"US International — AltGr dead keys"','',
        'COPYRIGHT\t"Based on xkeyboard-config; see linux/reference/COPYING.xkeyboard-config"',
        'COMPANY\t"Athesto"','LOCALENAME\t"en-US"','LOCALEID\t"00000409"','VERSION\t1.1','',
        'SHIFTSTATE','','0','1','2','6','7','','LAYOUT','','// SC VK Cap Normal Shift Ctrl AltGr Shift+AltGr']
    for rec in records:
        normal,shift,alt,alt_shift=rec['symbols']
        caps=int(len(normal)==1 and normal.isalpha()and shift==normal.upper())
        if len(alt)==1 and alt.isalpha()and alt_shift==alt.upper():caps|=4
        ctrl={33:'001b',42:'001c',30:'001d',49:'0020'}.get(rec['mac_code'],'-1')
        lines.append(f'{rec["scan"]:02x}\t{rec["vk"]}\t{caps}\t{cell(normal)}\t{cell(shift)}\t{ctrl}\t{cell(alt)}\t{cell(alt_shift)}')
    lines.append('56\tOEM_102\t0\t005c\t007c\t001c\t005c\t007c')
    for state,table in sorted(compose.items()):
        lines+=['',f'DEADKEY\t{ord(terms[state]):04x}','']
        for base,result in sorted(table.items(),key=lambda item:(item[0]==' ',item[0])):
            if len(result)!=1 or ord(result)>0xffff or ord(base)>0xffff:
                limitations.append({'state':state,'input':base,'linux':result,'reason':'KLC DEADKEY needs one BMP code unit for input and output'})
            else:lines.append(f'{ord(base):04x}\t{ord(result):04x}')
    lines+=['','KEYNAME','','01\tEsc','0e\tBackspace','0f\tTab','1c\tEnter','1d\tCtrl','2a\tShift','36\t"Right Shift"','38\tAlt','39\tSpace','3a\t"Caps Lock"','','KEYNAME_EXT','','1d\t"Right Ctrl"','38\t"Right Alt"','5b\t"Left Windows"','5c\t"Right Windows"','','KEYNAME_DEAD','']
    lines += [f'{ord(t):04x}\t"{s}"'for s,t in sorted(terms.items())]
    lines+=['','DESCRIPTIONS','','0409\tUS International — AltGr dead keys','LANGUAGENAMES','','0409\tEnglish (United States)','ENDKBD','']
    (ROOT/'windows/us-intl-altgr.klc').write_bytes(b'\xff\xfe'+('\r\n'.join(lines)).encode('utf-16-le'))
    spec={'reference':'xkeyboard-config 2.46 us(altgr-intl)','source_manifest':'reference/sources.json','keys':records,'dead_keys':compose,'terminators':terms,
        'scope':'ANSI four levels; explicit two-key Compose pairs; platform special keys and fallback differ'}
    (ROOT/'linux/us-intl-altgr.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    report={'source':'linux/us-intl-altgr.json','sha256':hashlib.sha256((ROOT/'linux/us-intl-altgr.json').read_bytes()).hexdigest(),
        'key_positions':len(records),'dead_key_states':len(compose),'build_status_file':'windows/dist/linux-build-info.json','limitations':limitations,
        'scope':'Linux-derived ANSI four-level assignments and explicit two-key Compose; runtime fallback/platform behavior remains platform-specific'}
    (ROOT/'windows/us-intl-altgr.report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Generated Linux-based Mac and Windows: {len(records)*4} direct cells; {len(compose)} dead keys; {sum(map(len,compose.values()))} Compose pairs; {len(limitations)} KLC exceptions')
if __name__=='__main__':generate()
