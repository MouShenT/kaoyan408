import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import pymupdf

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import library
import tutor


class LibraryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  (self.root/'materials').mkdir()
  self.pdf=self.root/'materials/test.pdf'
  with pymupdf.open() as d:
   p=d.new_page();p.insert_text((30,50),'A calculus example with derivative and boundary conditions. '*2)
   d.new_page();d.set_toc([[1,'Chapter',1]]);d.save(self.pdf)

 def tearDown(self):self.temp.cleanup()

 def build(self):
  with contextlib.redirect_stdout(io.StringIO()):return library.build(self.root)

 def test_hash_pages_bookmarks_and_search(self):
  item=self.build()[0]
  self.assertEqual(item['sha256'],hashlib.sha256(self.pdf.read_bytes()).hexdigest())
  self.assertEqual(item['pages'],2)
  self.assertEqual(item['bookmarks'][0]['pdf_page'],1)
  self.assertEqual(item['extraction'],{'needs-visual-check':1,'text-layer':1})
  self.assertTrue(library.search(self.root,'derivative',3))
  chunk=(self.root/item['chunks'][0]).read_text(encoding='utf-8')
  self.assertIn('PDF 第 2 页',chunk)

 def test_ocr_requires_matching_source_hash(self):
  item=self.build()[0]
  cache=self.root/'.cache/ocr'/item['id']/'0002.json'
  library.save(cache,dict(source_sha256='outdated',text='Incorrect stale text',mean_confidence=.9))
  self.assertNotIn('ocr-unverified',self.build()[0]['extraction'])
  library.save(cache,dict(source_sha256=item['sha256'],text='New recognized content',mean_confidence=.8))
  self.assertEqual(self.build()[0]['extraction']['ocr-unverified'],1)

 def test_structured_question_provenance(self):
  library.save(self.root/'materials/paper.json',dict(year=2026,paper='数学一',questions=[dict(index=1,stem='x+1=2',answer='1')]))
  item=next(x for x in self.build() if x['path'].endswith('.json'))
  content=(self.root/item['chunks'][0]).read_text(encoding='utf-8')
  self.assertIn('JSON index=1',content);self.assertIn('未核验',content);self.assertIn('x+1=2',content)

 def test_unknown_material_and_empty_search_rejected(self):
  self.build()
  with self.assertRaises(ValueError):library.lookup(self.root,'missing')
  with self.assertRaises(ValueError):library.search(self.root,'   ',3)


class TutorTests(unittest.TestCase):
 def test_no_history_does_not_invent_weakness(self):
  self.assertEqual(tutor.feedback([],'积分')['actions'],[])

 def test_hinted_answers_are_not_independent_mastery(self):
  records=[];r=tutor.add(records,'积分','method','漏掉换元后的微分')
  tutor.review(records,r['id'],'hinted-correct');tutor.review(records,r['id'],'independent-correct')
  self.assertEqual(r['status'],'needs-check')
  tutor.review(records,r['id'],'independent-correct')
  self.assertEqual(r['status'],'provisionally-improved')
  tutor.review(records,r['id'],'incorrect')
  self.assertEqual(r['status'],'needs-check')

 def test_feedback_scoped_to_current_topic(self):
  r=[];tutor.add(r,'积分','calculation','符号抄错');tutor.add(r,'概率','concept','误判独立')
  f=tutor.feedback(r,'积分')
  self.assertEqual(f['observed_mistakes'],1);self.assertEqual(f['error_type'],'calculation')

 def test_invalid_records_rejected(self):
  with self.assertRaises(ValueError):tutor.add([],'','concept','evidence')
  with self.assertRaises(ValueError):tutor.add([],'topic','invented','evidence')
  with self.assertRaises(ValueError):tutor.review([],'missing','incorrect')

if __name__=='__main__':unittest.main()
