from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
root=Path(__file__).resolve().parents[1]
class Doc(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=set();self.h1=0;self.title=False;self.description=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.add(a['id'])
  if tag=='h1':self.h1+=1
  if tag=='title':self.title=True
  if tag=='meta' and a.get('name')=='description':self.description=True
  if tag in ['a','link','script','img']:
   value=a.get('href',a.get('src',''))
   if value:self.links.append(value)
errors=[];count=0
for rel in ['index.html','hotels/index.html','privacy/index.html']:
 path=root/rel;d=Doc();d.feed(path.read_text())
 if d.h1!=1 or not d.title or not d.description:errors.append(f'{rel}: SEO headings')
 for link in d.links:
  u=urlsplit(link)
  if u.scheme or u.netloc:continue
  dest=(path.parent/unquote(u.path)).resolve() if u.path else path
  if dest.is_dir():dest=dest/'index.html'
  if not dest.exists():errors.append(f'{rel}: missing {link}');continue
  if u.fragment and dest.suffix=='.html':
   target=Doc();target.feed(dest.read_text())
   if u.fragment not in target.ids:errors.append(f'{rel}: missing anchor {link}')
  count+=1
# Legacy routes and original assets must still exist.
for rel in ['world.html','dreams.html','dream.html','kids.html','art.html','dev/world.html','dev/kids.html','policy/index.html']:
 if not (root/rel).is_file():errors.append(f'Missing legacy route {rel}')
print(f'Checked {count} local references; {len(errors)} errors')
for e in errors:print(e)
raise SystemExit(bool(errors))
