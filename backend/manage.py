"""Run on private server via SSH; output can contain personal data. Never commit exports."""
import argparse,json,sqlite3,time
p=argparse.ArgumentParser();p.add_argument('--db',required=True);sub=p.add_subparsers(dest='command',required=True)
sub.add_parser('list');s=sub.add_parser('show');s.add_argument('id');s=sub.add_parser('handled');s.add_argument('id');s=sub.add_parser('delete');s.add_argument('id');s=sub.add_parser('backup');s.add_argument('destination')
a=p.parse_args()
with sqlite3.connect(a.db) as db:
 if a.command=='list':
  for row in db.execute('SELECT id,created_at,status FROM leads ORDER BY created_at DESC'):print(*row)
 elif a.command=='show':
  row=db.execute('SELECT payload FROM leads WHERE id=?',(a.id,)).fetchone(); print(json.dumps(json.loads(row[0]),ensure_ascii=False,indent=2) if row else 'Not found')
 elif a.command=='handled':db.execute("UPDATE leads SET status='handled' WHERE id=?",(a.id,))
 elif a.command=='delete':db.execute('DELETE FROM leads WHERE id=?',(a.id,))
 elif a.command=='backup':
  import os
  with sqlite3.connect(a.destination) as backup:db.backup(backup)
  os.chmod(a.destination,0o600)
