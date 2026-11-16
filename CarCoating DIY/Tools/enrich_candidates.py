import pathlib,sys,csv,json,collections
base=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(base/'Tools/python'))
import UnityPy
rows=list(csv.DictReader((base/'06_Reports/Candidate_Resources.csv').open(encoding='utf-8-sig')))
exports=json.loads((base/'06_Reports/Final_Export_Manifest.json').read_text(encoding='utf8'))
lookup={(r['source'],r['serialized'],str(r['path_id'])):r for r in exports};groups=collections.defaultdict(list)
for r in rows:groups[r['bundle']].append(r)
for path,items in groups.items():
 env=UnityPy.load(path);objects={(o.assets_file.name,str(o.path_id)):o for o in env.objects}
 for r in items:
  rec=lookup.get((path,r['serialized_file'],r['path_id']));r['export_status']='已导出' if rec else '已索引，未导出';r['output']=rec.get('output','') if rec else '';r['dimensions']='不适用（非图像/网格）'
  if r['type'] not in ['Mesh','Texture2D','Sprite']:continue
  try:
   d=objects[(r['serialized_file'],r['path_id'])].read()
   if r['type']=='Texture2D':r['dimensions']=f'{d.m_Width}x{d.m_Height}'
   elif r['type']=='Mesh':
    bounds=d.m_LocalAABB.m_Extent;r['dimensions']=f'AABB size {bounds.x*2:.6g} x {bounds.y*2:.6g} x {bounds.z*2:.6g} (mesh local units); submeshes {len(d.m_SubMeshes)}'
   else:r['dimensions']=f'{d.m_Rect.width}x{d.m_Rect.height}'
  except Exception as e:r['dimensions']='读取失败: '+str(e)
with (base/'06_Reports/Candidate_Resource_Status.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('enriched',len(rows),'candidates','dimension errors',sum(r['dimensions'].startswith('读取失败') for r in rows))
