import sys,pathlib,csv,json,re,time,traceback
sys.path.insert(0,str(pathlib.Path(__file__).parent/'python'))
import UnityPy
root=pathlib.Path(__import__('os').environ['SUBNAUTICA_DATA_DIR'])
out=pathlib.Path(__file__).resolve().parents[1]
files=list((root/'StreamingAssets/aa/StandaloneWindows64').glob('*.bundle'))+list(root.glob('*.assets'))+[root/'globalgamemanagers',root/'level0']
files.sort(key=lambda p: (0 if p.name.startswith(('aurora.unity','starship_souvenir','main.unity')) else 1,p.name))
pattern=re.compile(r'aurora|alterra|starship|crash|spaceship|ship_exterior',re.I)
with (out/'06_Reports/Asset_Object_Index.csv').open('w',newline='',encoding='utf-8-sig') as f,(out/'06_Reports/Scan_Errors.jsonl').open('w',encoding='utf8') as err:
 w=csv.writer(f);w.writerow(['bundle','serialized_file','unity_version','path_id','type','name','bytes','candidate'])
 for i,p in enumerate(files):
  try:
   env=UnityPy.load(str(p)); count=0
   for o in env.objects:
    if o.type.name not in ['Mesh','GameObject','Texture2D','Material','Sprite','AssetBundle','MonoBehaviour']:continue
    try:name=o.peek_name() or ''
    except:name=''
    hit=bool(pattern.search(name))
    w.writerow([str(p),o.assets_file.name,o.assets_file.unity_version,o.path_id,o.type.name,name,o.byte_size,hit]);count+=1
   f.flush()
   if i%100==0 or p.name.startswith(('aurora.unity','starship_souvenir','main.unity')):print(i,len(files),p.name,count,flush=True)
  except Exception as e:err.write(json.dumps({'file':str(p),'error':str(e)})+'\n');err.flush()
print('SCAN COMPLETE',flush=True)
