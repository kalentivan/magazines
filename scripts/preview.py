"""Local preview. --test-leads enables synthetic-only durable test submissions."""
import argparse,json,sys,tempfile
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app import Handler, LeadStore
p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=4173);p.add_argument('--strictPort',action='store_true');p.add_argument('--test-leads',action='store_true');a=p.parse_args()
class Preview(SimpleHTTPRequestHandler):
 def do_GET(self):
  if a.test_leads and self.path.split('?')[0]=='/assets/site/config.js':
   content=f'window.MAGAZINES_CONFIG={{endpoint:"http://127.0.0.1:{a.port}/leads",privacyApproved:true}};'.encode()
   self.send_response(200);self.send_header('Content-Type','application/javascript');self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(content)
  else:super().do_GET()
 def do_POST(self):
  if a.test_leads:return Handler.do_POST(self)
  self.send_error(405)
 reply=Handler.reply
 def log_message(self,*args):pass
server=ThreadingHTTPServer((a.host,a.port),Preview)
if a.test_leads:
 server.store=LeadStore(Path(tempfile.gettempdir())/'magazines-qa-leads.sqlite3','synthetic-test-only-secret-32-characters','qa-only',limit=100)
 server.origins={f'http://127.0.0.1:{a.port}'}
server.serve_forever()
