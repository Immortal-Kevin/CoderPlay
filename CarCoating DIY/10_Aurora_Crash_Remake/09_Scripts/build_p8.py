import bpy,bmesh,math,pathlib,json,random,sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'08_Aurora_HD_Remaster/01_Geometry/Aurora_HD_Remaster_Editable.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64;s.render.threads_mode='FIXED';s.render.threads=4;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8';s.render.resolution_percentage=100
for vl in s.view_layers:
 vl.use=vl.name=='Beauty'
 for c in vl.layer_collection.children:
  if c.name in ['HD_Remaster_Ship','P5_Original_Archived','Ship_Occlusion_ONLY','Ion_Thrusters_3D']:c.exclude=True
def col(name):
 c=bpy.data.collections.new('P8_'+name);s.collection.children.link(c);return c
cols={name:col(name) for name in ['OriginalContour_Hull','Engine_Details','Decals','Smoke','Fire','Ion','Studio']}
def move(o,c):
 for cc in list(o.users_collection):cc.objects.unlink(o)
 c.objects.link(o)
def material(name,color,metal=.3,rough=.3):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;p.inputs['Coat Weight'].default_value=.25;p.inputs['Coat Roughness'].default_value=.18;return m
def mesh(name,v,f,c,mat):
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);c.objects.link(o);me.materials.append(mat)
 for p in me.polygons:p.use_smooth=True
 return o
def lathe(name,x,z,profile,mat,N=96,break_sector=False):
 v=[];f=[]
 for y,r in profile:
  for j in range(N):a=j*2*math.pi/N;v.append((x+r*math.cos(a),y,z+r*math.sin(a)))
 for k in range(len(profile)-1):
  for j in range(N):
   if break_sector and 8<j<25 and k<2:continue
   f.append((k*N+j,(k+1)*N+j,(k+1)*N+(j+1)%N,k*N+(j+1)%N))
 return mesh(name,v,f,cols['Engine_Details'],mat)
def tube(name,pts,r,mat,c):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=2;sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for p,co in zip(sp.points,pts):p.co=(*co,1)
 ob=bpy.data.objects.new(name,cu);c.objects.link(ob);cu.materials.append(mat);return ob
# Keep P6 geometry and UVs. No P7 object or pressure-hull construction is loaded.
for o in list(bpy.data.collections['HD_Remaster_Ship'].objects):
 cp=o.copy();cp.data=o.data.copy();cp.name='P8_'+o.name;cols['OriginalContour_Hull'].objects.link(cp)
hull=bpy.data.objects['P8_Aurora_HD_Hull'];bm=bmesh.new();bm.from_mesh(hull.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.normal_update()
# Real shell openings in two original engine casings, concentrated near the stern.
damage=[{'x':.120033212,'z':.044989898,'y':.271,'side':1},{'x':-.120033212,'z':-.040943504,'y':.267,'side':-1}]
cut=[]
for f in bm.faces:
 c=f.calc_center_median()
 for d in damage:
  dx=c.x-d['x'];dz=c.z-d['z'];rad=math.hypot(dx,dz)
  if .021<rad<.033 and ((c.y-d['y'])/.033)**2+((dz-.012)/.022)**2<1 and dx*d['side']>.010:cut.append(f);break
bmesh.ops.delete(bm,geom=cut,context='FACES');bm.normal_update()
crease=bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
protected=0
for e in bm.edges:
 angle=e.calc_face_angle(0) if len(e.link_faces)==2 else math.pi
 # Boundary, mechanical hard edges and flat fin creases retain source proportions.
 e[crease]=1 if len(e.link_faces)!=2 or angle>math.radians(42) else .65 if angle>math.radians(28) else 0
 if e[crease]>0:protected+=1
bm.to_mesh(hull.data);bm.free()
for p in hull.data.polygons:p.use_smooth=True
sub=hull.modifiers.new('Constrained source surface smoothing','SUBSURF');sub.subdivision_type='CATMULL_CLARK';sub.levels=2;sub.render_levels=2;sub.uv_smooth='PRESERVE_BOUNDARIES'
# Native 2048 UV atlas + subtle physical coating. No large procedural panel grid.
mat=material('P8_Original_Atlas_Metal_Coating',(.6,.6,.6),.25,.3);nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Coat Weight'].default_value=.35
def tex(filename,noncolor=False):
 t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(root/'03_Textures'/filename),check_existing=True)
 if noncolor:t.image.colorspace_settings.name='Non-Color'
 return t
