import bpy,pathlib,json
from mathutils import Vector
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_P8_Crash_Editable_v03.blend'));s=bpy.context.scene
s.eevee.volumetric_samples=256;s.eevee.taa_render_samples=96;s.eevee.volumetric_start=1.8;s.eevee.volumetric_end=3.05;s.eevee.volumetric_sample_distribution=0
for m in bpy.data.materials:
 if not m.name.startswith(('P8_Amber','P8_Hot','P8_Soft')):continue
 pv=next(v for v in m.node_tree.nodes if v.type=='PRINCIPLED_VOLUME');density=pv.inputs['Density'].links[0].from_node;emission=pv.inputs['Emission Strength'].links[0].from_node
 if 'Ion' in m.name:density.inputs[1].default_value=4;emission.inputs[1].default_value=3;pv.inputs['Emission Color'].default_value=(.006,.32,1,1)
 elif 'Amber' in m.name:density.inputs[1].default_value=15;emission.inputs[1].default_value=26;pv.inputs['Emission Color'].default_value=(1,.18,.008,1)
 else:density.inputs[1].default_value=15;emission.inputs[1].default_value=45;pv.inputs['Emission Color'].default_value=(1,.65,.08,1)
s.camera=bpy.data.objects['Front_ThreeQuarter'];s.render.filepath=str(root/'06_Preview/Aurora_P8_Front_ThreeQuarter_2048.png');s['P8_version']='Final preview candidate; only two 2048 full views, no 8K batch.'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_P8_Crash_Editable.blend'))
bpy.data.libraries.write(str(root/'02_Geometry/Aurora_P8_SourceContour_Geometry.blend'),{bpy.data.collections['P8_OriginalContour_Hull'],bpy.data.collections['P8_Engine_Details'],bpy.data.collections['P8_Decals']},fake_user=True,compress=True)
bpy.data.libraries.write(str(root/'05_Effects/Aurora_P8_Editable_Effects.blend'),{bpy.data.collections['P8_Smoke'],bpy.data.collections['P8_Fire'],bpy.data.collections['P8_Ion']},fake_user=True,compress=True)
for view in ['Front_ThreeQuarter','Rear_ThreeQuarter']:
 s.camera=bpy.data.objects[view];s.render.filepath=str(root/'06_Preview'/f'Aurora_P8_{view}_2048.png');bpy.ops.render.render(write_still=True)
# Source structure inspection from front, rear, port and starboard. No added pedestal.
for c in ['P8_Smoke','P8_Fire','P8_Ion']:s.view_layers['Beauty'].layer_collection.children[c].exclude=True
cam=bpy.data.objects.new('P8_Bridge_Inspection',bpy.data.cameras.new('P8_Bridge_Inspection'));s.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=.29;s.camera=cam;s.render.resolution_x=1400;s.render.resolution_y=1000
for label,offset in [('Front',(0,-.6,.20)),('Rear',(0,.6,.20)),('Port',(.6,0,.10)),('Starboard',(-.6,0,.10))]:
 center=Vector((0,.105,.105));cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(root/'06_Preview'/f'Bridge_Connection_{label}_1400.png');bpy.ops.render.render(write_still=True)
print('FINAL SCENE AND STRUCTURE VIEWS COMPLETE',flush=True)
