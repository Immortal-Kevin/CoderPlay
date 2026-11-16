import bpy,pathlib,json,math
from mathutils import Vector
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root/'01_Geometry/Aurora_HD_Geometry_v02.blend'));s=bpy.context.scene;col=bpy.data.collections['HD_Remaster_Ship'];rings=json.loads((root/'06_Report/Ring_Repair.json').read_text())['rings']
shell=bpy.data.materials['HD_Port_Gray_Alloy']
for ring in rings:
 c=Vector(ring['center']);n=Vector(ring['normal']);t=Vector((0,0,1)).cross(n).normalized();u=n.cross(t);N=128;profile=[(.03065,-.014),(.03075,-.0015),(.0305,-.0005),(ring['radius'],.00005)];v=[];f=[]
 for r,d in profile:
  for j in range(N):a=2*math.pi*j/N;v.append(c+n*d+t*r*math.cos(a)+u*r*math.sin(a))
 for k in range(len(profile)-1):
  for j in range(N):f.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
 me=bpy.data.meshes.new('Curved_Port_Base_128');me.from_pydata(v,[],f);me.update();ob=bpy.data.objects.new('HD_Round_Base_'+str(ring['side']),me);col.objects.link(ob);me.materials.append(shell)
 for p in me.polygons:p.use_smooth=True
mat=bpy.data.materials.new('Aurora_HD_4096_PBR');mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
for filename,socket,noncolor in [('Aurora_BaseColor_4096.png','Base Color',False),('Aurora_Roughness_4096.png','Roughness',True),('Aurora_Metallic_4096.png','Metallic',True),('Aurora_Emission_4096.png','Emission Color',False)]:
 im=bpy.data.images.load(str(root/'02_Textures'/filename),check_existing=True);tex=n.new('ShaderNodeTexImage');tex.image=im
 if noncolor:im.colorspace_settings.name='Non-Color'
 l.new(tex.outputs['Color'],bs.inputs[socket])
bs.inputs['Emission Strength'].default_value=.35
im=bpy.data.images.load(str(root/'02_Textures/Aurora_Normal_4096.png'));im.colorspace_settings.name='Non-Color';tex=n.new('ShaderNodeTexImage');tex.image=im;normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.55;l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs['Normal'])
hull=bpy.data.objects['Aurora_HD_Hull'];hull.data.materials.clear();hull.data.materials.append(mat)
# Archived original remains available and hidden; tail objects/drivers are untouched.
for layer in s.view_layers:
 layer.layer_collection.children['P5_Original_Archived'].exclude=True;layer.layer_collection.children['Ship_Occlusion_ONLY'].exclude=True;layer.use=layer.name=='Beauty'
stats={'original_vertices':3723,'original_faces':4471,'remaster_objects':[]}
for o in col.objects:
 if o.type=='MESH':stats['remaster_objects'].append({'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons)})
stats['remaster_vertices']=sum(o['vertices'] for o in stats['remaster_objects']);stats['remaster_faces']=sum(o['faces'] for o in stats['remaster_objects']);stats['remaster_triangles']=sum(o['triangles'] for o in stats['remaster_objects']);stats['tail_objects']=len([o for o in bpy.data.collections['Ion_Thrusters_3D'].objects if o.type=='MESH'])
(root/'06_Report/Remaster_Model_Stats.json').write_text(json.dumps(stats,indent=2))
s['P6_notes']='12-segment ports rebuilt as 128 radial /16 annulus sections. Local hull Phong tessellation only. Source original archived hidden. P5 thrusters retained. 4096 source-aware PBR remaster, no AI.'
s.render.threads_mode='FIXED';s.render.threads=4;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8';s.render.resolution_percentage=100;s.render.film_transparent=True
s.camera=bpy.data.objects['Rear_ThreeQuarter'];s.render.resolution_x=2048;s.render.resolution_y=1528;s.render.filepath=str(root/'04_Comparison/Aurora_HD_Rear_2048_Raw.png')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Geometry/Aurora_HD_Remaster_Editable.blend'))
# Macro comparison uses exactly Stage1's camera and light settings.
cam=bpy.data.objects.new('Ring_Final_Comparison',bpy.data.cameras.new('Ring_Final_Comparison'));s.collection.objects.link(cam);c=Vector(rings[0]['center']);a=Vector(rings[0]['normal']);cam.location=c+a*.18+Vector((0,-.055,.035));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.078;s.camera=cam;s.render.resolution_x=1800;s.render.resolution_y=1800;s.view_layers['Beauty'].layer_collection.children['Ion_Thrusters_3D'].exclude=True;s.render.filepath=str(root/'04_Comparison/Ring_HD_Final_1800.png');bpy.ops.render.render(write_still=True)
print(json.dumps(stats),flush=True)
