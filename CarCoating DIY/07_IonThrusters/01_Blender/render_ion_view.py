import bpy,pathlib,json,sys,time,hashlib
root=pathlib.Path(__file__).resolve().parents[1];args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
view=args[0] if args else 'Rear_ThreeQuarter';width=int(args[1]) if len(args)>1 else 8000
bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_IonThrusters_v02.blend'))
s=bpy.context.scene;s.render.threads_mode='FIXED';s.render.threads=4;s.render.resolution_percentage=100
s.render.engine='CYCLES' if '--cpu' in args else 'BLENDER_EEVEE_NEXT'
if s.render.engine=='CYCLES':s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=False
else:s.eevee.taa_render_samples=64
records=json.loads((root.parent/'06_Reports/starship_souvenir_8000_Render_Stats.json').read_text());record=next(r for r in records['views'] if f'_{view}_8000' in r['file']);original_cameras=json.loads((root/'05_Report/Device_Detection.json').read_text())['cameras']
s.camera=bpy.data.objects[view];pad=round(width*.06);h=round(record['height']*width/8000);s.camera.data.ortho_scale=original_cameras[view]['ortho_scale']*(width+2*pad)/width
s.render.resolution_x=width+2*pad;s.render.resolution_y=h+2*pad
s.view_layers['Beauty'].use=False;s.view_layers['ThrusterOnly_Occluded'].use=True
outdir=root/('04_ThrusterOnly' if width>=8000 else '02_Preview');s.render.filepath=str(outdir/f'{view}_ThrusterRaw_{width}.png')
if pathlib.Path(s.render.filepath).exists():raise RuntimeError('Output exists; refusing overwrite '+s.render.filepath)
t=time.time();fallback=None
try:bpy.ops.render.render(write_still=True)
except Exception as e:
 fallback=str(e);s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=False;bpy.ops.render.render(write_still=True)
info={'view':view,'nominal_width':width,'render_width':s.render.resolution_x,'render_height':s.render.resolution_y,'engine':s.render.engine,'seconds':time.time()-t,'thread_limit':4,'fallback_error':fallback,'raw':s.render.filepath,'padding_per_side':pad,'camera_pose_preserved':True}
(root/'05_Report'/f'{view}_{width}_Render.json').write_text(json.dumps(info,indent=2));print(json.dumps(info),flush=True)
