import json, tempfile, threading, unittest, uuid, sqlite3
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from backend.app import LeadStore, LeadServer

class LeadTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'leads.sqlite3'
  self.store=LeadStore(self.path,'x'*32,'test-only',limit=10)
  self.server=LeadServer(('127.0.0.1',0),self.store,['https://kalentivan.github.io'])
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.url=f'http://127.0.0.1:{self.server.server_port}'
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
 def payload(self,kind='b2c'):
  return dict(request_id=str(uuid.uuid4()),name='QA Test',contact='qa@example.invalid',lead_type=kind,consent=True,company='Test hotel' if kind=='b2b' else '',message='Synthetic test',website='')
 def post(self,payload,origin='https://kalentivan.github.io',raw=None):
  req=Request(self.url+'/leads',data=raw or json.dumps(payload).encode(),headers={'Content-Type':'application/json','Origin':origin})
  try:r=urlopen(req)
  except HTTPError as e:r=e
  return r.status,json.load(r)
 def test_b2c_b2b_saved_and_reopened(self):
  for kind in ['b2c','b2b']:
   p=self.payload(kind);code,r=self.post(p);self.assertEqual(code,201);self.assertTrue(r['saved'])
  reopened=LeadStore(self.path,'x'*32,'test-only')
  with reopened.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM leads').fetchone()[0],2)
 def test_retry_deduplicates(self):
  p=self.payload();self.assertEqual(self.post(p),self.post(p))
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM leads').fetchone()[0],1)
 def test_changed_payload_same_id_conflict(self):
  p=self.payload();self.post(p);p['name']='Other test';self.assertEqual(self.post(p)[0],409)
 def test_invalid_fields(self):
  for patch in [{'contact':'bad'},{'consent':False},{'name':' '},{'name':'x'*81},{'lead_type':'xxx'},{'request_id':'bad'},{'website':'spam'},{'quantity':'0'},{'occasion_date':'not-a-date'},{'message':[]}]:
   p=self.payload();p.update(patch);self.assertEqual(self.post(p)[0],422)
 def test_b2b_company_required(self):
  p=self.payload('b2b');p['company']='';self.assertEqual(self.post(p)[0],422)
 def test_origin_denied(self):self.assertEqual(self.post(self.payload(),'https://other.invalid')[0],403)
 def test_invalid_json(self):self.assertEqual(self.post({},raw=b'{bad')[0],422)
 def test_body_limit(self):self.assertEqual(self.post({},raw=b' '*17000)[0],413)
 def test_rate_limit(self):
  for _ in range(10):self.assertEqual(self.post(self.payload())[0],201)
  self.assertEqual(self.post(self.payload())[0],429)
 def test_private_read_not_exposed(self):
  for path in ['/leads','/leads.sqlite3','/admin']:
   with self.assertRaises(HTTPError) as c:urlopen(self.url+path)
   self.assertEqual(c.exception.code,404)
 def test_storage_error_never_success(self):
  self.store.path='/nonexistent/path/test.sqlite3';code,r=self.post(self.payload());self.assertEqual(code,503);self.assertNotIn('saved',r)
 def test_preflight(self):
  r=urlopen(Request(self.url+'/leads',method='OPTIONS',headers={'Origin':'https://kalentivan.github.io'}));self.assertEqual(r.status,204);self.assertEqual(r.headers['Access-Control-Allow-Origin'],'https://kalentivan.github.io')
if __name__=='__main__':unittest.main()
