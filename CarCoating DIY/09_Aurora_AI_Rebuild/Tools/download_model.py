import pathlib,json,urllib.request,hashlib,time,concurrent.futures
root=pathlib.Path(__file__).resolve().parents[1];dest=root/'Tools/Models/TinySD';dest.mkdir(parents=True,exist_ok=True)
def getjson(url):
 with urllib.request.urlopen(url,timeout=60) as r:return json.load(r)
meta=getjson('https://huggingface.co/api/models/segmind/tiny-sd?blobs=true');sha=meta['sha'];(root/'09_Report/TinySD_Model_Metadata.json').write_text(json.dumps(meta,indent=2))
items=[f for f in meta['siblings'] if f['rfilename']=='model_index.json' or (f['rfilename'].startswith(('scheduler/','tokenizer/','text_encoder/','unet/','vae/')) and f['rfilename'].endswith(('.json','.txt','.bin','.safetensors')))]
def download(item):
 name=item['rfilename'];path=dest/name;path.parent.mkdir(parents=True,exist_ok=True);url=f'https://huggingface.co/segmind/tiny-sd/resolve/{sha}/{name}?download=true';expected=item.get('lfs',{}).get('sha256')
 if path.exists() and (not expected or hashlib.sha256(path.read_bytes()).hexdigest()==expected):return {'file':name,'cached':True,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 temp=path.with_suffix(path.suffix+'.part');t=time.time();h=hashlib.sha256();length=0
 with urllib.request.urlopen(url,timeout=120) as r,temp.open('wb') as f:
  while True:
   chunk=r.read(1024*1024)
   if not chunk:break
   f.write(chunk);h.update(chunk);length+=len(chunk)
   if length%(100*1024*1024)<1024*1024:print(name,round(length/1024/1024),'MB',flush=True)
 actual=h.hexdigest()
 if expected and actual!=expected:raise RuntimeError('HASH MISMATCH '+name)
 temp.rename(path);result={'file':name,'source':url,'revision':sha,'bytes':length,'sha256':actual,'expected_sha256':expected,'matches':not expected or expected==actual,'seconds':time.time()-t};print('DOWNLOADED',name,length,flush=True);return result
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for f in concurrent.futures.as_completed([pool.submit(download,item) for item in items]):
  try:results.append(f.result())
  except Exception as e:results.append({'error':str(e)});print('ERROR',str(e),flush=True)
  (root/'09_Report/TinySD_Download_Hashes.json').write_text(json.dumps(results,indent=2))
print('MODEL DOWNLOAD FINISHED',flush=True)
