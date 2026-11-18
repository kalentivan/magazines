"""Run periodically on server. Sends only lead ID/type; never contacts or message."""
import json,os,sqlite3,time
from urllib.request import Request,urlopen
from urllib.parse import urlparse

def deliver(db_path,url,token,transport=urlopen):
 if urlparse(url).scheme!='https':raise ValueError('HTTPS webhook required')
 sent=0
 with sqlite3.connect(db_path) as db:
  rows=db.execute('SELECT id,payload FROM leads WHERE notified_at IS NULL ORDER BY created_at LIMIT 100').fetchall()
  for lead_id,payload in rows:
   body=json.dumps({'event':'new_magazine_lead','lead_id':lead_id,'lead_type':json.loads(payload)['lead_type']}).encode()
   request=Request(url,data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+token,'Idempotency-Key':lead_id})
   try:
    with transport(request,timeout=10) as response:
     if not 200<=response.status<300:continue
    db.execute('UPDATE leads SET notified_at=? WHERE id=?',(int(time.time()),lead_id));db.commit();sent+=1
   except Exception:
    # Leave durable pending row. The next scheduled invocation retries it.
    continue
 return sent
if __name__=='__main__':
 url=os.environ.get('NOTIFY_WEBHOOK','');token=os.environ.get('NOTIFY_TOKEN','')
 if not url or not token:raise SystemExit('Set NOTIFY_WEBHOOK and NOTIFY_TOKEN on private server.')
 print('Notifications delivered:',deliver(os.environ.get('LEADS_DB','/data/leads.sqlite3'),url,token))
