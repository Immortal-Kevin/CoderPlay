import bpy,bmesh,pathlib,sys,math,json,time
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(pathlib.Path(__file__).parent));from model_utils import *
root=pathlib.Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(root.parent/'08_Aurora_HD_Remaster/01_Geometry/Aurora_HD_Remaster_Editable.blend'));s=bpy.context.scene
def collection(name):
 c=bpy.data.collections.new(name);s.collection.children.link(c);return c
cols={n:collection('P7_'+n) for n in ['Hull','Armor','WindowsDoors','Engines','Bridge','Decals','Lighting']}
archive=bpy.data.collections['HD_Remaster_Ship'];archive.name='P6_HD_Archive'
for vl in s.view_layers:
 vl.use=vl.name=='Beauty';vl.layer_collection.children[archive.name].exclude=True;vl.layer_collection.children['P5_Original_Archived'].exclude=True;vl.layer_collection.children['Ship_Occlusion_ONLY'].exclude=True
def pbr(name,color,metal,rough,group=None):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;bs.inputs['Coat Weight'].default_value=.25;bs.inputs['Coat Roughness'].default_value=.17
 if group:m['AI_MATERIAL_GROUP']=group
 return m
white=pbr('P7_White_Aerospace_Coating',(.79,.82,.86),.16,.26,'WhiteArmor');silver=pbr('P7_Satin_Silver_Alloy',(.52,.60,.69),.9,.23,'Silver');gold=pbr('P7_Champagne_Gold',(.68,.43,.12),.82,.21,'ChampagneGold');dark=pbr('P7_Graphite_Machinery',(.025,.039,.055),.68,.31,'DarkMetal');blue=pbr('P7_Deep_Navy_Armor',(.016,.043,.068),.48,.27,'DarkMetal');glass=pbr('P7_Optical_Blue_Glass',(.003,.018,.037),.34,.075);glass.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.9;glass.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.46
black=pbr('P7_Fluoropolymer_Seal',(.004,.007,.012),.12,.48);cyan=pbr('P7_Cyan_Service_Light',(.001,.15,.2),.2,.18);bs=cyan.node_tree.nodes['Principled BSDF'];bs.inputs['Emission Color'].default_value=(.001,.48,.66,1);bs.inputs['Emission Strength'].default_value=1.1
hull=bpy.data.objects['Aurora_HD_Hull'].copy();hull.data=hull.data.copy();hull.name='P7_Main_Hull_Clean_Shell';cols['Hull'].objects.link(hull)
engine_centers=[(x,z) for x in [-.120033212,.120033212] for z in [-.040943504,.044989898]]
bm=bmesh.new();bm.from_mesh(hull.data);remove=[]
for f in bm.faces:
 for x,z in engine_centers:
  if all(v.co.y>.1335 and math.hypot(v.co.x-x,v.co.z-z)<.033 for v in f.verts):remove.append(f);break
bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(hull.data);bm.free();hull.data.materials.clear()
for m in [white,blue,dark,silver]:hull.data.materials.append(m)
for p in hull.data.polygons:
 center=sum((hull.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
 p.material_index=2 if center.y>.245 and abs(center.x)<.085 else 1 if center.z<-.018 else 0
 if center.z>.085:p.material_index=0
 p.use_smooth=True
refbvh=BVHTree.FromPolygons([v.co.copy() for v in hull.data.vertices],[list(p.vertices) for p in hull.data.polygons],all_triangles=False)
# A genuinely new, smooth quad-loft pressure hull; retain bridge and stern separately.
stations=np.array([-.3319,-.325,-.315,-.30,-.275,-.25,-.225,-.20,-.175,-.15,-.10,-.05,0,.05,.10,.15,.20,.25,.28]);widths=[];tops=[];bottoms=[]
for y in stations:
 hit,n,idx,dist=refbvh.ray_cast(Vector((.22,y,-.008)),Vector((-1,0,0)),.44);widths.append(float(hit.x) if hit is not None and hit.x>.003 else float('nan'))
 hit,n,idx,dist=refbvh.ray_cast(Vector((0,y,.088)),Vector((0,0,-1)),.20);tops.append(float(hit.z) if hit is not None else float('nan'))
 hit,n,idx,dist=refbvh.ray_cast(Vector((0,y,-.107)),Vector((0,0,1)),.20);bottoms.append(float(hit.z) if hit is not None else float('nan'))
widths=np.array(widths);tops=np.array(tops);bottoms=np.array(bottoms)
for ar in [widths,tops,bottoms]:
 ok=np.isfinite(ar);ar[~ok]=np.interp(stations[~ok],stations[ok],ar[ok])
widths[0]=.001;tops[0]=-.004;bottoms[0]=-.008;widths=np.minimum(widths,.1575);tops=np.minimum(tops,.087);bottoms=np.maximum(bottoms,-.104)
# Bottom ray casts can pass through the open souvenir underside and hit the top.
# Use a smooth, design-matched lower pressure-shell profile instead of those hits.
bottoms=np.array([-.008,-.0164,-.0257,-.0352,-.0454,-.0575,-.0706,-.0812,-.0889,-.095,-.101,-.104,-.105,-.104,-.101,-.096,-.091,-.081,-.0635])
for ar in [widths,tops,bottoms]:
 for it in range(2):ar[2:-2]=(ar[1:-3]+ar[2:-2]*2+ar[3:-1])/4
def smooth_interp(x,values):
 i=int(np.clip(np.searchsorted(stations,x)-1,0,len(stations)-2));t=(x-stations[i])/(stations[i+1]-stations[i]);p0=values[max(0,i-1)];p1=values[i];p2=values[i+1];p3=values[min(len(values)-1,i+2)];return .5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
lv=[];lf=[];NY=144;NT=128
for k in range(NY+1):
 y=stations[0]+(stations[-1]-stations[0])*k/NY;rx=max(.0008,smooth_interp(y,widths));top=smooth_interp(y,tops);bottom=smooth_interp(y,bottoms);cz=(top+bottom)/2;rz=max(.0008,(top-bottom)/2)
 for j in range(NT):a=j*2*math.pi/NT;lv.append((rx*math.cos(a),y,cz+rz*math.sin(a)))
for k in range(NY):
 for j in range(NT):lf.append((k*NT+j,(k+1)*NT+j,(k+1)*NT+(j+1)%NT,k*NT+(j+1)%NT))
lf.append(tuple(reversed(range(NT))));lf.append(tuple(NY*NT+j for j in range(NT)))
structure=hull.copy();structure.data=hull.data.copy();structure.name='P7_Original_Bridge_Stern_Structure';cols['Hull'].objects.link(structure);bm=bmesh.new();bm.from_mesh(structure.data);discard=[]
for face in bm.faces:
 center=face.calc_center_median()
 if not(center.z>.104 or (center.y>.25 and abs(center.x)<.082)):discard.append(face)
bmesh.ops.delete(bm,geom=discard,context='FACES');bm.to_mesh(structure.data);bm.free();loft=bpy.data.meshes.new('P7_Quad_Loft_Pressure_Hull');loft.from_pydata(lv,[],lf);loft.update();hull.data=loft
for m in [white,blue,dark,silver]:hull.data.materials.append(m)
for face in hull.data.polygons:face.use_smooth=True;face.material_index=1 if face.center.z<-.018 else 0
bvh=BVHTree.FromPolygons([v.co.copy() for v in hull.data.vertices],[list(p.vertices) for p in hull.data.polygons],all_triangles=False)
surface_bvh=BVHTree.FromPolygons([v.co.copy() for v in hull.data.vertices]+[v.co.copy() for v in structure.data.vertices],[list(p.vertices) for p in hull.data.polygons]+[[i+len(hull.data.vertices) for i in p.vertices] for p in structure.data.polygons],all_triangles=False)
(root/'09_Report/Loft_Profiles.json').write_text(json.dumps({'y':stations.tolist(),'width':widths.tolist(),'top':tops.tolist(),'bottom':bottoms.tolist(),'radial_segments':NT,'longitudinal_segments':NY},indent=2))
def sidepoint(sign,y,z,offset=0):
 hit,n,idx,dist=surface_bvh.ray_cast(Vector((sign*.45,y,z)),Vector((-sign,0,0)),.9)
 if hit is None or n.x*sign<.20:return None
 return hit+n*offset,n
def topoint(x,y,offset=0):
 hit,n,idx,dist=bvh.ray_cast(Vector((x,y,.09)),Vector((0,0,-1)),.25)
 if hit is None or n.z<.35 or hit.z<.012:return None
 return hit+n*offset,n
def patch(name,func,umin,umax,vmin,vmax,mat,col,nu=5,nv=4,thick=.0007):
 verts=[];valid=[]
 for j in range(nv+1):
  for i in range(nu+1):
   hit=func(umin+(umax-umin)*i/nu,vmin+(vmax-vmin)*j/nv);valid.append(hit is not None);verts.append(hit[0] if hit else Vector())
 faces=[]
 for j in range(nv):
  for i in range(nu):
   ids=(j*(nu+1)+i,j*(nu+1)+i+1,(j+1)*(nu+1)+i+1,(j+1)*(nu+1)+i)
   if all(valid[k] for k in ids):faces.append(ids)
 if not faces:return None
 o=mesh(name,verts,faces,col,mat)
 if thick:
  so=o.modifiers.new('Physical layered armor thickness','SOLIDIFY');so.thickness=thick;so.offset=-1;be=o.modifiers.new('Armor edge highlight bevel','BEVEL');be.width=.00024;be.segments=3;be.limit_method='ANGLE';be.angle_limit=.45
 return o
# Large fitted top armor tiles: gaps and sidewalls are real geometry.
count_top=0
for j in range(10):
 y0=-.291+j*.0395;y1=y0+.0375
 for i in range(5):
  x0=-.094+i*.038;x1=x0+.036
  o=patch(f'Upper_Armor_{j:02d}_{i:02d}',lambda x,y:topoint(x,y,.00085),x0,x1,y0,y1,white,cols['Armor'])
  count_top+=bool(o)
for sign in [1,-1]:
 for j in range(8):
  y0=-.285+j*.048;y1=y0+.045
  if -.16<y0<-.08:continue
  patch(f'Side_Armor_{sign}_{j}',lambda y,z,sg=sign:sidepoint(sg,y,z,.0008),y0,y1,.038,.067,white,cols['Armor'],nu=5,nv=4)
 # Continuous gold accent follows the actual hull curve.
 patch('Gold_Hull_Ribbon_'+str(sign),lambda y,z,sg=sign:sidepoint(sg,y,z,.00115),-.295,.127,.0305,.0365,gold,cols['Armor'],nu=160,nv=2,thick=.0004)
 patch('Lower_Silver_Chine_'+str(sign),lambda y,z,sg=sign:sidepoint(sg,y,z,.0008),-.27,.14,-.067,-.064,silver,cols['Armor'],nu=100,nv=1,thick=.0003)
 # Two restrained cabin window groups, four actual panes each side.
 for group,cy in enumerate([-.238,-.034]):
  for j in range(4):
   y=cy+(j-1.5)*.017;z=.052;hit=sidepoint(sign,y,z,.0007)
   if not hit:continue
   p,n=hit;ba=basis(n);box(f'Window_Frame_{sign}_{group}_{j}',p,(.0019,.0147,.0072),silver,cols['WindowsDoors'],.0012,ba);box(f'Window_Glass_{sign}_{group}_{j}',p+n*.00105,(.0006,.0126,.0052),glass,cols['WindowsDoors'],.00105,ba)
 # Actual framed cargo hatch, with seal, hinges and four locking dogs.
 cy=.063;cz=-.015;W=.068;H=.041
 patch('Cargo_Door_Panel_'+str(sign),lambda y,z,sg=sign:sidepoint(sg,y,z,.001),cy-W/2,cy+W/2,cz-H/2,cz+H/2,dark,cols['WindowsDoors'],nu=10,nv=7,thick=.001)
 for frame,delta,r,mat in [('Gasket',0,.00135,black),('AlloyFrame',.001,.00085,silver),('GoldSafetyTrim',.0025,.00034,gold)]:
  pts=[]
  for y,z in [(cy-W/2-delta,cz-H/2-delta),(cy+W/2+delta,cz-H/2-delta),(cy+W/2+delta,cz+H/2+delta),(cy-W/2-delta,cz+H/2+delta)]:
   hit=sidepoint(sign,y,z,.00165)
   if hit:pts.append(hit[0])
  if len(pts)==4:tube(f'Cargo_{frame}_{sign}',pts,r,mat,cols['WindowsDoors'],True)
 for k,z in enumerate([cz-.014,cz+.014]):
  hit=sidepoint(sign,cy+W/2,z,.0022)
  if hit:cylinder(f'Cargo_Hinge_{sign}_{k}',hit[0],.0017,.010,silver,cols['WindowsDoors'],(0,0,1),32)
 for k,z in enumerate([cz-.014,cz-.005,cz+.005,cz+.014]):
  hit=sidepoint(sign,cy-W/2-.001,z,.0024)
  if hit:box(f'Cargo_Lock_{sign}_{k}',hit[0],(.002,.004,.003),gold,cols['WindowsDoors'],.0005,basis(hit[1]))
 # Door glazing, handrail and dedicated service access cover.
 hit=sidepoint(sign,cy,cz+.010,.002)
 if hit:box('Cargo_Status_Glass_'+str(sign),hit[0],(.0008,.035,.006),glass,cols['WindowsDoors'],.001,basis(hit[1]))
 patch('Service_Access_'+str(sign),lambda y,z,sg=sign:sidepoint(sg,y,z,.0012),-.205,-.165,-.045,-.022,silver,cols['WindowsDoors'],nu=5,nv=3,thick=.0006)
# Replace all four engine cowls with high-resolution concentric assemblies.
for ei,(x,z) in enumerate(engine_centers):
 c=(x,0,z);prefix=f'Engine_{ei+1:02d}';col=cols['Engines']
 profile=[(.119,.0005),(.122,.009),(.127,.017),(.132,.022),(.138,.026),(.15,.030),(.165,.0316),(.23,.0316),(.255,.0305),(.277,.0275),(.29,.024),(.304,.021),(.318,.0192),(.331,.0178)]
 lathe_y(prefix+'_White_CeramicMetal_Cowl',c,profile,white,col,128)
 for y,r,w,ma in [(.16,.0318,.002,silver),(.245,.0311,.003,gold),(.278,.0278,.002,silver),(.302,.0218,.0015,silver),(.328,.0183,.0010,silver)]:
  lathe_y(prefix+'_Collar_'+str(y),c,[(y-w,r),(y-w*.8,r+.00045),(y+w*.8,r+.00045),(y+w,r)],ma,col,128)
 lathe_y(prefix+'_Recessed_Nozzle_Liner',c,[(.297,.0142),(.306,.0152),(.325,.0156),(.3325,.0164),(.334,.0166)],dark,col,128)
 for k in range(32):
  a=k*2*math.pi/32;rad=.0278;loc=Vector((x+rad*math.cos(a),.282,z+rad*math.sin(a)));ob=box(prefix+f'_CoolingFin_{k:02d}',loc,(.002,.023,.004),dark,col,.00035);ob.rotation_euler.y=-a
 for k in range(16):
  a=k*2*math.pi/16;points=[Vector((x+.0152*math.cos(a),.306,z+.0152*math.sin(a))),Vector((x+.0159*math.cos(a),.331,z+.0159*math.sin(a)))];tube(prefix+f'_InnerWall_Rib_{k:02d}',points,.00038,silver,col)
 for k in range(8):
  a=k*2*math.pi/8;loc=(x+.029*math.cos(a),.25,z+.029*math.sin(a));cylinder(prefix+f'_CollarFastener_{k}',loc,.00095,.0018,silver,col,(0,1,0),20)
 # Actual support strut to the central chassis.
 target=Vector((x*.60,.211,z*.68));start=Vector((x,.211,z));tube(prefix+'_Mount_Strut',[start,target],.0036,silver,col)
 for off in [-.009,.009]:
  loc=Vector((x*.76,.211+off,z*.77));box(prefix+'_Bracket_'+str(off),loc,(.017,.003,.010),dark,col,.0007)
# Retain the exact 128-segment cyan rings, adding external mounting hardware.
rings=json.loads((root.parent/'08_Aurora_HD_Remaster/06_Report/Ring_Repair.json').read_text())['rings']
for o in archive.objects:
 if o.name=='Aurora_HD_Hull':continue
 cp=o.copy();cp.data=o.data.copy();cols['Hull'].objects.link(cp);cp.name='P7_'+o.name
 if 'Cyan' not in cp.name:cp.data.materials.clear();cp.data.materials.append(dark)
for rinfo in rings:
 c=Vector(rinfo['center']);n=Vector(rinfo['normal']);R=.031;t=n.cross(Vector((0,0,1))).normalized();u=n.cross(t)
 torus('Port_Gold_Retaining_Rim_'+str(rinfo['side']),c+n*.001,n,R,.00045,gold,cols['Armor'],128,12)
 for k in range(8):
  a=k*2*math.pi/8;p=c+n*.001+(t*math.cos(a)+u*math.sin(a))*.0304;cylinder('Port_Retention_Bolt_'+str(rinfo['side'])+'_'+str(k),p,.00095,.0013,silver,cols['Armor'],n,24)
# New bridge base seals the preserved upper fin to the new pressure hull.
box('Bridge_Integrated_Pedestal',(0,.16,.096),(.043,.112,.027),white,cols['Bridge'],.008)
cylinder('Forward_Comms_Base',(0,-.005,.095),.011,.028,white,cols['Bridge'],(0,0,1),64)
# Bridge glazing fitted to the actual upper triangular structure.
for sign in [1,-1]:
 for j in range(5):
  y=.123+j*.012;hit=sidepoint(sign,y,.119,.0008)
  if hit and abs(hit[0].x)<.045:
   p,n=hit;box(f'Bridge_Frame_{sign}_{j}',p,(.0015,.0105,.009),silver,cols['Bridge'],.001,basis(n));box(f'Bridge_Glass_{sign}_{j}',p+n*.0009,(.0005,.0088,.0072),glass,cols['Bridge'],.0008,basis(n))
for loc in [(-.014,.185,.173),(.014,.185,.173)]:
 cylinder('Comms_Mast',loc,.0009,.029,silver,cols['Bridge'],(0,.12,1),32);cylinder('Comms_Gold_Tip',Vector(loc)+Vector((0,.0017,.014)),.0011,.0025,gold,cols['Bridge'],(0,0,1),32)
# Original supplied logo glyphs, alpha-safe editable surface-conforming decals.
def decalmat(name,path):
 m=pbr(name,(1,1,1),.08,.38);m.surface_render_method='DITHERED';n=m.node_tree.nodes;l=m.node_tree.links;tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path));bs=n.get('Principled BSDF');l.new(tex.outputs['Color'],bs.inputs['Base Color']);l.new(tex.outputs['Alpha'],bs.inputs['Alpha']);return m
