import pathlib,sys,json
root=pathlib.Path(__file__).parent;sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageFilter
import numpy as np
work=root/'P9_Work';im=Image.open(root/'Alterra_full.png').convert('RGBA');raw=np.asarray(im,dtype='float32')/255;rgb=raw[:,:,:3].copy();alpha=np.clip((raw[:,:,3]*255-2)/251,0,1);h,w=alpha.shape;yy,xx=np.mgrid[:h,:w];mask=np.zeros((h,w),dtype='float32')
specs=[('far',(1165,252,1385,390),[(280,1170),(300,1201),(320,1224),(340,1231),(352,1226)]),('near_upper',(1485,345,1632,515),[(365,1485),(385,1507),(405,1533),(425,1550),(445,1554),(465,1541),(485,1522),(503,1493)]),('near_lower',(1480,555,1632,730),[(582,1490),(600,1520),(620,1542),(640,1557),(660,1558),(680,1542),(700,1517),(718,1477)])]
for name,(x0,y0,x1,y1),pts in specs:
 edge=np.interp(yy,[p[0] for p in pts],[p[1] for p in pts]);m=np.clip((xx-edge-2)/5,0,1);m*=((xx>=x0)&(xx<x1)&(yy>=y0)&(yy<y1))
 # Fade at ROI boundaries, and do not touch foreground hull underneath far plume.
 m*=np.clip(np.minimum(yy-y0,y1-yy)/6,0,1)
 if name=='far':m*=np.clip((352+.27*(xx-1230)-yy-2)/5,0,1)
 mask=np.maximum(mask,m)
# Black-matte decontamination preserves the plume's premultiplied RGB on black.
# F'=F/max(F), A'=A*max(F), applied only beyond the physical nozzle contour.
peak=np.maximum(rgb.max(2),1/255);factor=1-mask+mask*peak;rgb=np.clip(rgb/factor[:,:,None],0,1);alpha*=factor
alpha[(raw[:,:,3]*255<=3)&(raw[:,:,:3].max(2)<.015)]=0
clean=np.dstack((rgb,alpha));clean=np.round(np.clip(clean,0,1)*255).astype('uint8');clean[clean[:,:,3]==0,:3]=0
Image.fromarray(clean,'RGBA').save(work/'Clean_Source_RGBA.png');Image.fromarray(np.round(mask*255).astype('uint8')).save(work/'Plume_Only_Repair_Mask.png')
# Extend nearby foreground colour under transparency for a safe RGB-only SR input.
valid=alpha>.02;filled=rgb.copy();filled[~valid]=0
for step in range(24):
 sums=np.zeros_like(filled);count=np.zeros((h,w),dtype='float32')
 for dy,dx in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
  shifted=np.roll(np.roll(filled,dy,axis=0),dx,axis=1);ok=np.roll(np.roll(valid,dy,axis=0),dx,axis=1)
  if dy>0:ok[:dy]=False
  if dy<0:ok[dy:]=False
  if dx>0:ok[:,:dx]=False
  if dx<0:ok[:,dx:]=False
  sums+=shifted*ok[:,:,None];count+=ok
 new=(~valid)&(count>0);filled[new]=sums[new]/count[new,None];valid[new]=True
filled[~valid]=(.055,.075,.10)
Image.fromarray(np.round(np.clip(filled,0,1)*255).astype('uint8'),'RGB').save(work/'SR_Input_RGB_Padded.png')
for label,bg in [('Dark',(16,22,31)),('White',(240,240,240)),('OceanBlue',(8,88,135))]:
 c=Image.fromarray(clean,'RGBA');Image.alpha_composite(Image.new('RGBA',im.size,(*bg,255)),c).convert('RGB').save(work/f'Clean_Source_{label}.jpg',quality=97)
(work/'Alpha_Repair_Method.json').write_text(json.dumps({'input_size':[w,h],'target_size':[8000,4725],'cleanup':'Alpha clamp((A-2)/251); black RGB alpha<=3 noise removed; no morphology erosion','plume_method':'Only exterior of traced nozzle contours: preserve RGB*alpha on black by remapping F=RGB/maxRGB, A=alpha*maxRGB with feathered mask','plumes':specs,'mask_feather_source_px':5,'rgb_extension_source_px':24,'original_clipped_right_edge_plumes':True,'no_background_invention':True},indent=2));print('Clean alpha, repaired plume matte, padded RGB ready')
