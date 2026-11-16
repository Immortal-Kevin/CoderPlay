import bpy,pathlib,json,hashlib,struct
root=pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'01_Blender/Aurora_P7_AI_Rebuild_Standard_v03.blend'))
s=bpy.context.scene
s.view_layers['Beauty'].layer_collection.children['Ion_Thrusters_3D'].exclude=False
s.camera=bpy.data.objects['Front_ThreeQuarter']
s.render.resolution_x=2048;s.render.resolution_y=1528;s.render.resolution_percentage=100
s.render.threads_mode='FIXED';s.render.threads=4;s.render.film_transparent=True
s['P7_FINAL_WORKFLOW']='Editable 3D P5 ion objects retained. Delivered PNG: render body only with render_p7.py, alpha-over matching original P5 IonOnly via compose_render.py for original soft glow.'
s['P7_AI_PROVENANCE']='Local TinySD CPU img2img; accepted 384px outputs authored into 4K PBR. No native 4K diffusion claim.'
missing=[{'name':im.name,'path':im.filepath} for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not pathlib.Path(bpy.path.abspath(im.filepath)).exists()]
bpy.ops.file.pack_all()
path=root/'01_Blender/Aurora_P7_AI_Rebuild_Editable_Final.blend'
if path.exists():raise RuntimeError('Refusing overwrite')
bpy.ops.wm.save_as_mainfile(filepath=str(path))
components={c for c in bpy.data.collections if c.name.startswith('P7_') and c.name!='P7_Lighting'}
bpy.data.libraries.write(str(root/'02_Geometry/P7_Independent_Components.blend'),components,fake_user=True,compress=True)
bindings={m.name:{'group':m.get('AI_MATERIAL_GROUP'),'images':sorted(set(n.image.name for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image))} for m in bpy.data.materials if m.use_nodes and m.get('AI_MATERIAL_GROUP')}
for mat in bpy.data.materials:
 if not mat.get('AI_MATERIAL_GROUP'):continue
 nodes=mat.node_tree.nodes;nodes['P7_Roughness_Adjust'].inputs[1].default_value=.72;nodes['P7_Metallic_Adjust'].inputs[1].default_value=.06 if mat['AI_MATERIAL_GROUP']=='WhiteArmor' else .10
 if 'P7_Roughness_Adjust_Dark' in nodes:nodes['P7_Roughness_Adjust_Dark'].inputs[1].default_value=.72;nodes['P7_Metallic_Adjust_Dark'].inputs[1].default_value=.10
 bs=nodes.get('Principled BSDF');bs.inputs['Coat Weight'].default_value=.42;bs.inputs['Coat Roughness'].default_value=.10
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.31
bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/Aurora_P7_AI_Rebuild_Metallic_Final.blend'))
bpy.ops.wm.open_mainfile(filepath=str(path))
s=bpy.context.scene;s.view_layers['Beauty'].layer_collection.children['Ion_Thrusters_3D'].exclude=True
s.render.resolution_x=512;s.render.resolution_y=382;s.render.filepath=str(root/'06_Preview/Editable_Final_Reopen_512.png')
bpy.ops.render.render(write_still=True)
validation={'reopened':str(path),'missing_images_before_pack':missing,'packed_images':sum(bool(i.packed_file) for i in bpy.data.images),'bindings':bindings,'reopen_render':s.render.filepath,'engine':s.render.engine,'threads':s.render.threads,'ion_objects_preserved':len(bpy.data.collections['Ion_Thrusters_3D'].objects)}
def ion_snapshot():
 result={}
 for ob in bpy.data.collections['Ion_Thrusters_3D'].all_objects:
  if ob.type!='MESH':continue
  vals=[v for row in ob.matrix_world for v in row]+[v for vert in ob.data.vertices for v in vert.co]
  result[ob.name]=hashlib.sha256(struct.pack('<'+'d'*len(vals),*vals)).hexdigest()
 return result
after=ion_snapshot()
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'07_IonThrusters/01_Blender/Aurora_IonThrusters_Editable.blend'))
before=ion_snapshot();validation['p5_ion_geometry_worldtransform_identical']=before==after;validation['p5_ion_mesh_count']=len(before)
(root/'09_Report/Editable_Final_Validation.json').write_text(json.dumps(validation,indent=2))
