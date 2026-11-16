import bpy,pathlib,time,json
root=pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_IonThrusters_v01.blend'))
s=bpy.context.scene;s.render.threads_mode='FIXED';s.render.threads=4
for obj in bpy.data.collections['Ion_Thrusters_3D'].objects:
 if obj.type!='MESH':continue
 if obj.name.endswith('_Plasma'):obj.location.y=.33250665+.026;obj.scale=(.019,.031,.019)
 if obj.name.endswith('_Halo'):obj.location.y=.33250665+.031;obj.scale=(.027,.034,.027)
control=bpy.data.objects['ION_MASTER_PARAMETERS'];control['length_diameters']=1.95;control['length']=.065;control['output_padding_fraction']=.06
params=json.loads((root/'01_Blender/Ion_Parameters.json').read_text());params.update(length_diameters=1.95,length=.065,output_padding_fraction=.06,revision='v02');(root/'01_Blender/Ion_Parameters_v02.json').write_text(json.dumps(params,indent=2))
# Enlarge the image plane, preserving the original camera pose and pixel scale.
s.camera=bpy.data.objects['Rear_ThreeQuarter'];w,h=1600,1145;pad=round(w*.06);s.camera.data.ortho_scale*=((w+2*pad)/w)
s.render.resolution_x=w+2*pad;s.render.resolution_y=h+2*pad;s.render.resolution_percentage=100;s.render.filepath=str(root/'02_Preview/Rear_ThreeQuarter_ThrusterRaw_1600_v02.png')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_IonThrusters_v02.blend'))
t=time.time();bpy.ops.render.render(write_still=True);(root/'05_Report/Preview_v02_Timing.json').write_text(json.dumps({'seconds':time.time()-t,'engine':s.render.engine,'render_dimensions':[s.render.resolution_x,s.render.resolution_y],'nominal_width':1600},indent=2))
