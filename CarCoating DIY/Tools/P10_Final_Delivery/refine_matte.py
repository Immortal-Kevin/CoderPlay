import sys,os
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'Tools/P10_Final_Delivery/pythonlibs'))
os.environ['OMP_NUM_THREADS']='4'
import cv2,numpy as np
from PIL import Image,ImageFilter
from pathlib import Path
T=Path(str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'Tools/P10_Final_Delivery'))
a=np.asarray(Image.open(str(__import__('pathlib').Path(__file__).resolve().parents[2] / '03_Renders/Aurora_P10_Remaster_Preview.png')).convert('RGB'))
h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w];f=a.astype(np.float32);blue=f[:,:,2]-f[:,:,0]
old=np.asarray(Image.open(T/'alpha_original.png'))
gc=np.full((h,w),cv2.GC_PR_BGD,np.uint8)
gc[old>15]=cv2.GC_PR_FGD
gc[old==0]=cv2.GC_BGD
interior=cv2.erode(np.uint8(old>252),np.ones((13,13),np.uint8))>0
regions=((xx>1180)&(yy>220)&(yy<380))|((xx>1490)&(yy>320)&(yy<535))|((xx>1480)&(yy>550)&(yy<780))
interior &= (~regions)|(f[:,:,0]>70)
gc[interior]=cv2.GC_FGD
plume_weight=np.zeros((h,w),np.float32)
for cx,cy,rx,ry,lo,hi in [(1203,321,29,36,235,380),(1538,433,32,64,320,535),(1534,670,33,62,550,780)]:
 cut=cx+rx*np.sqrt(np.maximum(0,1-((yy-cy)/ry)**2))
 weight=np.clip((xx-cut)/5,0,1)*((yy>lo)&(yy<hi))*(blue>4)*(f[:,:,0]<65)
 plume_weight=np.maximum(plume_weight,weight)
gc[plume_weight>.9]=cv2.GC_BGD
bg=np.zeros((1,65),np.float64);fg=np.zeros((1,65),np.float64)
cv2.setNumThreads(4);cv2.grabCut(a[:,:,::-1].copy(),gc,None,bg,fg,5,cv2.GC_INIT_WITH_MASK)
hull=np.uint8((gc==cv2.GC_FGD)|(gc==cv2.GC_PR_FGD))
# Fill only enclosed holes; this restores cyan windows/black panels, not background.
inv=1-hull;flood=inv.copy();cv2.floodFill(flood,None,(0,0),2);hull|=np.uint8(flood==1)
# Remove disconnected matte specks, retaining thin mast components in their original area.
n,labels,stats,cent=cv2.connectedComponentsWithStats(hull,8)
clean=np.zeros_like(hull)
for i in range(1,n):
 if stats[i,cv2.CC_STAT_AREA]>35 or (850<cent[i,0]<1110 and cent[i,1]<140):clean[labels==i]=1
hull=clean
# Feather by measured RGB transition between exterior and nearest interior.
inside=cv2.erode(hull,np.ones((3,3),np.uint8))
outside=cv2.dilate(hull,np.ones((3,3),np.uint8))
alpha=cv2.GaussianBlur(hull.astype(np.float32),(0,0),.42)
# Feather plumes from original blue excess; continuous alpha, no rectangular cutoff.
glow_alpha=np.clip((f[:,:,2]-24)/231,0,1)*np.clip((blue-5)/10,0,1)*regions
plume_soft=glow_alpha
alpha=alpha+(1-alpha)*glow_alpha
alpha[alpha<.012]=0
# Known background is neutral with a low spatial gradient. Remove matte contamination.
bgvalue=22.
fg_rgb=np.clip((f-bgvalue*(1-alpha[:,:,None]))/np.maximum(alpha[:,:,None],.01),0,255)
fg_rgb[alpha==0]=0
rgba=Image.fromarray(np.dstack((np.uint8(fg_rgb+.5),np.uint8(alpha*255+.5))),'RGBA');rgba.save(T/'matte_check.png')
rgba.getchannel('A').save(T/'alpha_original.png');rgba.convert('RGB').save(T/'foreground_original.png')
Image.fromarray(np.uint8(plume_soft*255+.5)).save(T/'glow_mask.png')
for color,name in [((230,230,230,255),'light'),((22,24,28,255),'dark')]:
 out=Image.new('RGBA',rgba.size,color);out.alpha_composite(rgba);out.convert('RGB').save(T/('matte_'+name+'.jpg'))
print('GrabCut matte complete; no learned model downloaded',cv2.__version__)
