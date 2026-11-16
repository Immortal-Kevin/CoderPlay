import bpy,pathlib,json,sys,time
root=pathlib.Path(__file__).resolve().parents[1];args=sys.argv[sys.argv.index('--')+1:];view=args[0];width=int(args[1]);variant=args[2] if len(args)>2 else 'Standard'
bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_P7_AI_Rebuild_Standard_v03.blend'));s=bpy.context.scene
if variant.startswith('Metallic'):
 for mat in bpy.data.materials:
  if not mat.get('AI_MATERIAL_GROUP'):continue
  nodes=mat.node_tree.nodes;nodes['P7_Roughness_Adjust'].inputs[1].default_value=.72;nodes['P7_Metallic_Adjust'].inputs[1].default_value=.06 if mat['AI_MATERIAL_GROUP']=='WhiteArmor' else .10
  if 'P7_Roughness_Adjust_Dark' in nodes:nodes['P7_Roughness_Adjust_Dark'].inputs[1].default_value=.72;nodes['P7_Metallic_Adjust_Dark'].inputs[1].default_value=.10
  bs=nodes.get('Principled BSDF');bs.inputs['Coat Weight'].default_value=.42;bs.inputs['Coat Roughness'].default_value=.10
 s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.31
if variant=='P6_Control':
 for col in s.view_layers['Beauty'].layer_collection.children:
  if col.name.startswith('P7_') and col.name!='P7_Lighting':col.exclude=True
 s.view_layers['Beauty'].layer_collection.children['P6_HD_Archive'].exclude=False
s.view_layers['Beauty'].layer_collection.children['Ion_Thrusters_3D'].exclude=True
s.camera=bpy.data.objects[view];s.render.resolution_x=width;s.render.resolution_y=round((5967 if 'Quarter' in view else 4458)*width/8000);s.render.resolution_percentage=100;s.render.threads_mode='FIXED';s.render.threads=4;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64;s.render.film_transparent=True
folder=root/'06_Preview' if width<8000 else root/'02_Geometry/RenderLayers';folder.mkdir(parents=True,exist_ok=True);path=folder/f'{variant}_{view}_{width}_Body.png'
if path.exists():raise RuntimeError('Refusing overwrite '+str(path))
s.render.filepath=str(path);t=time.time();error=None
try:bpy.ops.render.render(write_still=True)
except Exception as e:
 error=str(e);s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=False;bpy.ops.render.render(write_still=True)
(root/'09_Report'/f'Render_{variant}_{view}_{width}.json').write_text(json.dumps({'view':view,'variant':variant,'size':[width,s.render.resolution_y],'engine':s.render.engine,'seconds':time.time()-t,'threads':4,'fallback_error':error,'raw_body':str(path)},indent=2));print('P7 RENDER COMPLETE',flush=True)
