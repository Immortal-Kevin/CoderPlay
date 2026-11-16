import bpy,bmesh,pathlib,json,math
from mathutils import Vector
base=pathlib.Path(__file__).resolve().parents[1];results=[]
for name in ['starship_souvenir','starship_crashed','Aurora_Intact_Atlas2048']:
 folder=base/'02_Models'/name;path=folder/f'{name}_8000.blend'
 if not (base/'06_Reports'/f'{name}_8000_Render_Stats.json').exists():continue
 bpy.ops.wm.open_mainfile(filepath=str(path));scene=bpy.context.scene
 stats=json.loads((base/'06_Reports'/f'{name}_8000_Render_Stats.json').read_text())
 mesh=next(o for o in scene.objects if o.type=='MESH');bounds=[mesh.matrix_world@Vector(c) for c in mesh.bound_box];center=sum(bounds,Vector())/8;radius=(Vector(stats['bounds']['max'])-Vector(stats['bounds']['min'])).length
 missing=[im.filepath for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not pathlib.Path(bpy.path.abspath(im.filepath)).exists()]
 for view in stats['views']:
  label=pathlib.Path(view['file']).name.replace(name+'_','').replace('_8000.png','');data=bpy.data.cameras.new(label);ob=bpy.data.objects.new(label,data);scene.collection.objects.link(ob);data.type='ORTHO';data.clip_end=radius*20;ob.location=center+Vector(view['direction']).normalized()*radius*3;ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
  rotation=ob.rotation_euler.to_matrix().transposed();pts=[rotation@(v-center) for v in bounds];sx=max(v.x for v in pts)-min(v.x for v in pts);sy=max(v.y for v in pts)-min(v.y for v in pts);aspect=view['width']/view['height'];data.ortho_scale=max(sx,sy*aspect)*1.12
  ob['render_width']=view['width'];ob['render_height']=view['height'];ob['render_output']=view['file']
 scene.camera=bpy.data.objects['Left'];scene.render.resolution_x=stats['views'][0]['width'];scene.render.resolution_y=stats['views'][0]['height'];scene.render.filepath=stats['views'][0]['file']
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'{name}_FourViews.blend'))
 rec={'model':name,'blend_opened':True,'missing_images':missing,'vertices':len(mesh.data.vertices),'triangles':len(mesh.data.polygons),'material_slots':len(mesh.material_slots),'packed_images':sum(bool(im.packed_file) for im in bpy.data.images),'orthographic_views':4}
 bm=bmesh.new();bm.from_mesh(mesh.data);rec['boundary_edges']=sum(e.is_boundary for e in bm.edges);rec['nonmanifold_edges']=sum(not e.is_manifold for e in bm.edges);rec['zero_area_faces']=sum(f.calc_area()<1e-15 for f in bm.faces);rec['has_uv']=bool(mesh.data.uv_layers);bm.free()
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(folder/f'{name}_8000.glb'))
 rec['glb_imported']=True;rec['glb_mesh_objects']=sum(o.type=='MESH' for o in bpy.context.scene.objects);results.append(rec)
(base/'06_Reports/Model_Validation.json').write_text(json.dumps(results,indent=2))
