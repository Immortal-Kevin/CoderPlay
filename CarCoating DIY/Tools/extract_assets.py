import sys,pathlib,csv,json,re,hashlib
base=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(base/'Tools/python'))
import UnityPy
from UnityPy.export.MeshExporter import export_mesh_obj
rows=list(csv.DictReader((base/'06_Reports/Asset_Object_Index.csv').open(encoding='utf-8-sig')))
selected={r['bundle'] for r in rows if (r['type']=='Mesh' and r['name'] in ['starship_crashed','starship_exploded_exterior','starship_souvenir','poster_aurora']) or (r['type']=='Texture2D' and r['name']=='starship_crashed')}
manifest=[];errors=[]
for path in sorted(selected):
 env=UnityPy.load(path);tag=pathlib.Path(path).stem;dest=base/'01_SourceAssets'/'Verified_Exports'/tag;dest.mkdir(exist_ok=True,parents=True)
 (dest/'source.json').write_text(json.dumps({'source':path,'sha256':hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()},indent=2),encoding='utf8')
 for obj in env.objects:
  if obj.type.name not in ['Mesh','Texture2D','Material','MeshRenderer','MeshFilter','Transform','GameObject']:continue
  try:
   dest=base/'01_SourceAssets'/'Verified_Exports'/tag/re.sub(r'[^\w.\-]','_',obj.assets_file.name);dest.mkdir(exist_ok=True,parents=True)
   d=obj.read();name=getattr(d,'m_Name','') or obj.type.name
   safe=re.sub(r'[^\w.\-]','_',name);stem=f'{safe}__{obj.path_id}'
   rec={'source':path,'serialized':obj.assets_file.name,'path_id':obj.path_id,'type':obj.type.name,'name':name}
   if obj.type.name=='Mesh':
    p=dest/(stem+'.obj');p.write_text(export_mesh_obj(d),encoding='utf8');rec.update(vertices=d.m_VertexCount,submeshes=len(d.m_SubMeshes))
   elif obj.type.name=='Texture2D':
    p=dest/(stem+'.png');d.image.save(p);rec.update(width=d.m_Width,height=d.m_Height)
   else:
    p=dest/(stem+'.json');p.write_text(json.dumps(obj.read_typetree(),ensure_ascii=False,indent=2),encoding='utf8')
   rec['output']=str(p);manifest.append(rec)
  except Exception as e:errors.append({'source':path,'id':obj.path_id,'type':obj.type.name,'error':str(e)})
 print(tag,len(manifest),'errors',len(errors),flush=True)
(base/'06_Reports/Verified_Export_Manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
(base/'06_Reports/Verified_Export_Errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2),encoding='utf8')
