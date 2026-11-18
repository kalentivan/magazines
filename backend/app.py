"""Private SQLite lead receiver. Put behind TLS reverse proxy; never serve DB files."""
import argparse
import hashlib
import hmac
import json
import os
import re
import sqlite3
import uuid
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import time

SCHEMA = '''CREATE TABLE IF NOT EXISTS leads (
 id TEXT PRIMARY KEY, created_at INTEGER NOT NULL, payload TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'new', notified_at INTEGER, consent_version TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS rate_limits (key TEXT PRIMARY KEY, window INTEGER NOT NULL, count INTEGER NOT NULL);'''

class LeadStore:
    def __init__(self, path, rate_secret, consent_version='review-required', limit=10):
        self.path, self.secret, self.version, self.limit = str(path), rate_secret.encode(), consent_version, limit
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)
            if 'notified_at' not in {r[1] for r in db.execute('PRAGMA table_info(leads)')}:
                db.execute('ALTER TABLE leads ADD COLUMN notified_at INTEGER')
        os.chmod(path, 0o600)
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return db
    def save(self, data, ip):
        now = int(time.time()); window = now // 600
        key = hmac.new(self.secret, f'{window}:{ip}'.encode(), hashlib.sha256).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM rate_limits WHERE window < ?', (window,))
            row = db.execute('SELECT count FROM rate_limits WHERE key=?', (key,)).fetchone()
            if row and row[0] >= self.limit: raise OverflowError('rate_limited')
            db.execute('INSERT INTO rate_limits VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET count=count+1', (key,window))
            payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
            old = db.execute('SELECT payload FROM leads WHERE id=?',(data['request_id'],)).fetchone()
            if old:
                if old[0] != payload: raise FileExistsError('id_conflict')
                return data['request_id']
            db.execute('INSERT INTO leads(id,created_at,payload,consent_version) VALUES(?,?,?,?)',(data['request_id'],now,payload,self.version))
        return data['request_id']

def validate(raw):
    if not isinstance(raw, dict): raise ValueError('invalid_object')
    limits={'name':80,'contact':160,'message':2000,'company':160,'quantity':6,'occasion_date':10,'website':200,'request_id':36,'lead_type':3}
    clean={}
    for key,limit in limits.items():
        value=raw.get(key,'')
        if not isinstance(value,str) or len(value)>limit or '\x00' in value: raise ValueError('invalid_'+key)
        clean[key]=value.strip()
    if clean['website']: raise ValueError('spam')
    if clean['lead_type'] not in ('b2c','b2b'): raise ValueError('invalid_type')
    if len(clean['name'])<2 or raw.get('consent') is not True: raise ValueError('name_or_consent')
    if clean['lead_type']=='b2b' and (not clean['company'] or not clean['message']): raise ValueError('company_or_message')
    c=clean['contact']; digits=re.sub(r'\D','',c)
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',c) and not (re.fullmatch(r'[+\d\s().-]+',c) and 10<=len(digits)<=15): raise ValueError('invalid_contact')
    if clean['quantity'] and (not clean['quantity'].isdigit() or not 1<=int(clean['quantity'])<=100000): raise ValueError('invalid_quantity')
    if clean['occasion_date']: date.fromisoformat(clean['occasion_date'])
    if str(uuid.UUID(clean['request_id'])) != clean['request_id']: raise ValueError('invalid_request_id')
    clean['consent']=True
    return clean

class LeadServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self, address, store, origins):
        self.store, self.origins=store,set(origins)
        super().__init__(address, Handler)

class Handler(BaseHTTPRequestHandler):
    server_version='LeadReceiver'
    def setup(self):
        super().setup(); self.connection.settimeout(10)
    def log_message(self,*args): pass  # No raw requests, IPs, contacts, or payloads in logs.
    def reply(self, code, data):
        body=json.dumps(data).encode()
        self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(body))); self.send_header('Vary','Origin')
        origin=self.headers.get('Origin')
        if origin in self.server.origins: self.send_header('Access-Control-Allow-Origin',origin)
        self.end_headers(); self.wfile.write(body)
    def do_OPTIONS(self):
        if self.path!='/leads' or self.headers.get('Origin') not in self.server.origins:
            return self.reply(403,{'error':'origin_denied'})
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin',self.headers['Origin'])
        self.send_header('Access-Control-Allow-Methods','POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.send_header('Vary','Origin'); self.end_headers()
    def do_GET(self):
        self.reply(200 if self.path=='/health' else 404, {'ok':True} if self.path=='/health' else {'error':'not_found'})
    def do_POST(self):
        trace=str(uuid.uuid4())
        if self.path!='/leads': return self.reply(404,{'error':'not_found','request_id':trace})
        if self.headers.get('Origin') not in self.server.origins: return self.reply(403,{'error':'origin_denied','request_id':trace})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.reply(415,{'error':'json_required','request_id':trace})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>16384: return self.reply(413,{'error':'body_size','request_id':trace})
            data=validate(json.loads(self.rfile.read(size)))
            lead_id=self.server.store.save(data,self.client_address[0])
            self.reply(201,{'saved':True,'lead_id':lead_id})
        except (ValueError,TypeError,UnicodeError): self.reply(422,{'error':'invalid_fields','request_id':trace})
        except OverflowError: self.reply(429,{'error':'rate_limited','request_id':trace})
        except FileExistsError: self.reply(409,{'error':'id_conflict','request_id':trace})
        except (sqlite3.Error,OSError): self.reply(503,{'error':'storage_unavailable','request_id':trace})

def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8080);p.add_argument('--host',default='127.0.0.1');a=p.parse_args()
    if os.environ.get('LEADS_ENABLED')!='true': raise SystemExit('Set LEADS_ENABLED=true only after policy and storage approval.')
    secret=os.environ.get('RATE_SECRET','');version=os.environ.get('CONSENT_VERSION','')
    if len(secret)<32 or not version: raise SystemExit('RATE_SECRET (32+ chars) and CONSENT_VERSION required.')
    store=LeadStore(os.environ.get('LEADS_DB','/data/leads.sqlite3'),secret,version)
    server=LeadServer((a.host,a.port),store,os.environ.get('ALLOWED_ORIGINS','https://kalentivan.github.io').split(','))
    server.serve_forever()
if __name__=='__main__':main()
