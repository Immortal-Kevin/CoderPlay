import bpy,bmesh,json,pathlib,math
import numpy as np
from mathutils import Vector
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root.parent/'07_IonThrusters/01_Blender/Aurora_IonThrusters_Editable.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64;s.render.threads_mode='FIXED';s.render.threads=4;s.render.image_settings.color_depth='8';s.render.resolution_percentage=100
old=next(o for o in bpy.data.collections['Original_Ship_UNMODIFIED'].objects if o.type=='MESH');original_collection=bpy.data.collections['Original_Ship_UNMODIFIED'];original_collection.name='P5_Original_Archived'
newcol=bpy.data.collections.new('HD_Remaster_Ship');s.collection.children.link(newcol);new=old.copy();new.data=old.data.copy();new.name='Aurora_HD_Hull';newcol.objects.link(new)
for layer in s.view_layers:
 layer.layer_collection.children[original_collection.name].exclude=True
 layer.layer_collection.children['Ship_Occlusion_ONLY'].exclude=True
 layer.use=layer.name=='Beauty'
baseverts=np.array([v.co[:] for v in old.data.vertices]);uvs={}
for p in old.data.polygons:
 for i,l in zip(p.vertices,p.loop_indices):uvs.setdefault(i,[]).append(list(old.data.uv_layers.active.data[l].uv))
cyan=bpy.data.materials.new('HD_Original_Cyan_Annulus');cyan.use_nodes=True;bs=cyan.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.005,.35,.32,1);bs.inputs['Metallic'].default_value=.5;bs.inputs['Roughness'].default_value=.23;bs.inputs['Emission Color'].default_value=(.008,.8,.66,1);bs.inputs['Emission Strength'].default_value=.8
ringinfo=[];remove=set()
for sign in [1,-1]:
 v=baseverts.copy();v[:,0]*=sign;plane=v[:,0]-.19856*v[:,1];sel=(v[:,0]>.13)&(v[:,1]>-.155)&(v[:,1]<-.085)&(abs(v[:,2])<.04)
 outerids=np.where(sel&(abs(plane-.16518)<.00002))[0];innerids=np.where(sel&(abs(plane-.17362)<.00002))[0]
 outer=np.unique(np.round(v[outerids],8),axis=0);inner=np.unique(np.round(v[innerids],8),axis=0);c=outer.mean(axis=0);ci=inner.mean(axis=0);_,_,vh=np.linalg.svd(outer-c);normal=vh[-1];normal*=1 if normal[0]>0 else -1
 t=np.cross([0,0,1],normal);t/=np.linalg.norm(t);u=np.cross(normal,t);r=float(np.mean(np.linalg.norm(outer-c,axis=1)));ri=float(np.mean(np.linalg.norm(inner-ci,axis=1)));depth=float(np.dot(ci-c,normal))
 # Original UVs are affine on each ring surface. Retain their orientation.
 def uvfit(ids):
  pts=v[ids];x=np.column_stack(((pts-c)@t,(pts-c)@u,np.ones(len(ids))));values=np.array([np.mean(uvs[int(i)],axis=0) for i in ids]);return np.linalg.lstsq(x,values,rcond=None)[0]
 fit_outer=uvfit(outerids);fit_inner=uvfit(innerids)
 mask=sel&(plane>=.16516)&(plane<=.176)
 ids=set(np.where(mask)[0].tolist())
 for p in new.data.polygons:
  if all(i in ids for i in p.vertices):remove.add(p.index)
 profile=[(r,0),(r,.00025),(r-.00025,.00065),(ri+.0006,depth-.0006),(ri,depth),(ri-.00035,depth+.00025)]
 verts=[];uvlist=[];faces=[];N=128
 for rad,d in profile:
  mix=min(1,max(0,d/max(depth,1e-8)));fit=fit_outer*(1-mix)+fit_inner*mix
  for j in range(N):
   a=2*math.pi*j/N;pt=c+normal*d+t*rad*math.cos(a)+u*rad*math.sin(a);pt[0]*=sign;verts.append(pt.tolist());uvlist.append((np.array([rad*math.cos(a),rad*math.sin(a),1])@fit).tolist())
 for k in range(len(profile)-1):
  for j in range(N):faces.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
 # Shallow dished cap, preserving original radial proportions.
 for rad in [ri*.94,ri*.82,ri*.5,ri*.1,0.0]:
  d=depth+.0003+.0017*(1-rad/ri)
  for j in range(N):
   a=2*math.pi*j/N;pt=c+normal*d+t*rad*math.cos(a)+u*rad*math.sin(a);pt[0]*=sign;verts.append(pt.tolist());uvlist.append((np.array([rad*math.cos(a),rad*math.sin(a),1])@fit_inner).tolist())
 count=len(verts)//N
 for k in range(len(profile)-1,count-1):
  for j in range(N):faces.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
 mesh=bpy.data.meshes.new(f'Ring_{sign}_128_Profile');mesh.from_pydata(verts,[],faces);mesh.update();ob=bpy.data.objects.new('HD_Port_Ring' if sign==1 else 'HD_Starboard_Ring',mesh);newcol.objects.link(ob);mesh.materials.append(old.data.materials[0]);uv=mesh.uv_layers.new(name='UVMap')
 for p in mesh.polygons:
  p.use_smooth=True
  for i,l in zip(p.vertices,p.loop_indices):uv.data[l].uv=uvlist[i]
 # Geometric emissive annulus, independent of low-resolution texture edges.
 tv=[];tf=[];R=ri*.875;minor=ri*.053
 for j in range(N):
  a=j*2*math.pi/N;radial=t*math.cos(a)+u*math.sin(a)
  for k in range(16):
   b=k*2*math.pi/16;pt=c+normal*(depth+.00065+minor*math.sin(b))+radial*(R+minor*math.cos(b));pt[0]*=sign;tv.append(pt.tolist())
 for j in range(N):
  for k in range(16):tf.append((j*16+k,((j+1)%N)*16+k,((j+1)%N)*16+(k+1)%16,j*16+(k+1)%16))
 tm=bpy.data.meshes.new('Cyan_Annulus_128x16');tm.from_pydata(tv,[],tf);tm.update();to=bpy.data.objects.new('HD_Cyan_Annulus_'+str(sign),tm);newcol.objects.link(to);tm.materials.append(cyan)
 for p in tm.polygons:p.use_smooth=True
 c[0]*=sign;normal[0]*=sign;ringinfo.append({'side':sign,'center':c.tolist(),'normal':normal.tolist(),'radius':r,'inner_front_radius':ri,'depth':depth,'original_radial_segments':len(outer),'new_radial_segments':N,'new_annulus_cross_segments':16})
