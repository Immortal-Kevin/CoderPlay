import os
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
from PIL import Image,ImageFilter,ImageDraw,ImageFont
import numpy as np, json, hashlib, time
from collections import deque
from pathlib import Path
T=Path(str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'Tools/P10_Final_Delivery'));S=Path(str(__import__('pathlib').Path(__file__).resolve().parents[2] / '03_Renders/Aurora_P10_Remaster_Preview.png'))
a=np.asarray(Image.open(S).convert('RGB')).astype(np.float32)
# Connected neutral low-luminance background; fill enclosed dark ship details.
mx=a.max(2);mn=a.min(2);blue=a[:,:,2]-a[:,:,0]
candidate=(mx<28)&((mx-mn)<12)
h,w=candidate.shape
outside=np.zeros((h,w),np.uint8);q=deque()
for x in range(w):
 for y in (0,h-1):
  if candidate[y,x] and not outside[y,x]:outside[y,x]=1;q.append((y,x))
for y in range(h):
 for x in (0,w-1):
  if candidate[y,x] and not outside[y,x]:outside[y,x]=1;q.append((y,x))
while q:
 y,x=q.popleft()
 for yy,xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
  if 0<=yy<h and 0<=xx<w and candidate[yy,xx] and not outside[yy,xx]:outside[yy,xx]=1;q.append((yy,xx))
# Hue-based plume exclusion, only outside known engine nozzles. Never sharpen these.
yy,xx=np.mgrid[:h,:w]
plume=((xx>1223)&(yy>240)&(yy<395))|((xx>1554)&(yy>335)&(yy<510))|((xx>1540)&(yy>555)&(yy<755))
glow=plume&(blue>9)&(a[:,:,2]-a[:,:,1]>3)
hard=(outside==0)
mask=Image.fromarray(np.uint8(hard*255))
soft=np.asarray(mask.filter(ImageFilter.GaussianBlur(.38))).astype(np.float32)/255
# Existing nozzle bounds: distinguish their curved hard rims from the original soft plume.
plume=np.zeros((h,w),np.float32)
for cx,cy,rx,ry,lo,hi in [(1203,321,29,36,235,380),(1538,433,32,64,320,535),(1534,670,33,62,550,780)]:
 cut=cx+rx*np.sqrt(np.maximum(0,1-((yy-cy)/ry)**2))
 weight=np.clip((xx-cut)/5,0,1)*((yy>lo)&(yy<hi))*(blue>5)*(a[:,:,0]<65)
 plume=np.maximum(plume,weight)
galpha=np.clip((a[:,:,2]-a[:,:,0]-2)/232,0,1)
alpha=soft*(1-plume)+galpha*plume
alpha[alpha<.009]=0
# Original neutral background approximately 20-26; fit local smooth field from safe samples.
bg=np.repeat(np.mean(a,2)[:,:,None],3,2)
bg[:]=22
# Decontaminate matte edges rather than alpha-sharpening them.
fg=np.clip((a-bg*(1-alpha[:,:,None]))/np.maximum(alpha[:,:,None],.008),0,255)
fg[alpha==0]=0
Image.fromarray(np.uint8(alpha*255+.5),'L').save(T/'alpha_original.png')
Image.fromarray(np.uint8(fg+.5),'RGB').save(T/'foreground_original.png')
rgba=Image.fromarray(np.dstack((np.uint8(fg+.5),np.uint8(alpha*255+.5))),'RGBA')
rgba.save(T/'matte_check.png')
for color,name in [((230,230,230,255),'light'),((22,24,28,255),'dark')]:
 out=Image.new('RGBA',rgba.size,color);out.alpha_composite(rgba);out.convert('RGB').save(T/('matte_'+name+'.jpg'))
Image.fromarray(np.uint8(plume*255),'L').save(T/'glow_mask.png')
print(json.dumps({'input':list(a.shape),'alpha_zero':int((alpha==0).sum()),'alpha_partial':int(((alpha>0)&(alpha<1)).sum()),'alpha_opaque':int((alpha==1).sum())}))
