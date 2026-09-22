"""Fast local OCR using installed Windows Chinese OCR; requires Windows PowerShell 5."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import pymupdf


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
 p.add_argument('--workers',type=int,default=3)
 a=p.parse_args()
 if os.name!='nt':p.error('Windows only; use ocr_library.py on other systems')
 if not 1<=a.workers<=8:p.error('workers must be between 1 and 8')
 root=a.root.resolve();jobs=[];renders=[]
 catalog=json.loads((root/'catalog/materials.json').read_text(encoding='utf-8'))
 for item in catalog:
  if not item['path'].lower().endswith('.pdf'):continue
  with pymupdf.open(root/item['path']) as doc:
   for number,page in enumerate(doc,1):
    if len(page.get_text().strip())>=40:continue
    target=root/'.cache/ocr'/item['id']/f'{number:04}.json'
    if target.exists():
     if json.loads(target.read_text(encoding='utf-8')).get('source_sha256')==item['sha256']:continue
    image=root/'.cache/windows-images'/item['id']/item['sha256'][:12]/f'{number:04}.png'
    jobs.append(dict(image=str(image),output=str(target),sha256=item['sha256'],page=number))
    renders.append((root/item['path'],number,image))
 if not jobs:
  print('All eligible pages already have OCR cache.');return
 processes=[];streams=[]
 try:
  for i in range(a.workers):
   file=root/f'.cache/windows-jobs-{i}.json';file.parent.mkdir(parents=True,exist_ok=True)
   file.write_text(json.dumps(jobs[i::a.workers]),encoding='utf-8')
   stream=(root/f'.cache/windows-ocr-{i}.log').open('w');streams.append(stream)
   processes.append(subprocess.Popen(['powershell.exe','-NoProfile','-File',str(root/'scripts/ocr_windows.ps1'),'-JobsFile',str(file)],stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW))
  last=None;doc=None
  try:
   for i,(path,number,image) in enumerate(renders,1):
    if last!=path:
     if doc:doc.close()
     doc=pymupdf.open(path);last=path
    image.parent.mkdir(parents=True,exist_ok=True)
    if not Path(str(image)+'.ready').exists():
     doc[number-1].get_pixmap(dpi=140,colorspace=pymupdf.csRGB,alpha=False).save(image)
     Path(str(image)+'.ready').touch()
    if i%100==0:print(f'Rendered {i}/{len(renders)}',flush=True)
  finally:
   if doc:doc.close()
  codes=[proc.wait() for proc in processes]
  if any(codes):raise RuntimeError('OCR failed; inspect .cache/windows-ocr-*.log')
  missing=[j for j in jobs if not Path(j['output']).exists()]
  if missing:raise RuntimeError(f'{len(missing)} OCR results missing')
  print(f'OCR complete: {len(jobs)} pages. Run library.py build to refresh knowledge.')
 finally:
  for proc in processes:
   if proc.poll() is None:proc.terminate();proc.wait()
  for stream in streams:stream.close()


if __name__=='__main__':main()
