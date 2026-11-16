import bpy,json,pathlib,math,time,sys
from mathutils import Vector
root=pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'02_Models/starship_souvenir/starship_souvenir_FourViews.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.render.threads_mode='FIXED';s.render.threads=4
s.eevee.taa_render_samples=64
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='16';s.render.film_transparent=True
s.render.resolution_percentage=100
original=next(o for o in s.objects if o.type=='MESH')
def collection(name):
 c=bpy.data.collections.new(name);s.collection.children.link(c);return c
body=collection('Original_Ship_UNMODIFIED');hold=collection('Ship_Occlusion_ONLY');fx=collection('Ion_Thrusters_3D')
for c in list(original.users_collection):c.objects.unlink(original)
body.objects.link(original)
duplicate=original.copy();duplicate.data=original.data.copy();duplicate.name='Ship_Holdout_Copy';hold.objects.link(duplicate)
hm=bpy.data.materials.new('Occlusion_Holdout');hm.use_nodes=True;hm.node_tree.nodes.clear();h=hm.node_tree.nodes.new('ShaderNodeHoldout');o=hm.node_tree.nodes.new('ShaderNodeOutputMaterial');hm.node_tree.links.new(h.outputs[0],o.inputs['Surface']);duplicate.data.materials.clear();duplicate.data.materials.append(hm)
for p in duplicate.data.polygons:p.material_index=0
beauty=s.view_layers[0];beauty.name='Beauty';beauty.layer_collection.children[hold.name].exclude=True
layer=s.view_layers.new('ThrusterOnly_Occluded');layer.layer_collection.children[body.name].exclude=True
beauty.use=False;layer.use=True
controller=bpy.data.objects.new('ION_MASTER_PARAMETERS',None);fx.objects.link(controller)
params={'length_diameters':1.1,'nozzle_radius':.01668825,'length':.03671415,'radius_multiplier':1.45,'color':'cyan-white core -> electric blue halo','engine_axis':[0,1,0],'reference':str(root.parent/'01_SourceAssets/poster/poster_aurora__-963771210458364377.png')}
for k,v in params.items():
 if isinstance(v,(float,int,str,list)):controller[k]=v
def material(name,color,strength,opacity,noise):
 m=bpy.data.materials.new(name);m.use_nodes=True
 try:m.surface_render_method='BLENDED'
 except:m.surface_render_method='DITHERED'
 if hasattr(m,'use_transparent_shadow'):m.use_transparent_shadow=False
 n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
 out=n.new('ShaderNodeOutputMaterial');mix=n.new('ShaderNodeMixShader');trans=n.new('ShaderNodeBsdfTransparent');em=n.new('ShaderNodeEmission');em.inputs['Color'].default_value=(*color,1);em.inputs['Strength'].default_value=strength
 geom=n.new('ShaderNodeNewGeometry');dot=n.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';l.new(geom.outputs['Normal'],dot.inputs[0]);l.new(geom.outputs['Incoming'],dot.inputs[1]);ab=n.new('ShaderNodeMath');ab.operation='ABSOLUTE';l.new(dot.outputs['Value'],ab.inputs[0]);power=n.new('ShaderNodeMath');power.operation='POWER';power.inputs[1].default_value=1.7;l.new(ab.outputs[0],power.inputs[0])
 tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=5;tex.inputs['Detail'].default_value=2;coord=n.new('ShaderNodeTexCoord');l.new(coord.outputs['Generated'],tex.inputs['Vector']);remap=n.new('ShaderNodeMapRange');remap.inputs['To Min'].default_value=1-noise;remap.inputs['To Max'].default_value=1;l.new(tex.outputs['Fac'],remap.inputs['Value'])
 mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';l.new(power.outputs[0],mul.inputs[0]);l.new(remap.outputs[0],mul.inputs[1]);gain=n.new('ShaderNodeMath');gain.operation='MULTIPLY';gain.inputs[1].default_value=opacity;l.new(mul.outputs[0],gain.inputs[0]);l.new(gain.outputs[0],mix.inputs[0]);l.new(trans.outputs[0],mix.inputs[1]);l.new(em.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])
 return m
core=material('Ion_CoolWhite_Cyan_Core',(0.20,.86,1),3.0,.82,.08)
plasma=material('Ion_Cyan_Blue_Plasma',(.005,.32,1),1.7,.43,.2)
halo=material('Ion_Soft_Blue_Halo',(.005,.12,1),1.15,.13,.12)
engines=[]
for x in [-.120033212,.120033212]:
 for z in [-.040943504,.044989898]:
  p=Vector((x,.33250665,z));name=('Port' if x>0 else 'Starboard')+('_Upper' if z>0 else '_Lower');engines.append({'name':name,'center':list(p),'radius':params['nozzle_radius'],'axis':[0,1,0]})
  mount=bpy.data.objects.new(name+'_Nozzle',None);fx.objects.link(mount);mount.location=p;mount.parent=controller;mount['radius']=params['nozzle_radius'];mount['axis']=[0,1,0]
  for label,offset,scale,mat in [('Core',.004,(.013,.010,.013),core),('Plasma',.014,(.018,.021,.018),plasma),('Halo',.015,(.024,.022,.024),halo)]:
   bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=1,location=p+Vector((0,offset,0)));obj=bpy.context.object;obj.name=name+'_'+label
   for c in list(obj.users_collection):c.objects.unlink(obj)
   fx.objects.link(obj);obj.parent=mount;obj.matrix_parent_inverse=mount.matrix_world.inverted();obj.scale=scale;obj.data.materials.append(mat)
   for poly in obj.data.polygons:poly.use_smooth=True
params['engines']=engines;params['objects_per_engine']=3
(root/'01_Blender/Ion_Parameters.json').write_text(json.dumps(params,indent=2),encoding='utf8')
s['P5_notes']='Original mesh/materials untouched. Beauty: ship+FX; ThrusterOnly_Occluded: holdout ship+FX. Camera positions and scales from P4. Final PNG comp preserves P4 ship pixels.'
s.camera=bpy.data.objects['Rear_ThreeQuarter'];s.render.resolution_x=1600;s.render.resolution_y=1145;s.render.filepath=str(root/'02_Preview/Rear_ThreeQuarter_ThrusterRaw_1600.png')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_IonThrusters_v01.blend'))
t=time.time();bpy.ops.render.render(write_still=True)
(root/'05_Report/Thruster_Preview_Timing.json').write_text(json.dumps({'engine':s.render.engine,'width':1600,'seconds':time.time()-t,'threads':s.render.threads},indent=2))
print('P5 PREVIEW COMPLETE',flush=True)
