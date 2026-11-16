import bpy,pathlib,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_P7_AI_Rebuild_Standard.blend'));s=bpy.context.scene;hull=bpy.data.objects['P7_Main_Hull_Clean_Shell']
mat=bpy.data.materials['P7_White_Aerospace_Coating'].copy();mat.name='P7_MainHull_Layered_AI';mat['AI_SECONDARY_GROUP']='DarkMetal';n=mat.node_tree.nodes;l=mat.node_tree.links;bs=n.get('Principled BSDF');mapping=next(node for node in n if node.type=='MAPPING')
geometry=n.new('ShaderNodeNewGeometry');sep=n.new('ShaderNodeSeparateXYZ');l.new(geometry.outputs['Position'],sep.inputs[0]);band=n.new('ShaderNodeMapRange');band.inputs['From Min'].default_value=-.019;band.inputs['From Max'].default_value=-.017;band.inputs['To Min'].default_value=1;band.inputs['To Max'].default_value=0;band.clamp=True;l.new(sep.outputs['Z'],band.inputs['Value'])
for channel,socket in [('BaseColor','Base Color'),('Roughness','Roughness'),('Metallic','Metallic'),('Height',None)]:
 path=root/'04_PBR_Materials'/f'DarkMetal_{channel}_4096.png';im=bpy.data.images.load(str(path),check_existing=True);tex=n.new('ShaderNodeTexImage');tex.image=im;tex.projection='BOX';tex.projection_blend=.22
 if channel!='BaseColor':im.colorspace_settings.name='Non-Color'
 l.new(mapping.outputs['Vector'],tex.inputs['Vector'])
 if channel=='BaseColor':white=n['AI_BaseColor'].outputs['Color'];dark=tex.outputs['Color']
 elif channel in ['Roughness','Metallic']:
  suffix='Roughness' if channel=='Roughness' else 'Metallic';white=n['P7_'+suffix+'_Adjust'].outputs[0];adjust=n.new('ShaderNodeMath');adjust.name='P7_'+suffix+'_Adjust_Dark';adjust.operation='MULTIPLY' if channel=='Roughness' else 'ADD';adjust.inputs[1].default_value=1 if channel=='Roughness' else 0;adjust.use_clamp=True;l.new(tex.outputs['Color'],adjust.inputs[0]);dark=adjust.outputs[0]
 else:white=n['AI_Height'].outputs['Color'];dark=tex.outputs['Color']
 mix=n.new('ShaderNodeMixRGB');mix.name='Hull_Paint_'+channel;l.new(band.outputs['Result'],mix.inputs[0]);l.new(white,mix.inputs[1]);l.new(dark,mix.inputs[2])
 if socket:l.new(mix.outputs[0],bs.inputs[socket])
 else:l.new(mix.outputs[0],next(node for node in n if node.type=='BUMP').inputs['Height'])
hull.data.materials.clear();hull.data.materials.append(mat)
for p in hull.data.polygons:p.material_index=0
bvh=BVHTree.FromPolygons([v.co.copy() for v in hull.data.vertices],[list(p.vertices) for p in hull.data.polygons],all_triangles=False)
for sign in [1,-1]:
 ob=bpy.data.objects['Alterra_Hull_'+str(sign)];N=16
 for j in range(N+1):
  for i in range(N+1):
   y=-.235+sign*(i/N-.5)*.0365;z=.009+(j/N-.5)*.038;p,no,idx,d=bvh.ray_cast(Vector((sign*.45,y,z)),Vector((-sign,0,0)),.9)
   if p is not None:ob.data.vertices[j*(N+1)+i].co=p+no*.00010
 ob.data.update();text=bpy.data.objects['Ship_Registry_'+str(sign)];p,no,idx,d=bvh.ray_cast(Vector((sign*.45,-.235,-.033)),Vector((-sign,0,0)),.9)
 if p is not None:text.location=p+no*.0002
structure=bpy.data.objects['P7_Original_Bridge_Stern_Structure'];sbvh=BVHTree.FromPolygons([v.co.copy() for v in structure.data.vertices],[list(p.vertices) for p in structure.data.polygons],all_triangles=False)
for sign in [1,-1]:
 ob=bpy.data.objects['Alterra_TopFin_'+str(sign)]
 for v in ob.data.vertices:
  p,no,idx,d=sbvh.find_nearest(v.co)
  if p is not None:v.co=p+no*.00010
 ob.data.update()
s['P7_final_refinements']='Continuous world-space navy/white paint boundary; corporate logos fully within white coating; registry moved clear of plates.'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_P7_AI_Rebuild_Standard_v03.blend'))
# Updated logo inspections, with the final paint boundary and placement.
cam=bpy.data.objects.new('Final_Decal_Camera',bpy.data.cameras.new('Final_Decal_Camera'));s.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=.075;s.camera=cam;s.render.resolution_x=1800;s.render.resolution_y=1500
for sign in [1,-1]:
 ob=bpy.data.objects['Alterra_Hull_'+str(sign)];c=sum((v.co for v in ob.data.vertices),Vector())/len(ob.data.vertices);cam.location=c+Vector((sign*.24,-sign*.025,.025));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(root/'06_Preview'/f'Logo_Hull_{sign}_Final_v03_1800.png');bpy.ops.render.render(write_still=True)
