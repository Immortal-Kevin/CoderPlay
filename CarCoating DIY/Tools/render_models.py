import bpy,pathlib,json,math,sys
from mathutils import Vector
base=pathlib.Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
model=args[0] if args else 'starship_crashed';width=int(args[1]) if len(args)>1 else 1600
folder=base/'02_Models'/model;mats=json.loads((folder/'materials_decoded.json').read_text(encoding='utf8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
(folder/(model+'.mtl')).write_text('\n'.join(f'newmtl {m["name"]}\nKd 0.7 0.7 0.7\n' for m in mats))
bpy.ops.wm.obj_import(filepath=str(folder/(model+'.obj')),forward_axis='Y',up_axis='Z',use_split_objects=False,use_split_groups=False)
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');obj.name=model
for m in mats:
 mat=bpy.data.materials.get(m['name']) or bpy.data.materials.new(m['name']);mat.use_nodes=True
 nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs['BSDF'],output.inputs['Surface'])
 bs.inputs['Roughness'].default_value=.45;bs.inputs['Metallic'].default_value=.25
 col=m['colors'].get('_Color',{'r':1,'g':1,'b':1,'a':1});bs.inputs['Base Color'].default_value=(col['r'],col['g'],col['b'],1)
 for slot,tex in m['textures'].items():
  im=bpy.data.images.load(str(folder/tex.get('decoded_file',tex['file'])),check_existing=True);node=nodes.new('ShaderNodeTexImage');node.image=im
  uv=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeMapping');mapping.inputs['Scale'].default_value=(*tex['scale'],1);mapping.inputs['Location'].default_value=(*tex['offset'],0);links.new(uv.outputs['UV'],mapping.inputs['Vector']);links.new(mapping.outputs['Vector'],node.inputs['Vector'])
  if slot=='_MainTex':links.new(node.outputs['Color'],bs.inputs['Base Color'])
  elif slot in ['_Illum','_EmissionMap']:
   links.new(node.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=.3
  elif slot=='_BumpMap':
   im.colorspace_settings.name='Non-Color'
   normal=nodes.new('ShaderNodeNormalMap');links.new(node.outputs['Color'],normal.inputs['Color']);normal.inputs['Strength'].default_value=1;links.new(normal.outputs['Normal'],bs.inputs['Normal'])
 if mat.name not in [s.name for s in obj.data.materials]:obj.data.materials.append(mat)
for poly in obj.data.polygons:poly.use_smooth=True
verts=[obj.matrix_world@Vector(c) for c in obj.bound_box];lo=Vector(tuple(min(v[i] for v in verts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in verts) for i in range(3)));center=(lo+hi)/2;size=hi-lo;radius=size.length
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8';scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.65,.72,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.65
for name,pos,power,scale in [('Key',(2,-1,3),1800,2),('Fill',(-2,1,1),1300,2),('Rim',(1,2,2),1600,1.5)]:
 light=bpy.data.lights.new(name,'AREA');light.energy=power*(radius/10)**2;light.shape='DISK';light.size=radius*scale;ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=center+Vector(pos)*radius;ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Orthographic');cam=bpy.data.objects.new('Orthographic',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.clip_end=radius*20
views=[('Left',(1,0,0)),('Right',(-1,0,0)),('Front_ThreeQuarter',(1,-1,.36)),('Rear_ThreeQuarter',(-1,1,.36))]
if len(args)>2 and args[2]=='export_only':views=[]
stats={'model':model,'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons),'bounds':{'min':list(lo),'max':list(hi)},'views':[]}
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'{model}_{width}.blend'))
for label,direction in views:
 cam.location=center+Vector(direction).normalized()*radius*3;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
 # Fit all bounding-box corners into camera plane with 8% margin.
 rot=cam.rotation_euler.to_matrix().transposed();project=[rot@(v-center) for v in verts];sx=max(v.x for v in project)-min(v.x for v in project);sy=max(v.y for v in project)-min(v.y for v in project)
 aspect=min(4,max(1,sx/sy));scene.render.resolution_x=width;scene.render.resolution_y=round(width/aspect);camdata.ortho_scale=max(sx,sy*aspect)*1.12
 dest=base/('04_PrintReady' if width>=8000 else '05_Preview')/f'{model}_{label}_{width}.png';scene.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
 stats['views'].append({'file':str(dest),'width':scene.render.resolution_x,'height':scene.render.resolution_y,'direction':direction})
 if width>=8000:
  scene.render.filepath=str(base/'03_Renders'/dest.name)
  # The final PNG itself is in PrintReady; avoid duplicating large renders.
bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'{model}_{width}.blend'))
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.gltf(filepath=str(folder/(model+f'_{width}.glb')),export_format='GLB',use_selection=True)
(base/'06_Reports'/f'{model}_{width}_Render_Stats.json').write_text(json.dumps(stats,indent=2))
