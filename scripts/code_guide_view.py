"""Offline source-and-comment viewer. Uses only Python's standard library."""
import builtins
import html
import io
import json
import keyword
import tokenize


def highlight(source):
    lines = source.splitlines()
    spans = [[] for _ in lines]
    previous = ""
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        kind = ""
        if token.type == tokenize.NAME:
            kind = "kw" if keyword.iskeyword(token.string) else (
                "fn" if previous == "def" else "type" if previous == "class" else
                "builtin" if token.string in dir(builtins) else "name")
            previous = token.string
        elif token.type == tokenize.NUMBER:
            kind = "num"
        elif token.type == tokenize.STRING or "FSTRING" in tokenize.tok_name[token.type]:
            kind = "str"
        elif token.type == tokenize.COMMENT:
            kind = "comment"
        elif token.type == tokenize.OP:
            kind = "op"
        if kind:
            for row in range(token.start[0], min(token.end[0], len(lines)) + 1):
                start = token.start[1] if row == token.start[0] else 0
                end = token.end[1] if row == token.end[0] else len(lines[row - 1])
                if end > start:
                    spans[row - 1].append((start, end, kind))
    result = []
    for line, tokens in zip(lines, spans):
        cursor, parts = 0, []
        for start, end, kind in sorted(tokens):
            if start < cursor:
                continue
            parts.append(html.escape(line[cursor:start]))
            parts.append('<span class="' + kind + '">' + html.escape(line[start:end]) + '</span>')
            cursor = end
        parts.append(html.escape(line[cursor:]))
        result.append("".join(parts))
    return result


def render(source, rows, mission, digest, date='2026-11-10'):
    esc = html.escape
    scopes = list(dict.fromkeys(row["scope"] for row in rows if row["scope"] != "전역·구역 사이"))
    nav = ''.join('<a href="#L' + str(next(r['number'] for r in rows if r['scope'] == s))
                  + '"><span class="symbol">ƒ</span>' + esc(s) + '</a>' for s in scopes)
    options = ''.join('<option>' + esc(s) + '</option>' for s in scopes)
    colored = highlight(source)
    body = []
    for row, code in zip(rows, colored):
        n = row['number']
        if row.get('bonus'):
            row = dict(row, meaning='[보너스] ' + row['meaning'])
        note = ('<span class="blank-note" aria-hidden="true"></span>' if row['blank'] else
                '<span>' + esc(row['meaning']) + '</span>' if row['meaning'] == row['detail'] else
                '<details><summary>' + esc(row['meaning']) + '</summary><p>' + esc(row['detail']) + '</p></details>')
        body.append(f'<div class="line" id="L{n}" data-scope="{esc(row["scope"], quote=True)}" '
                    f'data-blank="{str(row["blank"]).lower()}"><a class="ln" href="#L{n}" '
                    f'aria-label="{n}행 선택">{n}</a><div class="code"><code>{code or " "}</code></div>'
                    f'<div class="note">{note}</div></div>')
    data = json.dumps({'source': source, 'mission': mission}, ensure_ascii=False).replace('<', '\\u003c')
    return TEMPLATE.replace('@@MISSION@@', esc(mission)).replace('@@HASH@@', digest).replace(
        '@@COUNT@@', str(len(rows))).replace('@@NAV@@', nav).replace('@@OPTIONS@@', options).replace(
        '@@ROWS@@', ''.join(body)).replace('@@DATA@@', data).replace('@@DATE@@', date)


