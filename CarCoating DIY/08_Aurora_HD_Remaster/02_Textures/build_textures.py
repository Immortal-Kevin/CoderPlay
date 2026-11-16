import pathlib,sys,json,hashlib
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
import numpy as np
from PIL import Image,ImageFilter,ImageDraw
srcA=root.parent/'02_Models/starship_souvenir';srcB=root.parent/'02_Models/Aurora_Intact_Atlas2048'
a=Image.open(next(srcA.glob('starship_souvenir__*.png'))).convert('RGB');b=Image.open(next(srcB.glob('starship_crashed__*.png'))).convert('RGB')
size=(4096,4096);low=np.asarray(a,dtype=np.float32);bl=np.asarray(b.resize(a.size,Image.Resampling.LANCZOS),dtype=np.float32)
lum=low.mean(2);blum=bl.mean(2);delta=lum-blum
bad=((delta>20)&(lum>55))|((bl[:,:,0]>bl[:,:,1]*1.5)&(bl[:,:,0]>90)&(low[:,:,0]<low[:,:,1]*1.3))
mask=Image.fromarray((bad*255).astype('uint8')).filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(2))
# Keep original markings/text silhouettes wherever native versions differ.
protected=Image.new('L',a.size);dr=ImageDraw.Draw(protected)
for rect in [(30,350,70,404),(404,348,461,450),(156,201,177,220)]:dr.rectangle(rect,fill=255)
mask=np.maximum(np.asarray(mask),np.asarray(protected));mask=Image.fromarray(mask).resize(size,Image.Resampling.LANCZOS);mask.save(root/'02_Textures/Damage_Replacement_Mask_4096.png')
A=a.resize(size,Image.Resampling.LANCZOS);B=b.resize(size,Image.Resampling.LANCZOS);fused=Image.composite(A,B,mask);fused=fused.filter(ImageFilter.UnsharpMask(radius=1.2,percent=75,threshold=5))
# Reconstruct crisp boundaries only for existing yellow paint. No new lines/text.
arr=np.array(fused);hsv=np.asarray(fused.convert('HSV'));yellow=((hsv[:,:,0]>17)&(hsv[:,:,0]<45)&(hsv[:,:,1]>90)&(hsv[:,:,2]>60))
ym=Image.fromarray((yellow*255).astype('uint8')).filter(ImageFilter.GaussianBlur(.6)).point(lambda v:max(0,min(255,round((v-90)*255/75))))
yp=np.array(ym,dtype=np.float32)/255;seed=np.random.default_rng(60128);grain=seed.normal(0,.65,arr.shape[:2]).astype('float32')
out=arr.astype('float32')+grain[:,:,None]*.45
# Existing hue and brightness stay intact; only small subpixel antialias colors are regularized.
yellowcolor=np.array([171,126,43],dtype='float32');weak=yp*(1-yp)*.5;out=out*(1-weak[:,:,None])+yellowcolor*weak[:,:,None]
out=np.clip(out,0,255).astype('uint8');Image.fromarray(out).save(root/'02_Textures/Aurora_BaseColor_4096.png')
ym.save(root/'02_Textures/Existing_Yellow_Paint_Mask_4096.png')
# UV-aligned normal restoration from real normal maps, with conservative fine grain.
na=Image.open(next(srcA.glob('*normal*OpenGL.png'))).convert('RGB').resize(size,Image.Resampling.LANCZOS);nb=Image.open(next(srcB.glob('starship_crashed_normal*OpenGL.png'))).convert('RGB').resize(size,Image.Resampling.LANCZOS)
normal=Image.composite(na,nb,mask);norm=np.array(normal,dtype=np.float32)/127.5-1;norm[:,:,:2]+=seed.normal(0,.006,norm[:,:,:2].shape);norm/=np.maximum(np.linalg.norm(norm,axis=2,keepdims=True),1e-4);Image.fromarray(np.clip((norm+1)*127.5,0,255).astype('uint8')).save(root/'02_Textures/Aurora_Normal_4096.png')
# Separate roughness and metal response, not diffuse-painted fake detail.
rgb=out.astype('float32')/255;bright=rgb.mean(2);cyan=(rgb[:,:,1]>rgb[:,:,0]*1.3)&(rgb[:,:,2]>rgb[:,:,0]*1.3)&(rgb[:,:,1]>.2)
rough=np.where(bright>.52,.48,.37)+grain*.007;rough=np.where(cyan,.24,rough);rough=np.where(yellow,.44,rough);Image.fromarray(np.clip(rough*255,0,255).astype('uint8')).save(root/'02_Textures/Aurora_Roughness_4096.png')
metal=np.where(bright>.52,.3,.65);metal=np.where(yellow,.24,metal);Image.fromarray((metal*255).astype('uint8')).save(root/'02_Textures/Aurora_Metallic_4096.png')
# Original illumination channels; new emission edges additionally follow the clean color atlas.
illum=Image.open(next(srcA.glob('*illum*.png'))).convert('RGB').resize(size,Image.Resampling.LANCZOS);ill=np.array(illum,dtype='float32');cm=Image.fromarray((cyan*255).astype('uint8')).filter(ImageFilter.GaussianBlur(.55));cm=np.asarray(cm,dtype='float32')/255
ill=np.maximum(ill,rgb*cm[:,:,None]*120);Image.fromarray(np.clip(ill,0,255).astype('uint8')).save(root/'02_Textures/Aurora_Emission_4096.png')
# Record a genuine before/after texture comparison, not a claimed native 4K asset.
canvas=Image.new('RGB',(2048,1024));a=a.resize((1024,1024),Image.Resampling.NEAREST);f=Image.fromarray(out).resize((1024,1024),Image.Resampling.LANCZOS);canvas.paste(a,(0,0));canvas.paste(f,(1024,0));canvas.save(root/'04_Comparison/Texture_Original512_vs_Remaster4096.jpg',quality=95)
report={'base_source_sizes':[[512,512],[2048,2048]],'output_size':[4096,4096],'method':'Real 2048 source detail + original clean 512 restoration masks, existing-paint edge reconstruction, separate normal/roughness/metallic/emission with conservative micrograin','new_mechanical_letters_or_rivets':False,'mask_coverage_fraction':float(np.mean(np.asarray(mask)>127)),'ai_used':False,'warning':'4096 is authored remaster working resolution; not recovered original 4K detail. Locally restored source512 regions remain detail limited.'}
(root/'06_Report/Texture_Remaster.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
