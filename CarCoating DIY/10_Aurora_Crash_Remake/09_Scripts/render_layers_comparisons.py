import bpy,pathlib,json,time,sys
from mathutils import Matrix
root=pathlib.Path(__file__).resolve().parents[1];final=root/'01_Blender/Aurora_P8_Crash_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(final));s=bpy.context.scene;vl=s.view_layers['Beauty'];refs={v:{'matrix':[list(row) for row in bpy.data.objects[v].matrix_world],'scale':bpy.data.objects[v].data.ortho_scale} for v in ['Front_ThreeQuarter','Rear_ThreeQuarter']}
def render(path):
 s.render.filepath=str(path);t=time.time();bpy.ops.render.render(write_still=True);return time.time()-t
times=[]
bodycols=['P8_OriginalContour_Hull','P8_Engine_Details','P8_Decals'];fxcols=['P8_Smoke','P8_Fire','P8_Ion']
for view in refs:
 s.camera=bpy.data.objects[view]
 for c in fxcols:vl.layer_collection.children[c].exclude=True
 times.append({'view':view,'pass':'Body','seconds':render(root/'05_Effects'/f'Body_{view}_2048.png')})
 for kind in ['Smoke','Fire','Ion']:
  for c in fxcols:vl.layer_collection.children[c].exclude=c!='P8_'+kind
  for c in bodycols:vl.layer_collection.children[c].holdout=True
  times.append({'view':view,'pass':kind,'seconds':render(root/'05_Effects'/f'{kind}_Occluded_{view}_2048.png')})
  for c in bodycols:vl.layer_collection.children[c].holdout=False
 for c in fxcols:vl.layer_collection.children[c].exclude=False
validation={'path':str(final),'reopen_success':True,'missing_images':[i.filepath for i in bpy.data.images if i.source=='FILE' and not i.packed_file and not pathlib.Path(bpy.path.abspath(i.filepath)).exists()],'packed_images':sum(bool(i.packed_file) for i in bpy.data.images),'engine':s.render.engine,'threads':s.render.threads,'volume_samples':s.eevee.volumetric_samples,'body_objects':sum(len(bpy.data.collections[c].objects) for c in bodycols),'fx_objects':{c:len([o for o in bpy.data.collections[c].objects if o.type=='MESH']) for c in fxcols},'p7_objects_in_visible_collections':[o.name for c in bodycols for o in bpy.data.collections[c].objects if o.name.startswith('P7_')]}
# Compare every model under the SAME P8 cameras, world, lights, image size and no FX.
for version,source in [('P6',root.parent/'08_Aurora_HD_Remaster/01_Geometry/Aurora_HD_Remaster_Editable.blend'),('P7',root.parent/'09_Aurora_AI_Rebuild/01_Blender/Aurora_P7_AI_Rebuild_Editable_Final.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
 for o in s.objects:
  if o.type=='LIGHT':o.hide_render=True
 with bpy.data.libraries.load(str(final),link=False) as (a,b):b.worlds=['P8_Studio_World'];b.objects=['P8_Key','P8_Fill','P8_Rim']
 s.world=b.worlds[0]
 for o in b.objects:s.collection.objects.link(o)
 for layer in s.view_layers:
  layer.use=layer.name=='Beauty'
  if 'Ion_Thrusters_3D' in layer.layer_collection.children:layer.layer_collection.children['Ion_Thrusters_3D'].exclude=True
 s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=96;s.render.threads_mode='FIXED';s.render.threads=4;s.render.resolution_x=2048;s.render.resolution_y=1528;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8'
 for view,camera in refs.items():
  cam=bpy.data.objects[view];cam.matrix_world=Matrix(camera['matrix']);cam.data.ortho_scale=camera['scale'];s.camera=cam;times.append({'version':version,'view':view,'seconds':render(root/'07_Comparison'/f'{version}_{view}_SameCameraLight_2048.png')})
(root/'08_Report/Reopen_Render_Validation.json').write_text(json.dumps(validation,indent=2));(root/'08_Report/Render_Times.json').write_text(json.dumps(times,indent=2));(root/'08_Report/Comparison_Cameras.json').write_text(json.dumps(refs,indent=2))
print('LAYERS AND MATCHED COMPARISONS COMPLETE',flush=True)
