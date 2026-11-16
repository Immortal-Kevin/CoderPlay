import os,pathlib,sys,json,hashlib
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
R=pathlib.Path(str(__import__('pathlib').Path(__file__).resolve().parents[2]));F=R/'Final';T=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'Tools/P10_Final_Delivery/pythonlibs'))
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
cv2.setNumThreads(4)
files=[F/'AuroraV12_Clean_8000.png',F/'AuroraV14_Clean_8000.png'];hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in files];images=[Image.open(p).convert('RGBA') for p in files];target=images[1].size;W,H=target
reg=json.loads((T/'Registration.json').read_text());m=np.array(reg['local']);ms=np.eye(3);ms[:2]=m;d1=np.diag([2000/images[0].width,round(images[0].height/4)/images[0].height,1]);d2=np.diag([2000/W,round(H/4)/H,1]);matrix=(np.linalg.inv(d2)@ms@d1)[:2]
source=np.asarray(images[0],dtype='float32')/255;source[:,:,:3]*=source[:,:,3,None];aligned=np.empty((H,W,4),dtype='uint8')
for top in range(0,H,256):
 bottom=min(H,top+256);mm=matrix.copy();mm[1,2]-=top;part=cv2.warpAffine(source,mm,(W,bottom-top),flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0));a=np.clip(part[:,:,3],0,1);rgb=np.divide(part[:,:,:3],a[:,:,None],out=np.zeros_like(part[:,:,:3]),where=a[:,:,None]>1e-7);q=np.uint8(np.clip(np.dstack((rgb,a))*255+.5,0,255));q[q[:,:,3]==0,:3]=0;aligned[top:bottom]=q
del source
imA=Image.fromarray(aligned,'RGBA');imB=images[1];smallA=np.asarray(imA.resize((2000,round(H/4)),Image.Resampling.LANCZOS));smallB=np.asarray(imB.resize((2000,round(H/4)),Image.Resampling.LANCZOS));hh=smallA.shape[0];xmin,xmax=900,1200
aa=smallA[:,:,3].astype('float32')/255;ab=smallB[:,:,3].astype('float32')/255;ga=cv2.cvtColor(smallA[:,:,:3],cv2.COLOR_RGB2GRAY).astype('float32');gb=cv2.cvtColor(smallB[:,:,:3],cv2.COLOR_RGB2GRAY).astype('float32')
diff=np.abs(smallA[:,:,:3].astype('float32')-smallB[:,:,:3].astype('float32')).mean(2);grad=np.hypot(cv2.Sobel(ga,cv2.CV_32F,1,0),cv2.Sobel(ga,cv2.CV_32F,0,1))+np.hypot(cv2.Sobel(gb,cv2.CV_32F,1,0),cv2.Sobel(gb,cv2.CV_32F,0,1));center=np.interp(np.arange(hh),[0,350,500,700,hh-1],[950,950,1030,1070,1080]);xs=np.arange(xmin,xmax)
cost=.55*diff[:,xmin:xmax]+.075*grad[:,xmin:xmax]+65*np.abs(aa[:,xmin:xmax]-ab[:,xmin:xmax]);cost+=.0006*(xs[None,:]-center[:,None])**2
dp=cost[0].copy();back=np.zeros(cost.shape,dtype='int8')
for y in range(1,hh):
 options=[]
 for shift in [-2,-1,0,1,2]:
  row=np.roll(dp,shift)+abs(shift)*.16
  if shift<0:row[shift:]=1e15
  if shift>0:row[:shift]=1e15
  options.append(row)
 stack=np.stack(options);choice=stack.argmin(0);dp=cost[y]+np.take_along_axis(stack,choice[None,:],axis=0)[0];back[y]=np.array([-2,-1,0,1,2],dtype='int8')[choice]
