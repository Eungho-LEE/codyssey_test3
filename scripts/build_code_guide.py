"""Render only fully reviewed source lines, without executing main.py."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from code_guide_view import render

ROOT = Path(__file__).resolve().parents[1]


class GuideInspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.line_ids = []
        self.references = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                raise ValueError('Duplicate HTML id: ' + attrs['id'])
            self.ids.add(attrs['id'])
        if tag == 'div' and 'line' in attrs.get('class', '').split():
            self.line_ids.append(attrs['id'])
        if attrs.get('href', '').startswith('#L'):
            self.references.append(attrs['href'][1:])


def main():
    raw = (ROOT / 'main.py').read_bytes()
    source = raw.decode('utf-8-sig')
    digest = hashlib.sha256(raw).hexdigest()
    notes = json.loads((ROOT / 'scripts/line_annotations.json').read_text(encoding='utf-8'))
    if notes['sha256'] != digest:
        raise SystemExit('main.py changed. Review line_annotations.json against the new source before generating.')
    lines, rows = source.splitlines(), notes['rows']
    if len(rows) != len(lines):
        raise ValueError('Source and annotation line counts differ')
    for number, (line, row) in enumerate(zip(lines, rows), 1):
        if row['number'] != number or row['code'] != line:
            raise ValueError('Annotation source mismatch at line ' + str(number))
        if line.strip() and (not row['meaning'].strip() or not row['detail'].strip()):
            raise ValueError('Missing explanation at line ' + str(number))
    page = render(source, rows, notes['mission'], digest, notes['date'])
    inspection = GuideInspector()
    inspection.feed(page)
    if inspection.line_ids != ['L' + str(n) for n in range(1, len(lines) + 1)]:
        raise ValueError('HTML line order/count mismatch')
    if not all(ref in inspection.ids for ref in inspection.references):
        raise ValueError('Broken function or line link')
    payload_start = page.index('<script type="application/json" id="source-data">')
    embedded = page[payload_start:].split('>', 1)[1].split('</script>', 1)[0]
    if json.loads(embedded)['source'] != source:
        raise ValueError('Copy-button source differs from main.py')
    output = ROOT / 'docs/code/main_line_by_line.html'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding='utf-8')
    snapshot = dict(date=notes['date'], source='main.py', sha256=digest,
                    lineCount=len(lines), annotatedRows=len(rows),
                    nonblankRows=sum(bool(line.strip()) for line in lines),
                    bonusRows=sum(row.get('bonus', False) for row in rows),
                    includesBonus=True)
    (output.parent / 'source_snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Keep the user's existing local entry points in sync with the canonical guide.
    aliases = []
    if ROOT.parent.name in ('No2_E1-2', 'No3_E1-3'):
        aliases.append(ROOT.parent / 'main_라인별_설명.html')
    if ROOT.parent.name == 'No3_E1-3':
        aliases += [ROOT.parent / 'code-guide/main_line_by_line.html']
        (ROOT.parent / 'code-guide').mkdir(parents=True, exist_ok=True)
        (ROOT.parent / 'code-guide/source_snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for alias in aliases:
        alias.parent.mkdir(parents=True, exist_ok=True)
        alias.write_text(page, encoding='utf-8')
    if (ROOT / 'main.py').read_bytes() != raw:
        raise ValueError('Source changed during generation')
    report = dict(snapshot, sourceUnchanged=True, sourceCopyMatches=True,
                  allLinesExplained=True, functionLinksValid=True,
                  htmlAliasesMatch=all(alias.read_bytes() == output.read_bytes() for alias in aliases))
    (output.parent / 'guide-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
