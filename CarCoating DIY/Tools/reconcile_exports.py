import pathlib,json,csv,re
base=pathlib.Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((base/'06_Reports/Asset_Object_Index.csv').open(encoding='utf-8-sig')))
manifest=json.loads((base/'06_Reports/Verified_Export_Manifest.json').read_text(encoding='utf8'))
errors=json.loads((base/'06_Reports/Verified_Export_Errors.json').read_text(encoding='utf8'))
fixed=[];unresolved=[]
for err in errors:
 source=err['source'];tag=pathlib.Path(source).stem
 hits=list((base/'01_SourceAssets/Verified_Exports'/tag).rglob(f'*__{err["id"]}.obj'))
 if hits:
  p=hits[0];lines=p.read_text().splitlines();v=sum(l.startswith('v ') for l in lines);f=sum(l.startswith('f ') for l in lines)
  if v and f:
   row=next((r for r in rows if r['bundle']==source and r['path_id']==str(err['id']) and r['type']=='Mesh'),{})
   rec={'source':source,'serialized':row.get('serialized_file'),'path_id':err['id'],'type':'Mesh','name':row.get('name'),'output':str(p),'vertices':v,'triangles':f,'status':'verified OBJ; metadata access error corrected'};manifest.append(rec);fixed.append(rec);continue
 unresolved.append(err)
(base/'06_Reports/Final_Export_Manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
(base/'06_Reports/Unresolved_Export_Errors.json').write_text(json.dumps(unresolved,ensure_ascii=False,indent=2),encoding='utf8')
print('Exported records',len(manifest),'Mesh corrected',len(fixed),'Unresolved',len(unresolved))
print('Object index rows',len(rows),'candidates',sum(r['candidate']=='True' for r in rows))
print('Candidate meshes',sum(r['candidate']=='True' and r['type']=='Mesh' for r in rows))
