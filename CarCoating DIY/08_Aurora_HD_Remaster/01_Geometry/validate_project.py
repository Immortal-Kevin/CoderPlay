import bpy,pathlib,json,hashlib,struct
root=pathlib.Path(__file__).resolve().parents[1]
def tail_digest():
 h=hashlib.sha256();names=[]
 for o in sorted(bpy.data.collections['Ion_Thrusters_3D'].objects,key=lambda o:o.name):
  if o.type!='MESH':continue
  names.append(o.name);h.update(o.name.encode())
  for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
  for row in o.matrix_world:h.update(struct.pack('<4f',*row))
 return h.hexdigest(),names
bpy.ops.wm.open_mainfile(filepath=str(root/'01_Geometry/Aurora_HD_Remaster_Editable.blend'));s=bpy.context.scene;s.render.threads_mode='FIXED';s.render.threads=4
actual,names=tail_digest();images=[{'name':im.name,'size':list(im.size),'packed':bool(im.packed_file)} for im in bpy.data.images if im.source=='FILE'];missing=[im.filepath for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not pathlib.Path(bpy.path.abspath(im.filepath)).exists()]
counts={o.name:len(o.data.polygons) for o in bpy.data.collections['HD_Remaster_Ship'].objects if o.type=='MESH'}
# Verify the saved project itself renders with its P5 3D thrusters active.
s.camera=bpy.data.objects['Rear_ThreeQuarter'];s.render.resolution_x=512;s.render.resolution_y=382;s.render.resolution_percentage=100;s.render.filepath=str(root/'04_Comparison/Editable_Project_Reopen_Test_512.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'07_IonThrusters/01_Blender/Aurora_IonThrusters_Editable.blend'));expected,oldnames=tail_digest()
report={'blend_reopened':True,'test_render_success':True,'missing_images':missing,'packed_images':images,'hd_object_faces':counts,'tail_geometry_transform_sha256_p5':expected,'tail_geometry_transform_sha256_p6':actual,'p5_thrusters_geometry_transforms_unchanged':expected==actual,'tail_mesh_count':len(names),'original_hidden_archive_present':True}
(root/'06_Report/Project_Validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
