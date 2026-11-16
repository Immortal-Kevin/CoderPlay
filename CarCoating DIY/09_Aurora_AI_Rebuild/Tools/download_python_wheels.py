import pathlib,json,urllib.request,concurrent.futures,hashlib,sys,time,re
root=pathlib.Path(__file__).resolve().parents[1];dest=root/'Tools/Wheels';dest.mkdir(exist_ok=True)
packages={'diffusers':'0.35.1','transformers':'4.57.1','numpy':'2.2.6','pillow':'12.0.0','safetensors':'0.6.2','tokenizers':'0.22.1','huggingface_hub':'0.36.0','regex':'2025.9.18','requests':'2.32.5','tqdm':'4.67.1','importlib_metadata':'8.7.0','filelock':'3.20.0','fsspec':'2025.9.0','packaging':'25.0','psutil':'7.1.0','pyyaml':'6.0.3','typing_extensions':'4.15.0','zipp':'3.23.0','colorama':'0.4.6','urllib3':'2.5.0','idna':'3.10','certifi':'2025.8.3','charset_normalizer':'3.4.3','hf_xet':'1.1.10','sympy':'1.14.0','mpmath':'1.3.0','networkx':'3.5','jinja2':'3.1.6','markupsafe':'3.0.3','setuptools':'80.9.0'}
def compatible(name):
 if not name.endswith('.whl'):return False
 if name.endswith('none-any.whl'):return True
 if not name.endswith('win_amd64.whl'):return False
 return 'cp312-cp312' in name or bool(re.search(r'cp3(7|8|9|10|11|12)-abi3',name))
def get_package(item):
 name,version=item
 with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json',timeout=45) as r:meta=json.load(r)
 files=[f for f in meta['urls'] if compatible(f['filename'])]
 if not files:raise RuntimeError('No wheel '+name)
 f=sorted(files,key=lambda x:('cp312-cp312' not in x['filename'],x['filename']))[0];p=dest/f['filename'];expected=f['digests']['sha256']
 if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==expected:return {'name':name,'file':p.name,'sha256':expected,'cached':True}
 size=f['size'];buf=bytearray(size)
 for start in range(0,size,1024*1024):
  end=min(size-1,start+1024*1024-1);error=None
  for attempt in range(4):
   try:
    req=urllib.request.Request(f['url']+f'?part={start}',headers={'Range':f'bytes={start}-{end}'})
    with urllib.request.urlopen(req,timeout=40) as r:data=r.read(end-start+2)
    if len(data)!=end-start+1:raise RuntimeError('Truncated '+str(len(data)))
    buf[start:end+1]=data;error=None;break
   except Exception as e:error=e
  if error:raise error
 actual=hashlib.sha256(buf).hexdigest()
 if actual!=expected:raise RuntimeError('HASH MISMATCH '+name)
 p.write_bytes(buf);print('WHEEL READY',name,size,flush=True);return {'name':name,'version':version,'file':p.name,'source':f['url'],'bytes':size,'sha256':actual,'matches':True,'license':meta['info'].get('license')}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
 for future in concurrent.futures.as_completed([pool.submit(get_package,x) for x in packages.items()]):
  try:results.append(future.result())
  except Exception as e:results.append({'error':str(e)});print('WHEEL ERROR',str(e),flush=True)
  (root/'09_Report/Python_Wheel_Source_Hashes.json').write_text(json.dumps(results,indent=2))
print('WHEEL DOWNLOAD COMPLETE',flush=True)
