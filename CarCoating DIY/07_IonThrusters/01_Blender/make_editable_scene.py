import bpy,pathlib,json,hashlib,struct
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_IonThrusters_v02.blend'))
s=bpy.context.scene;master=bpy.data.objects['ION_MASTER_PARAMETERS']
for key,val in [('LengthScale',1.0),('RadiusScale',1.0),('Brightness',1.0),('OpacityScale',1.0)]:
 master[key]=val;master.id_properties_ui(key).update(min=.1,max=3,description='Editable ion effect multiplier; default 1 preserves approved v02 appearance')
def driver(target,prop,index,key,expr):
 fc=target.driver_add(prop,index) if index is not None else target.driver_add(prop);d=fc.driver;d.type='SCRIPTED';v=d.variables.new();v.name='control';v.type='SINGLE_PROP';v.targets[0].id=master;v.targets[0].data_path='["'+key+'"]';d.expression=expr
for obj in bpy.data.collections['Ion_Thrusters_3D'].objects:
 if obj.type!='MESH':continue
 for axis in [0,2]:driver(obj,'scale',axis,'RadiusScale',f'{obj.scale[axis]:.10g}*control')
 driver(obj,'scale',1,'LengthScale',f'{obj.scale[1]:.10g}*control')
 offset=obj.location.y-.33250665;driver(obj,'location',1,'LengthScale',f'.33250665+{offset:.10g}*control')
for name in ['Ion_CoolWhite_Cyan_Core','Ion_Cyan_Blue_Plasma','Ion_Soft_Blue_Halo']:
 nodes=bpy.data.materials[name].node_tree.nodes
 em=next(n for n in nodes if n.type=='EMISSION');val=em.inputs['Strength'].default_value;driver(em.inputs['Strength'],'default_value',None,'Brightness',f'{val:.8g}*control')
 gain=[n for n in nodes if n.type=='MATH' and n.operation=='MULTIPLY'][-1];val=gain.inputs[1].default_value;driver(gain.inputs[1],'default_value',None,'OpacityScale',f'min(1,{val:.8g}*control)')
cameras=json.loads((root/'05_Report/Device_Detection.json').read_text())['cameras'];stats=json.loads((root.parent/'06_Reports/starship_souvenir_8000_Render_Stats.json').read_text())
for view in stats['views']:
 label=next(k for k in ['Left','Right','Front_ThreeQuarter','Rear_ThreeQuarter'] if '_'+k+'_8000' in view['file']);cam=bpy.data.objects[label];cam.data.ortho_scale=cameras[label]['ortho_scale']*1.12;cam['render_width']=8960;cam['render_height']=view['height']+960;cam['nominal_final_width']=8000
s.camera=bpy.data.objects['Rear_ThreeQuarter'];s.render.resolution_x=8960;s.render.resolution_y=6683;s.view_layers['Beauty'].use=True;s.view_layers['ThrusterOnly_Occluded'].use=False;s.render.filepath=str(root/'02_Preview/Editable_Beauty_Render.png')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_IonThrusters_Editable.blend'))
# Verify original ship geometry/UV/material data against the prior project.
def digest(obj):
 h=hashlib.sha256()
 for v in obj.data.vertices:h.update(struct.pack('<3f',*v.co))
 for p in obj.data.polygons:h.update(struct.pack('<'+str(len(p.vertices))+'I',*p.vertices))
 for uv in obj.data.uv_layers.active.data:h.update(struct.pack('<2f',*uv.uv))
 return h.hexdigest()
ship=next(o for o in bpy.data.collections['Original_Ship_UNMODIFIED'].objects if o.type=='MESH');actual=digest(ship);material_names=[m.name for m in ship.data.materials]
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'02_Models/starship_souvenir/starship_souvenir_FourViews.blend'));old=next(o for o in bpy.context.scene.objects if o.type=='MESH');expected=digest(old)
(root/'05_Report/Ship_Integrity.json').write_text(json.dumps({'original_geometry_uv_sha256':expected,'p5_geometry_uv_sha256':actual,'geometry_uv_identical':actual==expected,'original_material_names':[m.name for m in old.data.materials],'p5_material_names':material_names,'final_ship_plate':'Original P4 PNG used, not re-shaded'},indent=2))
