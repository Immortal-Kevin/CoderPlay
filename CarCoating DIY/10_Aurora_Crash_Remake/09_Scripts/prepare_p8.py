import pathlib,sys,json,hashlib,shutil
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageFilter
import numpy as np
src=root.parent/'02_Models/Aurora_Intact_Atlas2048'
p=src/'starship_crashed__-7178991039606161240.png';im=Image.open(p).convert('RGB');im.save(root/'03_Textures/Aurora_Original_Crash_Atlas_2048.png')
a=np.asarray(im,dtype=np.float32)/255;lum=a.mean(2);sat=a.max(2)-a.min(2);gold=(a[:,:,0]>a[:,:,2]*1.3)&(a[:,:,1]>a[:,:,2]*1.18)&(sat>.10);dark=lum<.28
rough=np.where(gold,.25,np.where(dark,.40,.31));metal=np.where(gold,.78,np.where(dark,.55,.23))
rough=np.clip(rough+(lum-.5)*.03,.16,.65)
for name,arr in [('Roughness',rough),('Metallic',metal)]:Image.fromarray((arr*255).astype('uint8')).save(root/'03_Textures'/f'Aurora_{name}_2048.png')
shutil.copy2(src/'starship_crashed_normal__-2168186086570603897_OpenGL.png',root/'03_Textures/Aurora_Original_Normal_OpenGL_2048.png')
# Exact source lettering: remove white matte, keep glyph colours; no generated text.
logos=[]
for name in ['Alterra Black Background.webp','Alterra White Background.webp']:
 pp=root.parent/'08_Aurora_HD_Remaster/02_Textures'/name;ii=Image.open(pp);logos.append({'path':str(pp),'size':ii.size,'mode':ii.mode,'sha256':hashlib.sha256(pp.read_bytes()).hexdigest()})
li=Image.open(root.parent/'08_Aurora_HD_Remaster/02_Textures/Alterra White Background.webp').convert('RGB');ar=np.asarray(li,dtype='float32')/255;alpha=np.clip(1-ar.min(2),0,1);rgb=np.clip((ar-(1-alpha[:,:,None]))/np.maximum(alpha[:,:,None],1e-6),0,1);out=np.dstack((rgb,alpha));out[alpha<.015]=0
Image.fromarray((out*255).astype('uint8'),'RGBA').save(root/'03_Textures/Alterra_Exact_Transparent.png')
# Local rear machinery patch is the only generative input. Never regenerate ship silhouette.
box=(1450,470,1962,982);crop=im.crop(box);crop.save(root/'04_AI/Scorch_Input_512.png')
(root/'08_Report/Source_Provenance.json').write_text(json.dumps({'atlas':str(p),'atlas_size':im.size,'atlas_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'logos':logos,'ai_crop_xyxy':box,'normal':'Original decoded OpenGL normal; unchanged','roughness_metallic':'Authored masks from original palette, not AI','P7_geometry_used':False},indent=2))
print('P8 native atlas / PBR / decals saved')
