import sys,pathlib,csv,json,re,hashlib
base=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(base/'Tools/python'))
import UnityPy
from UnityPy.export.MeshExporter import export_mesh_obj
rows=list(csv.DictReader((base/'06_Reports/Asset_Object_Index.csv').open(encoding='utf-8-sig')))
lookup={r['serialized_file'].lower():r['bundle'] for r in rows};env=UnityPy.Environment();loaded=set();provenance=[]
def load(p):
 if p not in loaded:env.load_file(p);loaded.add(p)
def resolve(ptr):
 if ptr.m_FileID:
  name=ptr.assetsfile.externals[ptr.m_FileID-1].path.rsplit('/',1)[-1].lower()
  if name in lookup:load(lookup[name])
 return ptr.deref()
def safe(n):return re.sub(r'[^\w.\-]','_',n)
for model in ['starship_crashed','starship_souvenir','starship_exploded_exterior']:
 row=next(r for r in rows if r['type']=='Mesh' and r['name']==model);load(row['bundle'])
 mesh=next(o for o in env.objects if o.type.name=='Mesh' and o.path_id==int(row['path_id']) and o.assets_file.name==row['serialized_file'])
 # Find renderer via mesh filter in the same source bundle.
 renderer=None
 for o in list(env.objects):
  if o.type.name!='MeshFilter':continue
  d=o.read()
  if d.m_Mesh.m_PathID!=mesh.path_id:continue
  try:
   if resolve(d.m_Mesh).assets_file.name!=mesh.assets_file.name:continue
   go=resolve(d.m_GameObject).read()
   for comp in go.m_Component:
    ptr=comp.component if hasattr(comp,'component') else comp[1]
    obj=resolve(ptr)
    if obj.type.name=='MeshRenderer':renderer=obj.read();break
  except Exception:continue
  if renderer:break
 if not renderer:raise RuntimeError('renderer missing '+model)
 dest=base/'02_Models'/model;dest.mkdir(parents=True,exist_ok=True);mats=[]
 for idx,ptr in enumerate(renderer.m_Materials):
  mo=resolve(ptr);mat=mo.read();tree=mo.read_typetree();rec={'name':f'mat_{idx:02d}_{safe(mat.m_Name)}','original_name':mat.m_Name,'textures':{},'colors':dict(tree['m_SavedProperties']['m_Colors']),'floats':dict(tree['m_SavedProperties']['m_Floats'])}
  for key,te in mat.m_SavedProperties.m_TexEnvs:
   if not te.m_Texture:continue
   if key not in ['_MainTex','_BumpMap','_SpecTex','_Illum','_EmissionMap','_SpecGlossMap']:continue
   try:
    texobj=resolve(te.m_Texture);tex=texobj.read();name=f'{safe(tex.m_Name)}__{texobj.path_id}.png';path=dest/name
    if not path.exists():tex.image.save(path)
    rec['textures'][key]={'file':name,'scale':[te.m_Scale.x,te.m_Scale.y],'offset':[te.m_Offset.x,te.m_Offset.y],'width':tex.m_Width,'height':tex.m_Height}
    provenance.append({'model':model,'material':mat.m_Name,'slot':key,'texture':tex.m_Name,'path_id':texobj.path_id,'serialized_file':texobj.assets_file.name,'source':lookup.get(texobj.assets_file.name.lower()),'output':str(path)})
   except Exception as e:rec.setdefault('errors',[]).append(f'{key}: {e}')
  mats.append(rec)
 (dest/(model+'.obj')).write_text(export_mesh_obj(mesh.read(),[m['name'] for m in mats]),encoding='utf8')
 (dest/'materials.json').write_text(json.dumps(mats,ensure_ascii=False,indent=2),encoding='utf8')
 (dest/'source.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf8')
 print(model,'materials',len(mats),'textures',sum(len(m['textures']) for m in mats),flush=True)
(base/'06_Reports/Model_Texture_Provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf8')
