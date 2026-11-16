import bpy,bmesh,pathlib,json,math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/P7_Geometry_Checkpoint_v04.blend'));s=bpy.context.scene
provenance=json.loads((root/'09_Report/AI_PBR_Provenance.json').read_text());assert len(provenance)==4
hull=bpy.data.objects['P7_Main_Hull_Clean_Shell'];profiles=json.loads((root/'09_Report/Loft_Profiles.json').read_text());ys=np.array(profiles['y']);NY=144;NT=128
def interp(y,values):
 values=np.array(values);der=np.gradient(values,ys);i=int(np.clip(np.searchsorted(ys,y)-1,0,len(ys)-2));dy=ys[i+1]-ys[i];t=(y-ys[i])/dy;return (2*t**3-3*t*t+1)*values[i]+(t**3-2*t*t+t)*dy*der[i]+(-2*t**3+3*t*t)*values[i+1]+(t**3-t*t)*dy*der[i+1]
for k in range(NY+1):
 y=ys[0]+(ys[-1]-ys[0])*k/NY;rx=max(.0008,interp(y,profiles['width']));top=interp(y,profiles['top']);bottom=interp(y,profiles['bottom']);cz=(top+bottom)/2;rz=max(.0008,(top-bottom)/2)
 for j in range(NT):a=j*2*math.pi/NT;hull.data.vertices[k*NT+j].co=(rx*math.cos(a),y,cz+rz*math.sin(a))
bm=bmesh.new();bm.from_mesh(hull.data);bmesh.ops.reverse_faces(bm,faces=[f for f in bm.faces if len(f.verts)>100]);bm.to_mesh(hull.data);bm.free();hull.data.update()
bvh=BVHTree.FromPolygons([v.co.copy() for v in hull.data.vertices],[list(p.vertices) for p in hull.data.polygons],all_triangles=False)
def hit_side(sign,y,z,offset):
 p,n,idx,d=bvh.ray_cast(Vector((sign*.45,y,z)),Vector((-sign,0,0)),.9)
 return p+n*offset if p is not None and n.x*sign>.2 else None
for colname in ['P7_Armor','P7_Decals','P7_WindowsDoors']:
 for ob in bpy.data.collections[colname].objects:
  if ob.type!='MESH':continue
  used={i for p in ob.data.polygons for i in p.vertices}
  if ob.name.startswith('Upper_Armor'):
   for i in used:
    v=ob.data.vertices[i];p,n,idx,d=bvh.ray_cast(Vector((v.co.x,v.co.y,.12)),Vector((0,0,-1)),.3)
    if p is not None:v.co=p+n*.00085
  elif ob.name.startswith(('Side_Armor','Gold_Hull_Ribbon','Lower_Silver_Chine','Cargo_Door_Panel','Service_Access','Alterra_Hull')):
   if ob.name.startswith('Side_Armor'):sign=int(ob.name.split('_')[2])
   else:sign=-1 if '_-1' in ob.name else 1
   offset=.0018 if ob.name.startswith('Alterra') else .00115 if ob.name.startswith('Gold') else .0010
   for i in used:
    v=ob.data.vertices[i];p=hit_side(sign,v.co.y,v.co.z,offset)
    if p is not None:v.co=p
  ob.data.update()
# All main coating groups use the actual accepted local generative output lineage.
bound=[]
for mat in bpy.data.materials:
 group=mat.get('AI_MATERIAL_GROUP')
 if not group:continue
 nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');coord=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeMapping');mapping.inputs['Scale'].default_value=(8,8,8);links.new(coord.outputs['Object'],mapping.inputs['Vector'])
 textures={}
 for channel in ['BaseColor','Roughness','Metallic','Height']:
  path=root/'04_PBR_Materials'/f'{group}_{channel}_4096.png';assert path.exists();im=bpy.data.images.load(str(path),check_existing=True)
  if channel!='BaseColor':im.colorspace_settings.name='Non-Color'
  tex=nodes.new('ShaderNodeTexImage');tex.name='AI_'+channel;tex.label='Local TinySD derived '+group+' '+channel;tex.image=im;tex.projection='BOX';tex.projection_blend=.22;links.new(mapping.outputs['Vector'],tex.inputs['Vector']);textures[channel]=tex
 links.new(textures['BaseColor'].outputs['Color'],bs.inputs['Base Color'])
 rough=nodes.new('ShaderNodeMath');rough.name='P7_Roughness_Adjust';rough.operation='MULTIPLY';rough.inputs[1].default_value=1;rough.use_clamp=True;links.new(textures['Roughness'].outputs['Color'],rough.inputs[0]);links.new(rough.outputs[0],bs.inputs['Roughness'])
 metal=nodes.new('ShaderNodeMath');metal.name='P7_Metallic_Adjust';metal.operation='ADD';metal.inputs[1].default_value=0;metal.use_clamp=True;links.new(textures['Metallic'].outputs['Color'],metal.inputs[0]);links.new(metal.outputs[0],bs.inputs['Metallic'])
 bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.000045;links.new(textures['Height'].outputs['Color'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
 mat['GENERATIVE_AI_SOURCE']='segmind/tiny-sd; local CPU img2img; see AI_PBR_Provenance.json';bound.append({'material':mat.name,'group':group,'projection':'object-space triplanar','maps':[t.image.filepath for t in textures.values()]})
(root/'09_Report/AI_Material_Bindings.json').write_text(json.dumps(bound,indent=2))
# Dark machinery remains navy/gunmetal instead of featureless black.
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.25
for light in bpy.data.collections['P7_Lighting'].objects:
 if light.type=='LIGHT' and light.name.endswith('Fill'):light.data.energy=13
s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64;s.render.threads_mode='FIXED';s.render.threads=4;s.render.film_transparent=True;s.render.resolution_percentage=100;s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8'
s.camera=bpy.data.objects['Front_ThreeQuarter'];s.render.resolution_x=2048;s.render.resolution_y=1528
# Render the new body only. The original P5 per-view ion layers are composited next.
beauty=s.view_layers['Beauty'];beauty.layer_collection.children['Ion_Thrusters_3D'].exclude=True
s.render.filepath=str(root/'06_Preview/P7_AI_Front_2048_Body.png');s['P7_status']='Local generative AI material groups bound. New quad hull, independent windows/doors/armor/engines, exact supplied Alterra decals.'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_P7_AI_Rebuild_Standard.blend'))
bpy.ops.render.render(write_still=True)
stats={'groups':len(provenance),'ai_materials_bound':len(bound),'collections':{},'raw_faces':0,'evaluated_triangles':0}
deps=bpy.context.evaluated_depsgraph_get()
for col in bpy.data.collections:
 if not col.name.startswith('P7_'):continue
 stats['collections'][col.name]=len(col.objects)
 for ob in col.objects:
  if ob.type=='MESH':stats['raw_faces']+=len(ob.data.polygons)
  if ob.type in ['MESH','CURVE','FONT']:
   ev=ob.evaluated_get(deps);me=ev.to_mesh();stats['evaluated_triangles']+=sum(len(p.vertices)-2 for p in me.polygons);ev.to_mesh_clear()
(root/'09_Report/P7_Complete_Model_Stats.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats),flush=True)
