import bpy,math
from mathutils import Vector,Matrix
def mesh(name,verts,faces,collection,material=None,smooth=True):
 m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update();o=bpy.data.objects.new(name,m);collection.objects.link(o)
 if material:m.materials.append(material)
 for p in m.polygons:p.use_smooth=smooth
 return o
def move(o,col):
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o)
def box(name,location,dimensions,mat,col,bevel=.0005,basis=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=location);o=bpy.context.object;o.name=name;o.dimensions=dimensions
 if basis:o.rotation_euler=Matrix(basis).transposed().to_euler()
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);move(o,col);o.data.materials.append(mat)
 if bevel:
  mod=o.modifiers.new('Machined edge radii','BEVEL');mod.width=bevel;mod.segments=3
  mod=o.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL');mod.keep_sharp=True
 return o
def cylinder(name,center,radius,length,mat,col,axis=(0,0,1),segments=32):
 bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=length,location=center);o=bpy.context.object;o.name=name;o.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler();move(o,col);o.data.materials.append(mat)
 mod=o.modifiers.new('Precision edge bevel','BEVEL');mod.width=min(radius*.15,.00035);mod.segments=2
 for p in o.data.polygons:p.use_smooth=True
 return o
def lathe_y(name,center,profile,mat,col,N=128):
 c=Vector(center);v=[];f=[]
 for y,r in profile:
  for j in range(N):a=j*2*math.pi/N;v.append(c+Vector((r*math.cos(a),y,r*math.sin(a))))
 for k in range(len(profile)-1):
  for j in range(N):f.append((k*N+j,(k+1)*N+j,(k+1)*N+(j+1)%N,k*N+(j+1)%N))
 return mesh(name,v,f,col,mat)
def torus(name,center,normal,R,r,mat,col,N=128,M=12):
 n=Vector(normal).normalized();t=n.cross(Vector((0,0,1)))
 if t.length<.01:t=n.cross(Vector((0,1,0)))
 t.normalize();u=n.cross(t);v=[];f=[];c=Vector(center)
 for i in range(N):
  a=i*2*math.pi/N;direction=t*math.cos(a)+u*math.sin(a)
  for j in range(M):b=j*2*math.pi/M;v.append(c+direction*(R+r*math.cos(b))+n*r*math.sin(b))
 for i in range(N):
  for j in range(M):f.append((i*M+j,((i+1)%N)*M+j,((i+1)%N)*M+(j+1)%M,i*M+(j+1)%M))
 return mesh(name,v,f,col,mat)
def tube(name,points,r,mat,col,cyclic=False):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r;cu.bevel_resolution=3;sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
 for p,v in zip(sp.points,points):p.co=(*v,1)
 sp.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,cu);col.objects.link(o);cu.materials.append(mat);return o
def basis(normal):
 n=Vector(normal).normalized();t=Vector((0,1,0));t=(t-n*t.dot(n)).normalized();u=n.cross(t)
 if u.z<0:t=-t;u=-u
 return n,t,u