base=tex('Aurora_Original_Crash_Atlas_2048.png');rough=tex('Aurora_Roughness_2048.png',True);metal=tex('Aurora_Metallic_2048.png',True);normal=tex('Aurora_Original_Normal_OpenGL_2048.png',True)
links.new(base.outputs['Color'],bs.inputs['Base Color']);links.new(rough.outputs['Color'],bs.inputs['Roughness']);links.new(metal.outputs['Color'],bs.inputs['Metallic'])
nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.16;links.new(normal.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])
coord=nodes.new('ShaderNodeTexCoord');pos=nodes.new('ShaderNodeNewGeometry')
def mathnode(op,a=None,b=None):
 n=nodes.new('ShaderNodeMath');n.operation=op
 for i,val in enumerate([a,b]):
  if val is None:continue
  if isinstance(val,(int,float)):n.inputs[i].default_value=val
  else:links.new(val,n.inputs[i])
 return n.outputs[0]
masks=[]
for d in damage:
 subtract=nodes.new('ShaderNodeVectorMath');subtract.operation='SUBTRACT';links.new(pos.outputs['Position'],subtract.inputs[0]);subtract.inputs[1].default_value=(d['x']+d['side']*.020,d['y'],d['z']+.013)
 scale=nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';links.new(subtract.outputs[0],scale.inputs[0]);scale.inputs[1].default_value=(1/.032,1/.061,1/.037)
 length=nodes.new('ShaderNodeVectorMath');length.operation='LENGTH';links.new(scale.outputs[0],length.inputs[0]);fac=mathnode('SUBTRACT',1,length.outputs['Value']);clamp=nodes.new('ShaderNodeClamp');links.new(fac,clamp.inputs[0]);masks.append(clamp.outputs[0])
mask=mathnode('MAXIMUM',masks[0],masks[1]);mask=mathnode('MULTIPLY',mask,.95)
ai=nodes.new('ShaderNodeTexImage');ai.image=bpy.data.images.load(str(root/'04_AI/Scorch_AI_Raw_384.png'),check_existing=True);ai.projection='BOX';ai.projection_blend=.25;ai.image.colorspace_settings.name='Non-Color'
mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='SCALE';mapping.inputs[3].default_value=12;links.new(coord.outputs['Object'],mapping.inputs[0]);links.new(mapping.outputs[0],ai.inputs['Vector'])
ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.012,.016,.020,1);ramp.color_ramp.elements[1].color=(.085,.068,.050,1);links.new(ai.outputs['Color'],ramp.inputs[0]);mix=nodes.new('ShaderNodeMixRGB');links.new(mask,mix.inputs[0]);links.new(base.outputs['Color'],mix.inputs[1]);links.new(ramp.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],bs.inputs['Base Color'])
rm=nodes.new('ShaderNodeMixRGB');links.new(mask,rm.inputs[0]);links.new(rough.outputs[0],rm.inputs[1]);rm.inputs[2].default_value=(.64,.64,.64,1);links.new(rm.outputs[0],bs.inputs['Roughness'])
mat['AI_scope']='Only localized rear burn colour/roughness masks; entire original atlas and UV retained.'
hull.data.materials.clear();hull.data.materials.append(mat)
alloy=material('P8_Satin_Titanium',(.22,.27,.32),.85,.27);inner=material('P8_Heat_Darkened_Internal',(.035,.045,.055),.72,.4);edge=material('P8_Polished_Nozzle_Lip',(.55,.61,.66),.9,.21)
for x in [-.120033212,.120033212]:
 for z in [-.040943504,.044989898]:
  damaged=(x>0 and z>0) or (x<0 and z<0)
  lathe('P8_OriginalSized_NozzleLip',x,z,[(.319,.0175),(.327,.0182),(.332,.0178),(.334,.0169),(.333,.0158),(.325,.0156)],edge)
  lathe('P8_Nozzle_Recess',x,z,[(.296,.0149),(.323,.0150),(.331,.0156)],inner)
  for j in range(16):
   a=j*math.tau/16;r=.0148;tube('P8_Inner_Cooling_Rib',[(x+r*math.cos(a),.300,z+r*math.sin(a)),(x+r*math.cos(a),.329,z+r*math.sin(a))],.00035,alloy,cols['Engine_Details'])
  if damaged:
   lathe('P8_Exposed_Engine_InnerSleeve',x,z,[(.229,.020),(.246,.021),(.286,.021),(.315,.019)],inner)
   for j in range(9):
    a=j*math.tau/9;r=.022;tube('P8_Exposed_Internal_Conduit',[(x+r*math.cos(a),.233,z+r*math.sin(a)),(x+r*math.cos(a),.305,z+r*math.sin(a))],.00065,alloy,cols['Engine_Details'])
