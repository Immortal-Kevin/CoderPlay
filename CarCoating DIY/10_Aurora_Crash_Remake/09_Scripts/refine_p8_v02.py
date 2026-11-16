import bpy,bmesh,math,pathlib,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_P8_Crash_Editable_v01.blend'));s=bpy.context.scene
hull=bpy.data.objects['P8_Aurora_HD_Hull'];mat=hull.data.materials[0]
with bpy.data.libraries.load(str(root.parent/'08_Aurora_HD_Remaster/01_Geometry/Aurora_RingRepair_Stage1.blend'),link=False) as (src,dst):dst.objects=['Aurora_HD_Hull']
source=dst.objects[0];hull.data=source.data.copy();bpy.data.objects.remove(source,do_unlink=True);hull.data.materials.clear();hull.data.materials.append(mat)
for mod in list(hull.modifiers):hull.modifiers.remove(mod)
bm=bmesh.new();bm.from_mesh(hull.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.normal_update();crease=bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
for e in bm.edges:
 c=(e.verts[0].co+e.verts[1].co)*.5;ang=e.calc_face_angle(0) if len(e.link_faces)==2 else math.pi
 broad=(-.32<c.y<.17 and .003<c.z<.080)
 e[crease]=1 if len(e.link_faces)!=2 else (0 if broad and ang<math.radians(65) else 1 if ang>math.radians(42) else .35 if ang>math.radians(30) else 0)
bm.to_mesh(hull.data);bm.free()
for p in hull.data.polygons:p.use_smooth=True
bpy.context.view_layer.objects.active=hull;hull.select_set(True)
sub=hull.modifiers.new('Source constrained curved surface','SUBSURF');sub.levels=2;sub.render_levels=2;sub.uv_smooth='NONE';bpy.ops.object.modifier_apply(modifier=sub.name)
# Damage is cut after curvature refinement, avoiding pinched UVs at coarse boundaries.
damage=json.loads((root/'08_Report/Build_v01.json').read_text())['damage'];bm=bmesh.new();bm.from_mesh(hull.data);cut=[]
for f in bm.faces:
 c=f.calc_center_median()
 for d in damage:
  dx=c.x-d['x'];dz=c.z-d['z'];r=math.hypot(dx,dz)
  if .022<r<.033 and ((c.y-d['y'])/.027)**2+((dz-.008)/.019)**2<1 and dx*d['side']>.012:cut.append(f);break
bmesh.ops.delete(bm,geom=cut,context='FACES');bm.to_mesh(hull.data);bm.free()
for n in mat.node_tree.nodes:
 if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.045
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Coat Weight'].default_value=.22;bs.inputs['Specular IOR Level'].default_value=.35
# Correct mesh volume coordinates: object coordinates are stable in EEVEE volumes.
for m in bpy.data.materials:
 if not m.name.startswith(('P8_Turbulent','P8_Amber','P8_Hot','P8_Soft')):continue
 n=m.node_tree.nodes;l=m.node_tree.links;coord=next(v for v in n if v.type=='TEX_COORD');sub=next(v for v in n if v.type=='VECT_MATH' and v.operation=='SUBTRACT');sub.operation='SCALE';sub.inputs[3].default_value=.5;l.new(coord.outputs['Object'],sub.inputs[0]);noise=next(v for v in n if v.type=='TEX_NOISE');l.new(sub.outputs[0],noise.inputs['Vector']);noise.inputs['Scale'].default_value=9 if 'Smoke' in m.name else 7
 pv=next(v for v in n if v.type=='PRINCIPLED_VOLUME');pv.inputs['Density Attribute'].default_value='';pv.inputs['Color Attribute'].default_value=''
 if 'Smoke' in m.name:pv.inputs['Color'].default_value=(.055,.061,.068,1)
# Smaller irregular puffs, soft fading ends. Same spatial trail in every view.
for o in bpy.data.collections['P8_Smoke'].objects:
 k=int(o.name.split('_')[-2]);d=damage[k];o.location.y=d['y']+.013+(o.location.y-d['y']-.013)*.78;o.scale*=.83
 o.rotation_euler=(0,0,0)
for cname in ['P8_Fire','P8_Ion']:
 for o in bpy.data.collections[cname].objects:
  if o.type=='MESH':o.rotation_euler=(0,0,0)
s.eevee.volumetric_tile_size='2';s.eevee.volumetric_samples=128;s.eevee.volumetric_start=.001;s.eevee.volumetric_end=3.0;s.eevee.volumetric_sample_distribution=.2;s.eevee.use_volumetric_shadows=True;s.eevee.volumetric_shadow_samples=32
# Move small hull logos clear of the original yellow stripe, refit to new surface.
bvh=BVHTree.FromPolygons([v.co for v in hull.data.vertices],[list(p.vertices) for p in hull.data.polygons]);placements=[]
for o in bpy.data.collections['P8_Decals'].objects:
 sign=int(o.name.split('_')[-1]);isbody='Hull' in o.name;N=20;y,z,w,h=(-.229,.030,.021,.023) if isbody else (.151,.147,.027,.029);miss=0
 for v in o.data.vertices:
  i=v.index%(N+1);j=v.index//(N+1);yy=y+(i/N-.5)*w*sign;zz=z+(j/N-.5)*h;hit,no,idx,dist=bvh.ray_cast(Vector((sign*.4,yy,zz)),Vector((-sign,0,0)),.8)
  if hit is not None:v.co=hit+no*.000055
  else:miss+=1
 placements.append({'name':o.name,'missed_rays':miss})
# Fit all visible ship and FX bounds with transparent margins; preserve camera orientation.
visible=[]
for c in s.collection.children:
 if c.name.startswith('P8_') and c.name!='P8_Studio':visible.extend(o for o in c.all_objects if o.type in {'MESH','CURVE'})
camera_info={}
for name in ['Front_ThreeQuarter','Rear_ThreeQuarter','Left','Right']:
 cam=bpy.data.objects[name];inv=cam.matrix_world.inverted();pts=[inv@(o.matrix_world@Vector(v)) for o in visible for v in o.bound_box];xmin=min(p.x for p in pts);xmax=max(p.x for p in pts);ymin=min(p.y for p in pts);ymax=max(p.y for p in pts)
 shift=cam.matrix_world.to_3x3()@Vector(((xmin+xmax)/2,(ymin+ymax)/2,0));cam.location+=shift;cam.data.ortho_scale=max(xmax-xmin,(ymax-ymin)*2048/1528)*1.12;bpy.context.view_layer.update();camera_info[name]={'matrix':[list(row) for row in cam.matrix_world],'ortho_scale':cam.data.ortho_scale}
s.camera=bpy.data.objects['Front_ThreeQuarter'];bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_P8_Crash_Editable_v02.blend'))
(root/'08_Report/Refinement_v02.json').write_text(json.dumps({'source':'P6 RingRepair Stage1 before earlier Phong tessellation','p7_geometry_used':False,'vertices':len(hull.data.vertices),'faces':len(hull.data.polygons),'cut_faces':len(cut),'logos':placements,'cameras':camera_info,'volume_coordinates':'Object local coordinates scaled to normalized radius; density/color grid attribute overrides cleared','volume_tile_px':2,'volume_samples':128},indent=2))
for view in ['Front_ThreeQuarter','Rear_ThreeQuarter']:
 s.camera=bpy.data.objects[view];s.render.filepath=str(root/'06_Preview'/f'P8_{view}_2048_v02.png');bpy.ops.render.render(write_still=True)
