"""Build static, prerendered art preview. Requires React 19 and esbuild in NODE_MODULES."""
from pathlib import Path
import os, tempfile, shutil, subprocess, json, re
root=Path(__file__).resolve().parents[1]
modules=Path(os.environ.get('NODE_MODULES',str(root/'node_modules'))).resolve()
base='/magazines/art-dev/'
source=root/'art-dev-source'; output=root/'art-dev'
with tempfile.TemporaryDirectory() as t:
 temp=Path(t); shutil.copytree(source,temp,dirs_exist_ok=True)
 (temp/'node_modules').symlink_to(modules,target_is_directory=True)
 for p in (temp/'app').glob('*.tsx'):
  s=p.read_text()
  s=re.sub(r'''(["'])/(?=[a-zA-Z])''',lambda m:m[1]+base,s)
  s=s.replace('href="/"', 'href="'+base+'"')
  p.write_text(s)
 p=temp/'data/artworks.json'; data=json.loads(p.read_text())
 for w in data:
  w['primary_image']=base+w['primary_image'].lstrip('/')
  w['images']=[base+x.lstrip('/') for x in w['images']]
 p.write_text(json.dumps(data,ensure_ascii=False))
 (temp/'navigation.ts').write_text('export function notFound():never {throw new Error("Page not found")}')
 (temp/'shell.tsx').write_text('''import React from 'react';import Home from './app/page';import Page from './app/detail';import {Header} from './app/ui';
export async function content(route:string){return <><a className="skip" href="#main">К содержанию</a><Header/><main id="main">{route?await Page({params:Promise.resolve({path:route.split('/')})}):<Home/>}</main><footer><a className="brand" href="BASE">Милена Дмитриева<small>ЖИВОПИСЬ И ГРАФИКА</small></a><div><a href="BASEworks/">Картины</a><a href="BASEabout/">О художнике</a></div><div><a href="BASEcontacts/">Контакты</a><a href="BASEprivacy/">Обращения</a></div><p>© Милена Дмитриева · Краснодар<br/>Предварительная версия каталога</p></footer></>}
'''.replace('BASE',base))
 (temp/'client.tsx').write_text("import React from 'react';import {hydrateRoot} from 'react-dom/client';import {content} from './shell';content(document.body.dataset.route||'').then(node=>hydrateRoot(document.getElementById('root')!,node));")
 (temp/'render.tsx').write_text("import React from 'react';import {renderToString} from 'react-dom/server';import {content} from './shell';export async function render(route:string){return renderToString(await content(route))}")
 build=[str(modules/'.bin/esbuild'),'--bundle','--jsx=automatic','--alias:next/navigation='+str(temp/'navigation.ts')]
 subprocess.run(build+[str(temp/'client.tsx'),'--minify','--define:process.env.NODE_ENV="production"','--outfile='+str(output/'app.js')],check=True)
 subprocess.run(build+[str(temp/'render.tsx'),'--platform=node','--format=esm','--packages=external','--outfile='+str(temp/'render.mjs')],check=True)
 routes=['','works','about','projects','for-business','contacts','privacy']+['works/'+w['slug'] for w in data if w['published']]
 (temp/'generate.mjs').write_text("import {render} from './render.mjs';import fs from 'node:fs';const routes="+json.dumps(routes)+";for(const r of routes){const html=await render(r);fs.writeFileSync("+json.dumps(str(temp))+"+'/page-'+routes.indexOf(r)+'.html',html)}")
 subprocess.run(['node',str(temp/'generate.mjs')],check=True)
 for i,route in enumerate(routes):
  dest=output/route;dest.mkdir(parents=True,exist_ok=True)
  html=(temp/f'page-{i}.html').read_text()
  title=next((w['title'] for w in data if route=='works/'+w['slug']),'Милена Дмитриева — живопись')
  (dest/'index.html').write_text(f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{title}</title><link rel="icon" href="{base}favicon.svg"><link rel="stylesheet" href="{base}style.css"></head><body data-route="{route}"><div id="root">{html}</div><script defer src="{base}app.js"></script></body></html>')
 shutil.copyfile(source/'app/globals.css',output/'style.css')
 print(f'Built {len(routes)} prerendered pages at {base}')
