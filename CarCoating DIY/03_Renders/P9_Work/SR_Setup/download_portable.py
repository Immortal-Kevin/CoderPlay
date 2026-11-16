import pathlib,urllib.request,concurrent.futures,json,hashlib,zipfile,time
base=pathlib.Path(str(__import__('pathlib').Path(__file__).resolve().parents[3]));root=base/'Tools/P9_SuperResolution';report=base/'03_Renders/P9_Work/SR_Setup'
url='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip';size=45474481;chunk=1024*1024
def get(start):
 end=min(start+chunk,size)-1;p=root/f'part_{start:09d}.download'
 if p.exists() and p.stat().st_size==end-start+1:return p
 for attempt in range(4):
  try:
   req=urllib.request.Request(url+f'?part={start}',headers={'Range':f'bytes={start}-{end}'})
   with urllib.request.urlopen(req,timeout=45) as r:
    cr=r.headers.get('Content-Range','')
    if r.status!=206 or not cr.startswith(f'bytes {start}-{end}/'):raise RuntimeError(str(r.status)+' '+cr)
    data=r.read()
   if len(data)!=end-start+1:raise RuntimeError('truncated')
   p.write_bytes(data);print('PART',start,flush=True);return p
  except Exception as e:print('RETRY',start,attempt,str(e),flush=True);time.sleep(.3)
 raise RuntimeError('download failed '+str(start))
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:parts=list(pool.map(get,range(0,size,chunk)))
dest=root/'realesrgan_portable_verified.zip'
with dest.open('wb') as f:
 for p in parts:f.write(p.read_bytes())
with zipfile.ZipFile(dest) as z:
 bad=z.testzip()
 if bad:raise RuntimeError('Zip CRC failed '+bad)
 z.extractall(root/'portable')
record={'source':url,'publisher_size':size,'actual_size':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'publisher_digest':None,'verification':'Official GitHub HTTPS release; exact publisher file size and ZIP entry CRC checked; SHA256 recorded locally, no publisher SHA256 available','zip_crc_ok':True}
(report/'Portable_Verification.json').write_text(json.dumps(record,indent=2));print('PORTABLE EXTRACTED',flush=True)
