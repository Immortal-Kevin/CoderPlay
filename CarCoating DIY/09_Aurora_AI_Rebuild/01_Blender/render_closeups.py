import bpy,pathlib,json
from mathutils import Vector
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_P7_AI_Rebuild_Standard.blend'));s=bpy.context.scene;s.render.threads_mode='FIXED';s.render.threads=4;s.render.resolution_percentage=100;s.render.resolution_x=1800;s.render.resolution_y=1500
beauty=s.view_layers['Beauty'];cam=bpy.data.objects.new('P7_Inspection_Camera',bpy.data.cameras.new('P7_Inspection_Camera'));s.collection.objects.link(cam);cam.data.type='ORTHO';s.camera=cam
def point(center,offset,scale):
 c=Vector(center);cam.location=c+Vector(offset);cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
def render(name):s.render.filepath=str(root/'06_Preview'/f'{name}_1800.png');bpy.ops.render.render(write_still=True)
point((.120033,.26,.04499),(.24,.16,.10),.245);render('Engine_P7')
for col in beauty.layer_collection.children:
 if col.name.startswith('P7_') and col.name!='P7_Lighting':col.exclude=True
beauty.layer_collection.children['P6_HD_Archive'].exclude=False;render('Engine_P6_SameLight')
for col in beauty.layer_collection.children:
 if col.name.startswith('P7_'):col.exclude=False
beauty.layer_collection.children['P6_HD_Archive'].exclude=True;beauty.layer_collection.children['Ion_Thrusters_3D'].exclude=True
for sign in [1,-1]:
 for objname,label,scale in [('Alterra_Hull_'+str(sign),'Logo_Hull_'+str(sign),.078),('Alterra_TopFin_'+str(sign),'Logo_TopFin_'+str(sign),.054)]:
  ob=bpy.data.objects[objname];pts=[ob.matrix_world@v.co for v in ob.data.vertices];c=sum(pts,Vector())/len(pts);point(c,(.24*sign,-.025*sign,.025),scale);render(label)
point((.14,.063,-.015),(.3,-.025,.05),.115);render('Cargo_Door_and_Windows')
# Save a complete, editable beauty project with the retained 3D P5 ion objects.
s.camera=bpy.data.objects['Front_ThreeQuarter'];s.render.resolution_x=2048;s.render.resolution_y=1528;beauty.layer_collection.children['Ion_Thrusters_3D'].exclude=False;s.render.filepath=str(root/'06_Preview/Editable_Beauty_Raw.png');bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_P7_AI_Rebuild_Editable.blend'))
# Save an independent metallic material variant, without changing Standard.
for mat in bpy.data.materials:
 if not mat.get('AI_MATERIAL_GROUP'):continue
 mat.node_tree.nodes['P7_Roughness_Adjust'].inputs[1].default_value=.72;mat.node_tree.nodes['P7_Metallic_Adjust'].inputs[1].default_value=.06 if mat['AI_MATERIAL_GROUP']=='WhiteArmor' else .10;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Coat Weight'].default_value=.42;bs.inputs['Coat Roughness'].default_value=.10
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.31;bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_P7_AI_Rebuild_Metallic.blend'))
print('CLOSEUPS AND EDITABLE PROJECTS COMPLETE',flush=True)