# Source-aligned exact logos, on the original fin/hull surfaces.
dg=bpy.context.evaluated_depsgraph_get();ev=hull.evaluated_get(dg);me=ev.to_mesh();bvh=BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear()
decal=bpy.data.materials.new('P8_Exact_Alterra_Decal');decal.use_nodes=True;decal.surface_render_method='DITHERED';dn=decal.node_tree.nodes;dl=decal.node_tree.links;db=dn.get('Principled BSDF');dt=dn.new('ShaderNodeTexImage');dt.image=bpy.data.images.load(str(root/'03_Textures/Alterra_Exact_Transparent.png'));dl.new(dt.outputs['Color'],db.inputs['Base Color']);dl.new(dt.outputs['Alpha'],db.inputs['Alpha']);db.inputs['Roughness'].default_value=.32
placements=[]
for sign in [1,-1]:
 for label,y,z,w,h in [('Hull',-.235,.016,.026,.028),('TopFin',.151,.147,.027,.029)]:
  verts=[];faces=[];N=20;valid=True
  for j in range(N+1):
   for i in range(N+1):
    yy=y+(i/N-.5)*w*sign;zz=z+(j/N-.5)*h;hit,no,ind,dist=bvh.ray_cast(Vector((sign*.4,yy,zz)),Vector((-sign,0,0)),.8)
    if hit is None:valid=False;hit=Vector((0,yy,zz));no=Vector((sign,0,0))
    verts.append(hit+no*.00006)
  if not valid:placements.append({'name':label,'side':sign,'valid':False});continue
  for j in range(N):
   for i in range(N):k=j*(N+1)+i;faces.append((k,k+1,k+N+2,k+N+1))
  ob=mesh('P8_Alterra_'+label+'_'+str(sign),verts,faces,cols['Decals'],decal);uv=ob.data.uv_layers.new()
  for p in ob.data.polygons:
   for vi,li in zip(p.vertices,p.loop_indices):uv.data[li].uv=(vi%(N+1)/N,vi//(N+1)/N)
  placements.append({'name':label,'side':sign,'valid':True,'position':[y,z]})
# Genuine 3D volumes: spatial feathering + turbulence, never billboard copies.
def volume(name,color,density,emission=0,emitcolor=(1,.2,.01),noise_scale=5):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');pv=n.new('ShaderNodeVolumePrincipled');pv.inputs['Color'].default_value=(*color,1);pv.inputs['Anisotropy'].default_value=.18
 co=n.new('ShaderNodeTexCoord');sub=n.new('ShaderNodeVectorMath');sub.operation='SUBTRACT';l.new(co.outputs['Generated'],sub.inputs[0]);sub.inputs[1].default_value=(.5,.5,.5);ln=n.new('ShaderNodeVectorMath');ln.operation='LENGTH';l.new(sub.outputs[0],ln.inputs[0]);ran=n.new('ShaderNodeMapRange');ran.clamp=True;ran.inputs['From Min'].default_value=.13;ran.inputs['From Max'].default_value=.50;ran.inputs['To Min'].default_value=1;ran.inputs['To Max'].default_value=0;l.new(ln.outputs['Value'],ran.inputs['Value']);noi=n.new('ShaderNodeTexNoise');noi.inputs['Scale'].default_value=noise_scale;noi.inputs['Detail'].default_value=4;noi.inputs['Roughness'].default_value=.7;l.new(co.outputs['Generated'],noi.inputs['Vector']);nr=n.new('ShaderNodeMapRange');nr.inputs['From Min'].default_value=.27;nr.inputs['From Max'].default_value=.7;nr.inputs['To Min'].default_value=0;nr.inputs['To Max'].default_value=1;nr.clamp=True;l.new(noi.outputs['Fac'],nr.inputs['Value']);mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';l.new(ran.outputs[0],mul.inputs[0]);l.new(nr.outputs[0],mul.inputs[1]);gain=n.new('ShaderNodeMath');gain.operation='MULTIPLY';gain.inputs[1].default_value=density;l.new(mul.outputs[0],gain.inputs[0]);l.new(gain.outputs[0],pv.inputs['Density'])
 if emission:
  eg=n.new('ShaderNodeMath');eg.operation='MULTIPLY';eg.inputs[1].default_value=emission;l.new(mul.outputs[0],eg.inputs[0]);l.new(eg.outputs[0],pv.inputs['Emission Strength']);pv.inputs['Emission Color'].default_value=(*emitcolor,1)
 l.new(pv.outputs['Volume'],out.inputs['Volume']);return m
smoke=volume('P8_Turbulent_Charcoal_Smoke',(.11,.12,.13),65,noise_scale=6)
fire=volume('P8_Amber_Fire_Volume',(.12,.025,.003),16,70,(1,.16,.008),7)
hot=volume('P8_Hot_Yellow_Core',(.3,.06,.003),20,110,(1,.55,.045),5)
ion=volume('P8_Soft_Cyan_Ion',(.015,.10,.3),18,80,(.015,.43,1),3)
def blob(name,loc,scale,mat,c,seed):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,radius=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;o.rotation_euler=(0,seed*.17,seed*.51);move(o,c);o.data.materials.append(mat);return o
rng=random.Random(8102)
for k,d in enumerate(damage):
 origin=Vector((d['x']+d['side']*.024,d['y']+.013,d['z']+.017))
 for j in range(11):
  t=j/10;c=origin+Vector((d['side']*(.008+.014*t)+rng.uniform(-.004,.004),.015+.225*t,.006+.044*t+rng.uniform(-.005,.005)));r=.017+.022*t;blob(f'P8_Smoke_{k}_{j}',c,(r,.029+.017*t,r*.86),smoke,cols['Smoke'],k*31+j)
 for j in range(7):
  t=j/6;c=origin+Vector((rng.uniform(-.007,.007),.002+.057*t,rng.uniform(-.008,.009)));blob(f'P8_Fire_{k}_{j}',c,(.009*(1-.6*t),.020*(1-.35*t),.012*(1-.55*t)),fire,cols['Fire'],j+k*20)
 for j in range(3):blob(f'P8_Fire_Core_{k}_{j}',origin+Vector((rng.uniform(-.004,.004),.012*j,rng.uniform(-.004,.004))),(.005,.013,.006),hot,cols['Fire'],j)
for x,z in [(.120033212,-.040943504),(-.120033212,.044989898)]:
 blob('P8_Undamaged_Ion_Plume',(x,.359,z),(.022,.043,.022),ion,cols['Ion'],1)
control=bpy.data.objects.new('P8_FX_Controls',None);cols['Fire'].objects.link(control);control['notes']='Toggle P8_Smoke, P8_Fire and P8_Ion collections independently; all are actual 3D volumes. Damage concentrated in two rear casings.'
# New studio environment, entirely local, no inherited P7 geometry or lighting.
for o in s.objects:
 if o.type=='LIGHT':o.hide_render=True
W,H=1024,512;xx,yy=np.meshgrid(np.arange(W)/W,np.arange(H)/H);env=np.zeros((H,W,4),dtype=np.float32);env[:,:,:3]=(.13,.16,.20);env[:,:,3]=1
for cx,cy,wx,wy,power in [(.17,.38,.11,.13,3.5),(.66,.37,.07,.22,2.2),(.91,.55,.12,.10,1.5)]:
 mask=np.exp(-((xx-cx)/wx)**8-((yy-cy)/wy)**8);env[:,:,:3]+=mask[:,:,None]*power
im=bpy.data.images.new('P8_Studio_Reflection',W,H,float_buffer=True);im.pixels.foreach_set(env.ravel());im.filepath_raw=str(root/'03_Textures/P8_Studio_Reflection.exr');im.file_format='OPEN_EXR';im.save()
world=bpy.data.worlds.new('P8_Studio_World');world.use_nodes=True;wn=world.node_tree.nodes;wl=world.node_tree.links;et=wn.new('ShaderNodeTexEnvironment');et.image=im;wl.new(et.outputs['Color'],wn['Background'].inputs['Color']);wn['Background'].inputs['Strength'].default_value=.30;s.world=world
lights=[]
for name,loc,power,size in [('Key',(.35,-.32,.60),10,.5),('Fill',(-.35,-.10,.25),5,.65),('Rim',(.05,.55,.38),14,.42)]:
 data=bpy.data.lights.new('P8_'+name,'AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new('P8_'+name,data);cols['Studio'].objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,0))-ob.location).to_track_quat('-Z','Y').to_euler();lights.append({'name':name,'location':list(loc),'energy':power,'size':size,'rotation':list(ob.rotation_euler)})
camera_info={}
for name in ['Front_ThreeQuarter','Rear_ThreeQuarter','Left','Right']:
 cam=bpy.data.objects[name];cam.location+=Vector((0,.045,.008));cam.data.ortho_scale*=1.15;camera_info[name]={'matrix':[list(row) for row in cam.matrix_world],'ortho_scale':cam.data.ortho_scale}
s.camera=bpy.data.objects['Front_ThreeQuarter'];s.render.resolution_x=2048;s.render.resolution_y=1528;s.render.filepath=str(root/'06_Preview/P8_Front_ThreeQuarter_2048_v01.png');s['P8_notes']='P6 source contour + creased subdivision, native crashed atlas, localized two-engine damage. No P7 geometry. Volumetric fire/smoke/ion independent.'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_P8_Crash_Editable_v01.blend'))
(root/'08_Report/Build_v01.json').write_text(json.dumps({'source':'P6','P7_geometry_used':False,'cut_faces':len(cut),'protected_edges':protected,'source_hull_vertices':7490,'current_base_vertices':len(hull.data.vertices),'subdivision':2,'logos':placements,'lights':lights,'cameras':camera_info,'damage':damage,'collections':{k:len(v.objects) for k,v in cols.items()}},indent=2))
bpy.ops.render.render(write_still=True)
s.camera=bpy.data.objects['Rear_ThreeQuarter'];s.render.filepath=str(root/'06_Preview/P8_Rear_ThreeQuarter_2048_v01.png');bpy.ops.render.render(write_still=True)
print('P8 V01 SAVED AND RENDERED',flush=True)