path=np.empty(hh,dtype='float32');col=int(dp.argmin());path[-1]=xmin+col
for y in range(hh-1,0,-1):col-=int(back[y,col]);path[y-1]=xmin+col
path=cv2.GaussianBlur(path.reshape(-1,1),(1,25),sigmaX=0,sigmaY=4).ravel();path_full=np.interp(np.arange(H)*hh/H,np.arange(hh),path)*4
result=np.empty((H,W,4),dtype='uint8');B=np.asarray(imB);maskall=np.empty((H,W),dtype='uint8');feather=40.;right_equal=True;left_equal=True
for top in range(0,H,192):
 bottom=min(H,top+192);a=aligned[top:bottom];b=B[top:bottom];distance=np.arange(W)[None,:]-path_full[top:bottom,None];weight=np.clip(.5-distance/(2*feather),0,1);weight=weight*weight*(3-2*weight)
 # Use one original silhouette at the join rather than averaging two edges.
 boundary=(np.minimum(a[:,:,3],b[:,:,3])<248);weight[boundary]=(weight[boundary]>=.5).astype('float32')
 fa=a.astype('float32')/255;fb=b.astype('float32')/255;alpha=fa[:,:,3]*weight+fb[:,:,3]*(1-weight);premult=fa[:,:,:3]*fa[:,:,3,None]*weight[:,:,None]+fb[:,:,:3]*fb[:,:,3,None]*(1-weight[:,:,None]);rgb=np.divide(premult,alpha[:,:,None],out=np.zeros_like(premult),where=alpha[:,:,None]>1e-8);o=np.uint8(np.clip(np.dstack((rgb,alpha))*255+.5,0,255));o[o[:,:,3]==0,:3]=0;o[weight==0]=b[weight==0];o[weight==1]=a[weight==1];result[top:bottom]=o;maskall[top:bottom]=np.uint8(weight*255+.5)
 assert np.array_equal(o[weight==0],b[weight==0]) and np.array_equal(o[weight==1],a[weight==1])
 assert not np.any((a[:,:,3]>=254)&(b[:,:,3]>=254)&(o[:,:,3]<254))
final=Image.fromarray(result,'RGBA');assert np.array_equal(result[:,5400:],B[:,5400:]),'V14 stern and complete source exhaust must be unchanged'
assert np.array_equal(result[:,:3400],aligned[:,:3400]),'V12 bow must be unchanged after alignment'
final.save(T/'Candidate_V15_8000.png',compress_level=6);Image.fromarray(maskall).save(T/'Local_Blend_Mask.png');imA.save(T/'Aligned_V12_8000.png',compress_level=6)
thumb=final.copy();thumb.thumbnail((2000,1300))
for name,bg in [('Dark',(16,22,30)),('White',(240,240,240))]:
 check=Image.new('RGBA',thumb.size,(*bg,255));check.alpha_composite(thumb);check.convert('RGB').save(T/f'Candidate_V15_{name}.jpg',quality=96)
# Inspect join at native output scale, same field of view for both source images and result.
crop=(3500,1800,4750,4050);sheet=Image.new('RGB',(1800,1100),(18,24,32));draw=ImageDraw.Draw(sheet)
for n,(label,im) in enumerate([('V12 aligned',imA),('V14',imB),('V15 blend',final)]):
 p=im.crop(crop);p.thumbnail((590,1050));bg=Image.new('RGBA',p.size,(18,24,32,255));bg.alpha_composite(p);sheet.paste(bg.convert('RGB'),(n*600,30));draw.text((n*600+10,8),label,fill='white')
sheet.save(T/'Join_Detail_Comparison.jpg',quality=97)
proof={'inputs':[str(p) for p in files],'input_hashes':hashes,'target_size':target,'alignment_matrix':matrix.tolist(),'join_seam_range_px':[float(path_full.min()),float(path_full.max())],'blend_feather_halfwidth_px':feather,'V12_bow_pixels_identical_after_alignment':True,'V14_stern_tail_pixels_identical':True,'new_opaque_hull_holes':0,'no_added_exhaust_crop':True,'no_colour_grading_or_redrawing':True,'sources_unchanged':all(hashlib.sha256(p.read_bytes()).hexdigest()==v for p,v in zip(files,hashes))}
(T/'Validation.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof,indent=2),flush=True)
if '--save' in sys.argv:
 dest=F/'AuroraV15_Clean_8000.png';comp=F/'AuroraV15_Comparison.png';assert not dest.exists() and not comp.exists();final.save(dest,compress_level=6)
 comparison=Image.new('RGBA',(8000,1600),(0,0,0,0));draw=ImageDraw.Draw(comparison);font=ImageFont.truetype('msyh.ttc',60)
 for n,(label,im) in enumerate([('V12 - aligned',imA),('V14 - original',imB),('V15 - bow / stern blend',final)]):
  p=im.copy();p.thumbnail((2640,1490));x=n*2666+(2666-p.width)//2;comparison.alpha_composite(p,(x,100));draw.text((n*2666+35,20),label,font=font,fill=(160,172,188,255))
 comparison.save(comp,compress_level=6)
 for p in [dest,comp]:
  with Image.open(p) as check:check.verify()
 print('SAVED TWO V15 PNG FILES',flush=True)
