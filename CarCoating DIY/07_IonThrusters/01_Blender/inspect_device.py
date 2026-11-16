import bpy,gpu,json,pathlib,time
root=pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'02_Models/starship_souvenir/starship_souvenir_FourViews.blend'))
s=bpy.context.scene;s.render.threads_mode='FIXED';s.render.threads=4
info={'blender':bpy.app.version_string,'gpu_platform':{}}
for key in ['vendor_get','renderer_get','version_get','backend_type_get','device_type_get']:
 try:info['gpu_platform'][key]=getattr(gpu.platform,key)()
 except Exception as e:info['gpu_platform'][key]=str(e)
p=bpy.context.preferences.addons['cycles'].preferences
try:
 p.compute_device_type='ONEAPI';p.get_devices();info['cycles_devices']=[{'name':d.name,'type':d.type,'id':d.id} for d in p.devices]
except Exception as e:info['oneapi_error']=str(e)
mesh=next(o for o in s.objects if o.type=='MESH')
verts=[list(v.co) for v in mesh.data.vertices]
(root/'05_Report/mesh_vertices.json').write_text(json.dumps(verts))
info['cameras']={o.name:{'position':list(o.location),'rotation':list(o.rotation_euler),'ortho_scale':o.data.ortho_scale} for o in s.objects if o.type=='CAMERA'}
s.camera=bpy.data.objects['Rear_ThreeQuarter'];s.render.engine='BLENDER_EEVEE_NEXT';s.render.resolution_x=1024;s.render.resolution_y=733;s.render.resolution_percentage=100;s.render.image_settings.color_mode='RGBA';s.render.filepath=str(root/'02_Preview/DeviceTest_EEVEE_1024.png')
t=time.time()
try:bpy.ops.render.render(write_still=True);info['eevee_test']={'success':True,'seconds':time.time()-t}
except Exception as e:info['eevee_test']={'success':False,'error':str(e),'seconds':time.time()-t}
(root/'05_Report/Device_Detection.json').write_text(json.dumps(info,indent=2))
print(json.dumps(info,indent=2),flush=True)
