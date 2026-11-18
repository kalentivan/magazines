import json,tempfile,unittest,uuid
from pathlib import Path
from backend.app import LeadStore,validate
from backend.notify import deliver
class NotificationTests(unittest.TestCase):
 def test_failure_retains_lead_and_retry_has_no_private_fields(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'test.sqlite3';store=LeadStore(path,'x'*32,'qa')
   store.save(validate(dict(name='Test',contact='qa@example.invalid',lead_type='b2c',request_id=str(uuid.uuid4()),consent=True)),'127.0.0.1')
   def fail(*a,**k):raise OSError('offline')
   self.assertEqual(deliver(path,'https://example.invalid','test',fail),0)
   with store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM leads WHERE notified_at IS NULL').fetchone()[0],1)
   class Reply:
    status=200
    def __enter__(self):return self
    def __exit__(self,*args):pass
   def ok(req,**kw):
    p=json.loads(req.data);self.assertEqual(set(p),{'event','lead_id','lead_type'});return Reply()
   self.assertEqual(deliver(path,'https://example.invalid','test',ok),1)
   self.assertEqual(deliver(path,'https://example.invalid','test',ok),0)
