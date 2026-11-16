import bpy,pathlib,json,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
def fingerprint(mat):
 data=[]
 for n in mat.node_tree.nodes:
  values=[]
  for sock in n.inputs:
   if not hasattr(sock,'default_value'):continue
   v=sock.default_value
   try:v=list(v)
   except:pass
   if isinstance(v,(float,int,str,bool,list)):values.append([sock.name,v])
  row={'name':n.name,'type':n.bl_idname,'inputs':values}
  if n.type=='TEX_IMAGE':row['image']=hashlib.sha256(n.image.packed_file.data).hexdigest() if n.image.packed_file else n.image.filepath
  data.append(row)
 links=sorted((l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in mat.node_tree.links)
 return hashlib.sha256(json.dumps({'nodes':data,'links':links},sort_keys=True).encode()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_IonThrusters_Editable.blend'))
ship=next(o for o in bpy.data.collections['Original_Ship_UNMODIFIED'].objects if o.type=='MESH');p5=fingerprint(ship.data.materials[0]);o=bpy.data.objects['Port_Upper_Plasma'];master=bpy.data.objects['ION_MASTER_PARAMETERS'];before=o.evaluated_get(bpy.context.evaluated_depsgraph_get()).scale.y
master['LengthScale']=1.2;master.update_tag();bpy.context.view_layer.update();after=o.evaluated_get(bpy.context.evaluated_depsgraph_get()).scale.y
drivers_ok=abs(after-before*1.2)<1e-6
packed=sum(bool(im.packed_file) for im in bpy.data.images)
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'02_Models/starship_souvenir/starship_souvenir_FourViews.blend'));original=next(o for o in bpy.context.scene.objects if o.type=='MESH');prior=fingerprint(original.data.materials[0])
(root/'05_Report/Editable_Validation.json').write_text(json.dumps({'blend_reopened':True,'packed_images':packed,'length_driver_default':before,'length_driver_at_1_2':after,'length_driver_works':drivers_ok,'p4_material_sha256':prior,'p5_material_sha256':p5,'original_material_nodes_and_images_unchanged':p5==prior},indent=2))
