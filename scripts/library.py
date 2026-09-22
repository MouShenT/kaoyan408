"""Build a page-addressable study library; extraction is never treated as verification."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def build(root):
    import pymupdf
    root = Path(root)
    catalog = []
    for path in sorted((root / 'materials').rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        key = hashlib.sha256(rel.encode()).hexdigest()[:12]
        item = dict(id=key, path=rel, title=path.stem, bytes=path.stat().st_size,
                    sha256=digest(path), provenance='user-provided; not authenticated as official',
                    human_verified=False, chunks=[])
        folder = root / 'knowledge' / key
        folder.mkdir(parents=True, exist_ok=True)
        pages = []
        if path.suffix.lower() == '.pdf':
            with pymupdf.open(path) as doc:
                item['pages'] = len(doc)
                item['bookmarks'] = [dict(level=t[0], title=t[1], pdf_page=t[2]) for t in doc.get_toc()]
                for number, page in enumerate(doc, 1):
                    content = page.get_text(sort=True).strip()
                    method = 'text-layer' if len(content) >= 40 else 'needs-visual-check'
                    confidence = None
                    cache = root / '.cache' / 'ocr' / key / f'{number:04}.json'
                    if method == 'needs-visual-check' and cache.exists():
                        cached = json.loads(cache.read_text(encoding='utf-8'))
                        if cached.get('source_sha256') == item['sha256']:
                            content = cached['text']
                            method = 'ocr-unverified' if content else 'blank-or-unreadable'
                            confidence = cached['mean_confidence']
                    pages.append(dict(pdf_page=number, method=method, chars=len(content), confidence=confidence))
                    pages[-1]['text'] = content
            item['extraction'] = {s:sum(p['method']==s for p in pages) for s in sorted({p['method'] for p in pages})}
            for start in range(0, len(pages), 6):
                group = pages[start:start+6]
                target = folder / f'p{start+1:04}-{start+len(group):04}.md'
                content = f'# {path.stem}\n\n原文件：[{path.name}](../../{quote(rel)})\n\n'
                content += '以下为机器提取，未人工校对；公式、上下标、图表、选项和答案必须对照原页。PDF 页码从 1 开始，不等于印刷页码。\n\n'
                for page in group:
                    content += f'## PDF 第 {page["pdf_page"]} 页\n\n提取方式：{page["method"]}\n\n{page["text"] or "[本页无可用文本，请查看原 PDF 或用户照片。]"}\n\n'
                target.write_text(content, encoding='utf-8')
                item['chunks'].append(target.relative_to(root).as_posix())
            save(folder / 'pages.json', [{k:v for k,v in p.items() if k != 'text'} for p in pages])
        elif path.suffix.lower() == '.json':
            original = json.loads(path.read_text(encoding='utf-8-sig'))
            item['questions'] = len(original.get('questions', []))
            for q in original.get('questions', []):
                target = folder / f'q{q["index"]:02}.md'
                body = f'# {original.get("year", "")} 年 {original.get("paper", "")} 第 {q["index"]} 题\n\n'
                body += f'来源：[{path.name}](../../{quote(rel)})，JSON index={q["index"]}。用户资料，题目及解析均未核验为官方版本。\n\n'
                for name, value in q.items():
                    if name in ('id','paper','year','index'):
                        continue
                    if isinstance(value, dict):
                        value = '\n'.join(f'{k}: {v}' for k,v in value.items())
                    if isinstance(value, list):
                        value = '\n'.join(f'- {v}' for v in value)
                    body += f'## {name}\n\n{value}\n\n'
                target.write_text(body, encoding='utf-8')
                item['chunks'].append(target.relative_to(root).as_posix())
        index = f'# {path.stem}\n\n资料编号：`{key}`\n\n原件：[下载 / 查看](../../{quote(rel)})\n\nSHA-256：`{item["sha256"]}`\n\n'
        index += '## 可检索内容\n\n' + '\n'.join(f'- [{Path(c).name}]({Path(c).name})' for c in item['chunks'])
        index += '\n\n## 原书书签（PDF 页码）\n\n'
        index += '\n'.join(f'- {b["title"]} → PDF {b["pdf_page"]}' for b in item.get('bookmarks', []))
        (folder / 'README.md').write_text(index + '\n', encoding='utf-8')
        catalog.append(item)
        print(f'Indexed {path.name}: {item.get("extraction", item.get("questions", 0))}', flush=True)
    save(root / 'catalog' / 'materials.json', catalog)
    table = '# 资料目录\n\n所有原件均为用户提供；文件名年份及“答案”字样不代表官方认证。\n\n| 资料 | 页数 / 题数 | 提取状态 |\n|---|---:|---|\n'
    for c in catalog:
        table += f'| [{c["title"]}](../knowledge/{c["id"]}/README.md) | {c.get("pages", c.get("questions", ""))} | {c.get("extraction", "结构化题库，未核验")} |\n'
    (root / 'catalog' / 'README.md').write_text(table, encoding='utf-8')
    return catalog


def lookup(root, key):
    catalog = json.loads((root / 'catalog/materials.json').read_text(encoding='utf-8'))
    matches = [x for x in catalog if x['id'] == key or x['path'] == key]
    if len(matches) != 1:
        raise ValueError('Use a unique material ID or full catalog path')
    return matches[0]


def search(root, query, limit):
    words = [w.casefold() for w in query.split()]
    if not words:
        raise ValueError('Empty search')
    hits = []
    for path in (root / 'knowledge').rglob('*.md'):
        content = path.read_text(encoding='utf-8')
        score = sum(content.casefold().count(w) for w in words)
        if score:
            lines = [x[:240] for x in content.splitlines() if any(w in x.casefold() for w in words)][:3]
            hits.append(dict(path=path.relative_to(root).as_posix(), score=score, snippets=lines))
    return sorted(hits, key=lambda x:(-x['score'],x['path']))[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('build')
    p = sub.add_parser('search'); p.add_argument('query'); p.add_argument('--limit', type=int, default=8)
    p = sub.add_parser('page'); p.add_argument('material'); p.add_argument('page', type=int)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.root)
    elif args.command == 'search':
        print(json.dumps(search(args.root,args.query,args.limit), ensure_ascii=False, indent=2))
    else:
        import pymupdf
        item = lookup(args.root, args.material)
        with pymupdf.open(args.root / item['path']) as doc:
            if not 1 <= args.page <= len(doc):
                raise ValueError('PDF page out of range')
            target = args.root / '.cache' / f'{item["id"]}-p{args.page}.png'
            target.parent.mkdir(parents=True, exist_ok=True)
            doc[args.page-1].get_pixmap(dpi=140).save(target)
            print(target.resolve())


if __name__ == '__main__':
    main()
