import bpy,pathlib,json,sys,time
root=pathlib.Path(__file__).resolve().parents[1];args=sys.argv[sys.argv.index('--')+1:];view=args[0];width=int(args[1]);original='original' in args
bpy.ops.wm.open_mainfile(filepath=str(root/'01_Geometry/Aurora_HD_Remaster_Editable.blend'));s=bpy.context.scene;s.render.threads_mode='FIXED';s.render.threads=4;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64;s.render.resolution_percentage=100;s.render.film_transparent=True
for vl in s.view_layers:
 vl.use=vl.name=='Beauty';vl.layer_collection.children['HD_Remaster_Ship'].exclude=original;vl.layer_collection.children['P5_Original_Archived'].exclude=not original;vl.layer_collection.children['Ion_Thrusters_3D'].exclude=True;vl.layer_collection.children['Ship_Occlusion_ONLY'].exclude=True
s.camera=bpy.data.objects[view];height8000=5967 if 'Quarter' in view else 4458;s.render.resolution_x=width;s.render.resolution_y=round(height8000*width/8000);s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8'
label='Original' if original else 'HD';s.render.filepath=str(root/'04_Comparison'/f'{label}_{view}_{width}_Body.png')
if pathlib.Path(s.render.filepath).exists():raise RuntimeError('Refusing overwrite '+s.render.filepath)
t=time.time();fallback=None
try:bpy.ops.render.render(write_still=True)
except Exception as e:
 fallback=str(e);s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=False;bpy.ops.render.render(write_still=True)
(root/'06_Report'/f'{label}_{view}_{width}_Render.json').write_text(json.dumps({'view':view,'width':width,'height':s.render.resolution_y,'engine':s.render.engine,'seconds':time.time()-t,'threads':4,'fallback':fallback,'original':original,'body':s.render.filepath},indent=2));print('P6 RENDER COMPLETE',flush=True)