decal=decalmat('Alterra_Exact_Dark_Glyphs',root/'05_Alterra_Decals/Alterra_Dark_Transparent_1024.png');placements=[]
def logo(sign,cy,cz,W,H,name):
 N=16;verts=[];valid=[]
 for j in range(N+1):
  for i in range(N+1):
   hit=sidepoint(sign,cy+sign*(i/N-.5)*W,cz+(j/N-.5)*H,.0018);valid.append(hit is not None);verts.append(hit[0] if hit else Vector())
 faces=[]
 for j in range(N):
  for i in range(N):
   q=(j*(N+1)+i,j*(N+1)+i+1,(j+1)*(N+1)+i+1,(j+1)*(N+1)+i)
   if all(valid[k] for k in q):faces.append(q)
 ob=mesh(name,verts,faces,cols['Decals'],decal);uv=ob.data.uv_layers.new(name='LogoUV')
 for p in ob.data.polygons:
  for vi,li in zip(p.vertices,p.loop_indices):uv.data[li].uv=(vi%(N+1)/N,vi//(N+1)/N)
 placements.append({'name':name,'side':sign,'center_yz':[cy,cz],'size_yz':[W,H],'valid_grid_points':sum(valid),'total_grid_points':len(valid)})
 return ob
for sign in [1,-1]:
 logo(sign,-.235,.006,.046,.048,'Alterra_Hull_'+str(sign))
 # Find a fully supported rectangle on the triangular fin, rather than floating it.
 selected=None
 for W,H in [(.026,.024),(.022,.022),(.019,.020)]:
  for cy in [.17,.18,.165,.175,.16,.185,.15,.19]:
   for cz in [.145,.14,.15,.135,.13,.125]:
    if all(sidepoint(sign,float(cy+dy),float(cz+dz),.0011) is not None and abs(sidepoint(sign,float(cy+dy),float(cz+dz))[0].x)<.04 for dy in [-W/2,0,W/2] for dz in [-H/2,0,H/2]):selected=(float(cy),float(cz),W,H);break
   if selected:break
  if selected:break
 if selected:logo(sign,*selected,'Alterra_TopFin_'+str(sign))
def text_surface(sign,text,cy,cz,size,name):
 hit=sidepoint(sign,cy,cz,.0020)
 if not hit:return
 curve=bpy.data.curves.new(name,'FONT');curve.body=text;curve.align_x='CENTER';curve.size=size;curve.extrude=.000008;ob=bpy.data.objects.new(name,curve);cols['Decals'].objects.link(ob);ob.location=hit[0];ob.rotation_euler=Matrix((Vector((0,sign,0)),Vector((0,0,1)),Vector((sign,0,0)))).transposed().to_euler();curve.materials.append(white if name.startswith('Cargo') else gold)
for sign in [1,-1]:
 text_surface(sign,'AURORA  /  01',-.235,-.024,.0036,'Ship_Registry_'+str(sign));text_surface(sign,'CARGO  /  01',.063,-.027,.0031,'Cargo_Label_'+str(sign))
(root/'09_Report/Decal_Placements.json').write_text(json.dumps(placements,indent=2))
# A locally authored floating-point studio HDRI, for reflection only.
w,h=1024,512;xx,yy=np.meshgrid(np.arange(w)/w,np.arange(h)/h);hdr=np.zeros((h,w,4),dtype=np.float32);hdr[:,:,:3]=(.045,.062,.085);hdr[:,:,3]=1
for ux,uy,sx,sy,power,color in [(.18,.31,.085,.12,6,(.88,.95,1)),(.58,.23,.13,.065,8,(1,.95,.86)),(.85,.46,.025,.20,9,(.72,.85,1))]:
 dx=np.minimum(abs(xx-ux),1-abs(xx-ux));shape=np.exp(-((dx/sx)**8+((yy-uy)/sy)**8));hdr[:,:,:3]+=shape[:,:,None]*np.array(color)*power
env=bpy.data.images.new('P7_Studio_HDRI',width=w,height=h,float_buffer=True);env.pixels.foreach_set(hdr.ravel());env.filepath_raw=str(root/'04_PBR_Materials/P7_Studio_HDRI_v04.exr');env.file_format='OPEN_EXR';env.save()
world=bpy.data.worlds.new('P7_Transparent_Studio');world.use_nodes=True;s.world=world;n=world.node_tree.nodes;l=world.node_tree.links;bg=n.get('Background');tex=n.new('ShaderNodeTexEnvironment');tex.image=env;l.new(tex.outputs['Color'],bg.inputs['Color']);bg.inputs['Strength'].default_value=.20
for o in list(s.objects):
 if o.type=='LIGHT':o.hide_render=True
for name,loc,power,size,color in [('Key',(0,-.35,1),14,1.2,(.90,.95,1)),('Fill',(-.8,.1,.4),9,1.0,(.75,.86,1)),('Rim',(.2,.8,.65),20,.65,(1,.9,.72))]:
 data=bpy.data.lights.new('P7_'+name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color;ob=bpy.data.objects.new('P7_'+name,data);cols['Lighting'].objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,.02))-ob.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64;s.render.threads_mode='FIXED';s.render.threads=4;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8';s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.0
s.camera=bpy.data.objects['Front_ThreeQuarter'];s.render.resolution_x=2048;s.render.resolution_y=1528;s.render.resolution_percentage=100;s.render.filepath=str(root/'06_Preview/Geometry_Checkpoint_Front_2048_v04.png')
s['P7_status']='Geometry checkpoint. AI material binding is a separate explicit stage; not yet a complete AI rebuild.'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'01_Blender/P7_Geometry_Checkpoint_v04.blend'))
stats={'new_objects':{},'armor_top_panels':count_top,'old_engine_faces_replaced':len(remove),'p6_archived':True,'ai_bound':False}
for name,col in cols.items():stats['new_objects'][name]={'objects':len(col.objects),'mesh_polygons':sum(len(o.data.polygons) for o in col.objects if o.type=='MESH')}
(root/'09_Report/Geometry_Checkpoint_Stats_v04.json').write_text(json.dumps(stats,indent=2));bpy.ops.render.render(write_still=True);print(json.dumps(stats),flush=True)
