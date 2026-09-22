"""Local OCR of pages without a text layer. Resumable; caches tied to source SHA."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import pymupdf
from rapidocr_onnxruntime import RapidOCR
from library import save


def run(root, limit=None, shard=0, shards=1):
    engine = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1, use_cls=False)
    count = 0
    started = time.monotonic()
    catalog = json.loads((root / 'catalog/materials.json').read_text(encoding='utf-8'))
    ordinal = 0
    for item in catalog:
        if not item['path'].lower().endswith('.pdf'):
            continue
        with pymupdf.open(root / item['path']) as doc:
            for n, page in enumerate(doc, 1):
                if len(page.get_text().strip()) >= 40:
                    continue
                ordinal += 1
                if (ordinal - 1) % shards != shard:
                    continue
                target = root / '.cache/ocr' / item['id'] / f'{n:04}.json'
                if target.exists():
                    prior = json.loads(target.read_text(encoding='utf-8'))
                    if prior.get('source_sha256') == item['sha256']:
                        continue
                pix = page.get_pixmap(dpi=120, colorspace=pymupdf.csRGB, alpha=False)
                array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height,pix.width,3)
                result, _ = engine(array)
                lines = result or []
                save(target, dict(source_sha256=item['sha256'], pdf_page=n,
                     text='\n'.join(r[1] for r in lines),
                     mean_confidence=sum(float(r[2]) for r in lines)/len(lines) if lines else 0,
                     engine='RapidOCR ONNX', dpi=120, human_verified=False))
                count += 1
                if count % 10 == 0 or count == 1:
                    print(f'{root.name}: {count} new pages, {time.monotonic()-started:.1f}s; {item["id"]} p{n}', flush=True)
                if limit and count >= limit:
                    return
    print(f'{root.name}: OCR complete, {count} new pages', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--limit', type=int)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--shards', type=int, default=1)
    args = p.parse_args()
    if args.shards < 1 or not 0 <= args.shard < args.shards:
        p.error('Require shards >= 1 and 0 <= shard < shards')
    run(args.root, args.limit, args.shard, args.shards)