TEMPLATE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>@@MISSION@@ · main.py 코드와 줄별 설명</title><style>
:root{color-scheme:dark;--bg:#1f1f1f;--code:#1e1e1e;--note:#252526;--border:#343434;--muted:#a3a3a3;--accent:#75beff;--font:15px;--code-width:59%}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#d4d4d4;font:14px/1.6 "Segoe UI","Malgun Gothic",sans-serif}button,input,select{font:inherit}button,select,input[type=search]{background:#313131;color:#eee;border:1px solid #555;border-radius:4px;padding:6px 10px}button{cursor:pointer}button:hover{background:#414141}button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}a{color:inherit;text-decoration:none}.titlebar{height:40px;display:flex;align-items:center;gap:12px;padding:0 16px;background:#181818;border-bottom:1px solid var(--border)}.brand{color:#75beff;font-size:19px}.titlebar strong{font-size:13px;font-weight:500}.titlebar small{margin-left:auto;color:var(--muted)}.layout{display:grid;grid-template-columns:220px minmax(0,1fr);min-height:calc(100vh - 40px)}aside{background:#181818;border-right:1px solid var(--border);padding:18px 10px;position:sticky;top:0;height:100vh;overflow:auto}.eyebrow{letter-spacing:1.5px;color:#a3a3a3;font-size:10px;padding:0 10px;margin:0 0 10px}.file{background:#2a2d2e;padding:7px 12px;border-left:2px solid #007acc}.py{color:#e5c07b;margin-right:8px}.outline{margin-top:26px}.outline a{display:block;padding:5px 10px;font:12px/1.7 Consolas,"Malgun Gothic",monospace;overflow-wrap:anywhere}.outline a:hover{background:#2a2d2e}.symbol{color:#dcdcaa;margin-right:9px}.sidebar-foot{color:#929292;font-size:11px;margin:24px 10px}main{min-width:0}.tabbar{background:#181818;border-bottom:1px solid var(--border);display:flex;align-items:stretch}.tab{background:#1f1f1f;border-top:2px solid #007acc;border-right:1px solid var(--border);padding:10px 22px}.tabbar .label{align-self:center;margin-left:18px;color:#8c8c8c;font-size:12px}.intro{padding:20px 24px 14px;border-bottom:1px solid var(--border)}h1{font-size:21px;color:#f0f0f0;margin:0 0 7px;font-weight:600}.intro p{color:#b4b4b4;margin:4px 0;font-size:13px}.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:12px 24px;border-bottom:1px solid var(--border);background:#202020}.toolbar input[type=search]{flex:1;min-width:190px}.toolbar select{max-width:230px}.toolbar label{display:flex;gap:6px;align-items:center;white-space:nowrap;color:#bdbdbd;font-size:12px}.secondary{display:flex;gap:20px;align-items:center;flex-wrap:wrap;padding:7px 24px;color:#999;font-size:12px}.secondary label{display:flex;align-items:center;gap:7px}.secondary input{width:85px;accent-color:#007acc}.copy{background:#0e639c;border-color:#0e639c;white-space:nowrap}.copy:hover{background:#1177bb}.status{color:#a7d89d;font-size:12px;min-height:19px}.editor-scroll{overflow:auto;border-top:1px solid var(--border)}.column-labels,.line{display:grid;grid-template-columns:54px minmax(0,calc(var(--code-width) - 54px)) minmax(0,1fr);min-width:920px}.column-labels{background:#202020;color:#999;font-size:11px;position:sticky;top:0;z-index:1;border-bottom:1px solid var(--border)}.column-labels span{padding:7px 14px}.line{background:var(--code);min-height:28px;scroll-margin-top:45vh}.line[hidden]{display:none}.ln{color:#858585;text-align:right;user-select:none;font:13px/26px Consolas,monospace;padding:0 12px 0 4px}.ln:hover{color:#fff}.code{overflow:auto;scrollbar-width:thin;padding:0 12px;tab-size:4;background-image:repeating-linear-gradient(to right,transparent 0,transparent calc(4ch - 1px),#ffffff08 calc(4ch - 1px),#ffffff08 4ch);font:var(--font)/26px Consolas,"Cascadia Code","Malgun Gothic",monospace}.code code{font:inherit;white-space:pre}.note{background:var(--note);border-left:1px solid #414141;padding:2px 18px;color:#c9d1da;font:13px/22px "Segoe UI","Malgun Gothic",sans-serif;min-width:0}.note details summary{cursor:pointer;list-style:none;position:relative;padding-right:18px}.note summary::-webkit-details-marker{display:none}.note summary::after{content:'+';position:absolute;right:0;color:#8b9caf}.note details[open] summary::after{content:'−'}.note details p{color:#9faebd;border-left:2px solid #4b657e;padding-left:10px;margin:6px 0 9px;font-size:12px}.blank-note{color:#686868;font-size:11px}.line:hover .ln,.line:hover .code{background-color:#ffffff05}.line:target .code,.line:target .ln{background-color:#264f784d}.line:target .note{background:#2b3d4c;border-left-color:#75beff}.kw{color:#c586c0}.fn{color:#dcdcaa}.type,.builtin{color:#4ec9b0}.name{color:#9cdcfe}.num{color:#b5cea8}.str{color:#ce9178}.comment{color:#6a9955}.op{color:#d4d4d4}.empty{padding:50px;text-align:center;color:#a3a3a3}.statusbar{background:#007acc;color:white;padding:4px 16px;font-size:11px;display:flex;justify-content:space-between;gap:10px}.foot{padding:14px 24px;color:#858585;font-size:11px;overflow-wrap:anywhere}.copy-fallback{display:none;width:100%;height:200px;background:#1e1e1e;color:#ddd}.collapsed .layout{grid-template-columns:minmax(0,1fr)}.collapsed aside{display:none}@media(max-width:1000px){.layout{grid-template-columns:180px minmax(0,1fr)}.toolbar{padding:10px 14px}.intro{padding:16px}.column-labels,.line{min-width:850px}}@media(max-width:1000px){.layout{display:block}aside{display:none}.titlebar small{display:none}.column-labels{display:none}.line{min-width:0;grid-template-columns:42px minmax(0,1fr)}.ln{grid-column:1;grid-row:1;padding-right:8px}.code{grid-column:2;grid-row:1;min-width:0}.note{grid-column:2;border-left:2px solid #435466;margin-bottom:7px;padding:3px 10px}.line[data-blank=true] .note{display:none}.line[data-blank=true]{min-height:14px}.toolbar select{max-width:100%}.statusbar{flex-wrap:wrap}.secondary .width-control{display:none}.tabbar .label{font-size:11px}}@media print{aside,.titlebar,.toolbar,.secondary,.statusbar{display:none}.layout{display:block}.editor-scroll{overflow:visible}.line,.column-labels{min-width:0}.code{white-space:pre-wrap;overflow-wrap:anywhere}.code code{white-space:pre-wrap}.line{break-inside:avoid}body{print-color-adjust:exact}}
</style></head><body>
<header class="titlebar"><span class="brand">&lt;/&gt;</span><button id="sidebar" aria-label="함수 목록 접기" aria-expanded="true">☰</button><strong>@@MISSION@@ · 코드 읽기</strong><small>main.py — 코드와 설명을 나란히</small></header>
<div class="layout"><aside><p class="eyebrow">EXPLORER</p><div class="file"><span class="py">Py</span>main.py</div><div class="outline"><p class="eyebrow">함수 · 클래스</p>@@NAV@@</div><p class="sidebar-foot">함수 이름을 누르면 해당 줄로 이동합니다.<br><br>설명의 +를 누르면 상세 설명을 펼칩니다.</p></aside>
<main><div class="tabbar"><div class="tab"><span class="py">Py</span>main.py</div><span class="label">Python · @@MISSION@@</span></div>
<section class="intro"><h1>코드 한 줄, 바로 옆에 설명</h1><p>왼쪽은 실제 main.py, 오른쪽은 같은 줄의 역할입니다. 들여쓰기와 원본 줄 번호를 유지했습니다.</p><p>@@DATE@@ 보너스 포함 코드 @@COUNT@@줄 기준 · 해설 페이지의 버튼은 원본 파일을 수정하지 않습니다.</p></section>
<div class="toolbar"><input type="search" id="search" placeholder="코드 · 설명 검색" aria-label="코드와 설명 검색"><select id="scope" aria-label="함수와 클래스 선택"><option value="">모든 함수 · 구역</option>@@OPTIONS@@</select><button id="copy" class="copy">전체 코드 복사</button><button id="reset">초기화</button></div>
<div class="secondary"><label><input type="checkbox" id="blank">빈 줄 숨기기</label><label><input type="checkbox" id="detail">상세 설명 모두</label><label>코드 크기 <input type="range" id="font" min="12" max="20" value="15" aria-label="코드 글자 크기"><output id="font-value">15px</output></label><label class="width-control">코드 너비 <input type="range" id="width" min="45" max="72" value="59" aria-label="코드 영역 너비"></label><span id="count" aria-live="polite"></span><span id="copy-status" class="status" role="status"></span></div>
<textarea class="copy-fallback" id="fallback" aria-label="전체 코드 수동 복사" readonly></textarea><div class="editor-scroll"><div class="column-labels"><span>줄</span><span>main.py</span><span>이 줄이 하는 일 · + 상세 설명</span></div>@@ROWS@@<div class="empty" id="empty" hidden>검색 결과가 없습니다. 검색어나 함수 선택을 바꿔 보세요.</div></div>
<div class="statusbar"><span>Python · UTF-8 · 들여쓰기 유지</span><span>@@MISSION@@ / main.py</span></div><footer class="foot">실제 코드 스냅샷 SHA-256: @@HASH@@<br>빈 줄을 숨겨도 원본 줄 번호를 유지합니다. 코드가 바뀌면 설명도 다시 검토해야 합니다.</footer></main></div>
<script type="application/json" id="source-data">@@DATA@@</script><script>
(()=>{const $=s=>document.querySelector(s),rows=[...document.querySelectorAll('.line')],data=JSON.parse($('#source-data').textContent);function apply(){let count=0;const q=$('#search').value.trim().toLowerCase(),scope=$('#scope').value;for(const row of rows){row.hidden=($('#blank').checked&&row.dataset.blank==='true')||(scope&&row.dataset.scope!==scope)||(q&&!row.textContent.toLowerCase().includes(q));if(!row.hidden)count++;}$('#count').textContent=count+' / '+rows.length+'줄';$('#empty').hidden=count!==0;}['search','scope','blank'].forEach(id=>$('#'+id).addEventListener(id==='search'?'input':'change',apply));$('#detail').addEventListener('change',()=>document.querySelectorAll('.note details').forEach(d=>d.open=$('#detail').checked));$('#font').addEventListener('input',()=>{document.documentElement.style.setProperty('--font',$('#font').value+'px');$('#font-value').textContent=$('#font').value+'px';});$('#width').addEventListener('input',()=>document.documentElement.style.setProperty('--code-width',$('#width').value+'%'));$('#reset').addEventListener('click',()=>{$('#search').value='';$('#scope').value='';$('#blank').checked=false;apply();});$('#sidebar').addEventListener('click',()=>{const closed=document.body.classList.toggle('collapsed');$('#sidebar').setAttribute('aria-expanded',String(!closed));});function reveal(){const row=document.getElementById(location.hash.slice(1));if(row&&row.classList.contains('line')){$('#search').value='';$('#scope').value='';apply();row.hidden=false;row.scrollIntoView({block:'center'});}}window.addEventListener('hashchange',reveal);$('#copy').addEventListener('click',async()=>{const status=$('#copy-status');try{if(!navigator.clipboard?.writeText)throw Error();await navigator.clipboard.writeText(data.source);status.textContent='전체 코드를 복사했습니다.';}catch{const field=$('#fallback');field.style.display='block';field.value=data.source;field.focus();field.select();let ok=false;try{ok=document.execCommand('copy');}catch{}if(ok){field.style.display='none';status.textContent='전체 코드를 복사했습니다.';}else{status.textContent='코드가 선택됐습니다. Ctrl+C로 복사하세요.';}}});apply();if(location.hash)reveal();})();
</script></body></html>'''