bm=bmesh.new();bm.from_mesh(new.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in sorted(remove)],context='FACES');bm.to_mesh(new.data);bm.free()
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Geometry/Aurora_RingRepair_Stage1.blend'))
info={'original_vertices':len(old.data.vertices),'original_faces':len(old.data.polygons),'old_ring_faces_hidden_in_archived_original':len(remove),'rings':ringinfo};(root/'06_Report/Ring_Repair.json').write_text(json.dumps(info,indent=2))
# Consistent oblique macro camera reveals silhouette, not only smooth shading.
center=Vector(ringinfo[0]['center']);axis=Vector(ringinfo[0]['normal']);camera=bpy.data.objects.new('Ring_Comparison_Camera',bpy.data.cameras.new('Ring_Comparison_Camera'));s.collection.objects.link(camera);camera.location=center+axis*.18+Vector((0,-.055,.035));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.078;s.camera=camera;s.render.resolution_x=1800;s.render.resolution_y=1800
for label,hd in [('Original',False),('Repaired',True)]:
 beauty=s.view_layers['Beauty'];beauty.layer_collection.children[original_collection.name].exclude=hd;beauty.layer_collection.children[newcol.name].exclude=not hd;beauty.layer_collection.children['Ion_Thrusters_3D'].exclude=True;s.render.filepath=str(root/'04_Comparison'/f'Ring_{label}_1800.png');bpy.ops.render.render(write_still=True)
print(json.dumps(info,indent=2))
