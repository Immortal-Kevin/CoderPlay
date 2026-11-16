import pathlib,json,urllib.request,urllib.parse,concurrent.futures,threading,time,hashlib,re
root=pathlib.Path(__file__).resolve().parents[1];meta=json.loads((root/'09_Report/TinySD_Model_Metadata.json').read_text());jobs=[]
torch={'name':'torch-cpu-fallback','url':'https://download.pytorch.org/whl/cpu/torch-2.14.1%2Bcpu-cp312-cp312-win_amd64.whl','size':123996008,'sha256':'c52adc3bd526ff7fc5bdcc58fc4a76e6214d09951b646ffe5256ebd7ba60cef1','dest':str(root/'Tools/Wheels/torch-2.14.1+cpu-cp312-cp312-win_amd64.whl')};jobs.append(torch)
for f in meta['siblings']:
 if f['rfilename'].endswith('.bin'):
  jobs.append({'name':f['rfilename'],'url':f'https://huggingface.co/segmind/tiny-sd/resolve/{meta["sha"]}/{f["rfilename"]}?download=true','size':f['lfs']['size'],'sha256':f['lfs']['sha256'],'dest':str(root/'Tools/Models/TinySD'/f['rfilename'])})
chunk=1024*1024;locks={j['name']:threading.Lock() for j in jobs};state={};progress=threading.Lock();done=0
for job in jobs:
 p=pathlib.Path(job['dest']);p.parent.mkdir(parents=True,exist_ok=True);job['part']=str(p)+'.ranged';job['map']=str(p)+'.ranges.json'
 state[job['name']]=set(json.loads(pathlib.Path(job['map']).read_text())) if pathlib.Path(job['map']).exists() else set()
 if not pathlib.Path(job['part']).exists():
  with open(job['part'],'wb') as f:f.truncate(job['size'])
def fetch(job,start):
 global done
 if start in state[job['name']]:return True
 end=min(job['size']-1,start+chunk-1);expected=end-start+1;errors=[]
 for attempt in range(3):
  try:
   url=job['url']+('&' if '?' in job['url'] else '?')+f'part={start}'
   req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
   with urllib.request.urlopen(req,timeout=35) as r:
    cr=r.headers.get('Content-Range','')
    if r.status!=206 or not cr.startswith(f'bytes {start}-{end}/'):raise RuntimeError('Incorrect range '+str(r.status)+' '+cr)
    data=r.read(expected+1)
   if len(data)!=expected:raise RuntimeError(f'Truncated {len(data)}/{expected}')
   with locks[job['name']]:
    with open(job['part'],'r+b') as f:f.seek(start);f.write(data)
    state[job['name']].add(start);pathlib.Path(job['map']).write_text(json.dumps(sorted(state[job['name']])))
   with progress:
    done+=1
    if done%25==0:print('RANGE PROGRESS',done,'MB completed',job['name'],flush=True)
   return True
  except Exception as e:errors.append(str(e));time.sleep(.5)
 print('RANGE FAILED',job['name'],start,errors[-1],flush=True);return False
tasks=[(j,start) for j in jobs for start in range(0,j['size'],chunk)]
# Interleave model and runtime chunks, so no single large file blocks the rest.
tasks.sort(key=lambda t:t[1]);results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
 for future in concurrent.futures.as_completed([pool.submit(fetch,j,s) for j,s in tasks]):results.append(future.result())
verification=[]
for job in jobs:
 actual=hashlib.sha256(pathlib.Path(job['part']).read_bytes()).hexdigest();ok=actual==job['sha256'];verification.append({'name':job['name'],'expected_sha256':job['sha256'],'sha256':actual,'matches':ok,'bytes':job['size'],'completed_ranges':len(state[job['name']]),'path':job['dest']})
 if ok:
  dest=pathlib.Path(job['dest'])
  if not dest.exists():pathlib.Path(job['part']).rename(dest)
  print('VERIFIED COMPLETE',job['name'],flush=True)
 else:print('INCOMPLETE HASH',job['name'],flush=True)
(root/'09_Report/Segmented_Download_Verification.json').write_text(json.dumps(verification,indent=2));print('SEGMENTED RUN COMPLETE',flush=True)
