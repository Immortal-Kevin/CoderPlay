import bpy,bmesh,pathlib,json
root=pathlib.Path(__file__).resolve().parents[1];src=root.parent/'07_IonThrusters/01_Blender/Aurora_IonThrusters_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(src));obj=next(o for o in bpy.data.collections['Original_Ship_UNMODIFIED'].objects if o.type=='MESH')
data={'source':str(src),'vertices':[list(v.co) for v in obj.data.vertices],'faces':[list(p.vertices) for p in obj.data.polygons],'normals':[list(p.normal) for p in obj.data.polygons],'uv':[list(u.uv) for u in obj.data.uv_layers.active.data],'loops':[list(p.loop_indices) for p in obj.data.polygons]}
bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bm.verts.ensure_lookup_table();seen=set();components=[]
for v in bm.verts:
 if v in seen:continue
 stack=[v];seen.add(v);vs=[]
 while stack:
  a=stack.pop();vs.append(a)
  for e in a.link_edges:
   other=e.other_vert(a)
   if other not in seen:seen.add(other);stack.append(other)
 components.append({'verts':len(vs),'min':[min(v.co[i] for v in vs) for i in range(3)],'max':[max(v.co[i] for v in vs) for i in range(3)]})
data['components']=sorted(components,key=lambda c:-c['verts']);data['welded_vertices']=len(bm.verts);data['faces_count']=len(obj.data.polygons);bm.free()
(root/'06_Report/Original_Topology.json').write_text(json.dumps(data));print(json.dumps({'vertices':len(data['vertices']),'faces':len(data['faces']),'welded_vertices':data['welded_vertices'],'components':data['components'][:30]},indent=2))
