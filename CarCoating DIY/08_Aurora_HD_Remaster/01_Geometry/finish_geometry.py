import bpy,bmesh,json,pathlib,math
from mathutils import Vector
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root/'01_Geometry/Aurora_RingRepair_Stage1.blend'));s=bpy.context.scene
obj=bpy.data.objects['Aurora_HD_Hull'];bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.normal_update();rings=json.loads((root/'06_Report/Ring_Repair.json').read_text())['rings']
base_edges=[]
for ring in rings:
 c=Vector(ring['center']);n=Vector(ring['normal']);r=ring['radius']
 def is_base(v):
  delta=v.co-c;return abs(delta.dot(n))<2e-6 and abs(delta.length-r)<2e-6
 edges=[e for e in bm.edges if all(is_base(v) for v in e.verts)]
 if edges:
  result=bmesh.ops.subdivide_edges(bm,edges=edges,cuts=10,use_grid_fill=False)
  for geom in result['geom_inner']+result['geom_split']:
   if isinstance(geom,bmesh.types.BMVert):
    d=geom.co-c
    if abs(d.dot(n))<3e-6 and d.length<r*1.01 and d.length>r*.93:geom.co=c+(d-n*d.dot(n)).normalized()*r
 base_edges.append({'side':ring['side'],'old_boundary_edges':len(edges),'new_boundary_segments':len(edges)*11})
bm.normal_update()
# Select curved body edges; keep high-angle armor/mechanical joints unchanged.
eligible=[];targets=[]
for e in bm.edges:
 if len(e.link_faces)!=2:continue
 mid=(e.verts[0].co+e.verts[1].co)/2
 if not(-.32<mid.y<.17 and abs(mid.x)>.025 and -.105<mid.z<.085):continue
 if any((mid-Vector(r['center'])).length<.045 for r in rings):continue
 angle=e.calc_face_angle(0)
 if .015<angle<math.radians(24) and e.calc_length()>.004:
  a,b=[v.co.copy() for v in e.verts];na,nb=[v.normal.copy() for v in e.verts]
  targets.append((a,b,na,nb));eligible.append(e)
if eligible:
 result=bmesh.ops.subdivide_edges(bm,edges=eligible,cuts=3,use_grid_fill=True)
 newverts={g for g in result['geom_inner']+result['geom_split'] if isinstance(g,bmesh.types.BMVert)}
 # Project edge subdivisions onto blended tangent planes (Phong tessellation).
 moved=0;maxmove=0
 for v in newverts:
  p=v.co.copy();best=None;distance=1e9
  for a,b,na,nb in targets:
   edge=b-a;fac=(p-a).dot(edge)/edge.length_squared
   if -.001<=fac<=1.001:
    dist=(p-(a+edge*fac)).length_squared
    if dist<distance:distance=dist;best=(a,b,na,nb,fac)
  if best and distance<1e-12:
   a,b,na,nb,t=best;pa=p-na*(p-a).dot(na);pb=p-nb*(p-b).dot(nb);delta=((pa*(1-t)+pb*t)-p)*.65
   if delta.length>.0007:delta*=.0007/delta.length
   v.co+=delta;moved+=1;maxmove=max(maxmove,delta.length)
else:moved=0;maxmove=0
bm.normal_update()
for e in bm.edges:e.smooth=not(len(e.link_faces)==2 and e.calc_face_angle(0)>math.radians(36))
bm.to_mesh(obj.data);bm.free()
for p in obj.data.polygons:p.use_smooth=True
def mat(name,color,metal,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
 n=m.node_tree.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=220;bum=m.node_tree.nodes.new('ShaderNodeBump');bum.inputs['Strength'].default_value=.12;bum.inputs['Distance'].default_value=.000015;m.node_tree.links.new(n.outputs['Fac'],bum.inputs['Height']);m.node_tree.links.new(bum.outputs['Normal'],bs.inputs['Normal']);return m
shell=mat('HD_Port_Gray_Alloy',(.12,.145,.16),.65,.32);disc=mat('HD_Port_Dark_Recess',(.008,.018,.023),.55,.3)
for ob in bpy.data.collections['HD_Remaster_Ship'].objects:
 if ob==obj:continue
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-9)
 if 'Starboard' in ob.name or ob.name.endswith('_-1'):bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bm.to_mesh(ob.data);bm.free()
 if ob.name.startswith('HD_Port_Ring') or ob.name.startswith('HD_Starboard_Ring'):
  ob.data.materials.clear();ob.data.materials.append(shell);ob.data.materials.append(disc)
  for p in ob.data.polygons:p.material_index=0 if p.index<640 else 1
 # Keep generated normals smooth, instead of splitting every new ring facet.
 for p in ob.data.polygons:p.use_smooth=True
info={'boundary_repairs':base_edges,'selectively_subdivided_edges':len(eligible),'phong_projected_new_vertices':moved,'max_projection_distance_local':maxmove,'hd_hull_vertices':len(obj.data.vertices),'hd_hull_faces':len(obj.data.polygons),'ring_radial_segments':128,'scope':'low-angle broad hull only, armor hard edges excluded'}
(root/'06_Report/Geometry_Refinement.json').write_text(json.dumps(info,indent=2))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Geometry/Aurora_HD_Geometry_v02.blend'))
# Repeat the macro with exactly the camera/light from Stage 1 comparison.
macro=bpy.data.objects.new('Ring_Comparison_Camera_v02',bpy.data.cameras.new('Ring_Comparison_Camera_v02'));s.collection.objects.link(macro);c=Vector(rings[0]['center']);n=Vector(rings[0]['normal']);macro.location=c+n*.18+Vector((0,-.055,.035));macro.rotation_euler=(c-macro.location).to_track_quat('-Z','Y').to_euler();macro.data.type='ORTHO';macro.data.ortho_scale=.078;s.camera=macro;s.render.resolution_x=1800;s.render.resolution_y=1800;s.render.resolution_percentage=100;s.view_layers['Beauty'].layer_collection.children['Ion_Thrusters_3D'].exclude=True;s.render.filepath=str(root/'04_Comparison/Ring_Repaired_v02_1800.png');bpy.ops.render.render(write_still=True)
print(json.dumps(info),flush=True)
