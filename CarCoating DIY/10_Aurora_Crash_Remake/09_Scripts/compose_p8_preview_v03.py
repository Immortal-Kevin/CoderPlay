import pathlib,sys,json
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageFilter
import numpy as np
records=[]
for view in ['Front_ThreeQuarter','Rear_ThreeQuarter']:
 body=Image.open(root/'05_Effects'/f'Body_{view}_2048.png').convert('RGBA');result=body.copy()
 for kind,gain in [('Smoke',3.5),('Fire',16.0),('Ion',14.0)]:
  p=root/'05_Effects'/f'{kind}_Occluded_{view}_2048.png';im=Image.open(p).convert('RGBA');a=np.asarray(im).copy();original=a[:,:,3].astype('float32')/255
  # LDR transparent delivery needs usable alpha for emissive/translucent volumes.
  # Source spatial occlusion is retained; no pasted or generated ship geometry.
  alpha=1-(1-original)**gain
  rgb=a[:,:,:3].astype('float32')/255;lum=rgb.mean(2)
  if kind=='Smoke':
   alpha=np.minimum(alpha,.85);tone=.11+.28*lum;rgb=np.dstack((tone*.92,tone*.96,tone))
  elif kind=='Fire':
   hot=np.clip(original/.13,0,1)**1.25;rgb=np.dstack((np.ones_like(hot),.12+.80*hot,.002+.35*hot**3))
  else:
   hot=np.clip(lum,0,1);rgb=np.dstack((.025+.25*hot,.30+.40*hot,np.ones_like(hot)));alpha=np.minimum(alpha,.82)
  a[:,:,:3]=np.clip(rgb*255,0,255).astype('uint8')
  a[:,:,3]=np.clip(alpha*255,0,255).astype('uint8');a[a[:,:,3]==0,:3]=0
  layer=Image.fromarray(a);dest=root/'05_Effects'/f'{kind}_FinalAlpha_{view}_2048.png';layer.save(dest)
  result=Image.alpha_composite(result,layer)
  records.append({'view':view,'kind':kind,'input':str(p),'output':str(dest),'alpha_gain':gain,'original_alpha_max':float(original.max()),'new_alpha_max':float(alpha.max()),'method':'Anew=1-(1-A)^gain; smoke capped .85; Rendered smoke luminance retained in charcoal grade; fire/ion emission colours graded to orange-yellow/cyan-blue; no shape painting; original 3D occlusion retained.'})
 a=np.asarray(result).copy();a[a[:,:,3]==0,:3]=0;result=Image.fromarray(a);out=root/'06_Preview'/f'Aurora_P8_{view}_2048_Final_v03.png';result.save(out)
 for label,bg in [('Dark',(12,20,31)),('OceanBlue',(8,88,135)),('Light',(220,225,230))]:
  Image.alpha_composite(Image.new('RGBA',result.size,(*bg,255)),result).convert('RGB').save(root/'06_Preview'/f'Aurora_P8_{view}_Final_v03_{label}.jpg',quality=95)
(root/'08_Report/FX_Alpha_Compositing_v03.json').write_text(json.dumps(records,indent=2));print('Two final transparent previews and separately editable FX layers saved')


