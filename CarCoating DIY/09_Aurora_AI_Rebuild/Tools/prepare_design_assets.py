import pathlib,sys,json
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
import numpy as np
from PIL import Image,ImageFilter,ImageDraw,ImageFont
sources=[]
for name in ['White','Black']:
 p=root.parent/'08_Aurora_HD_Remaster/02_Textures'/f'Alterra {name} Background.webp';im=Image.open(p);sources.append({'file':str(p),'size':list(im.size),'mode':im.mode,'alpha':'A' in im.getbands()})
white=Image.open(sources[0]['file']).convert('RGB');arr=np.array(white,dtype='float32');alpha=1-arr.min(2)/255;rgb=np.clip((arr-255*(1-alpha[:,:,None]))/np.maximum(alpha[:,:,None],1e-5),0,255);rgba=np.dstack([rgb,alpha*255]).astype('uint8');im=Image.fromarray(rgba);bbox=im.getchannel('A').point(lambda x:255 if x>32 else 0).getbbox();im=im.crop(bbox);outsize=(1024,round(1024*im.height/im.width));im=im.resize(outsize,Image.Resampling.LANCZOS);a=im.getchannel('A').filter(ImageFilter.GaussianBlur(.45));a=a.point(lambda x:max(0,min(255,round((x-55)*255/145))));im.putalpha(a);im.save(root/'05_Alterra_Decals/Alterra_Dark_Transparent_1024.png')
ar=np.array(im);gold=(ar[:,:,0]>ar[:,:,2]+50)&(ar[:,:,0]>120);light=ar.copy();light[:,:,:3]=np.where(gold[:,:,None],ar[:,:,:3],245);Image.fromarray(light).save(root/'05_Alterra_Decals/Alterra_Light_Transparent_1024.png')
proof=Image.new('RGB',(1200,700),(235,240,244));d=ImageDraw.Draw(proof);d.rectangle((600,0,1200,700),fill=(8,27,43))
for x,p in [(40,root/'05_Alterra_Decals/Alterra_Dark_Transparent_1024.png'),(640,root/'05_Alterra_Decals/Alterra_Light_Transparent_1024.png')]:
 logo=Image.open(p);logo.thumbnail((520,600));proof.paste(logo,(x,50),logo)
proof.save(root/'05_Alterra_Decals/Logo_Transparency_Check.jpg',quality=96)
(root/'09_Report/Logo_Source_Inspection.json').write_text(json.dumps({'sources':sources,'output_size':outsize,'method':'Exact supplied glyphs; white matte removal, high-resolution alpha edge reconstruction; dark/light variants; no AI lettering'},indent=2))
# Local structural input guides for img2img: not a whole-ship image.
for name,bg,seam in [('WhiteArmor',(224,228,232),(120,130,140)),('Silver',(155,162,170),(75,85,95)),('DarkMetal',(45,55,67),(18,25,35)),('ChampagneGold',(187,145,74),(110,80,35))]:
 im=Image.new('RGB',(512,512),bg);d=ImageDraw.Draw(im)
 for box in [(16,16,252,248),(264,16,496,248),(16,260,496,496)]:
  d.rounded_rectangle(box,radius=10,outline=seam,width=3)
  x0,y0,x1,y1=box;d.line((x0+15,y0+10,x1-15,y0+10),fill=tuple(min(255,c+10) for c in bg),width=2)
 im.save(root/'03_AI_Textures'/f'InputGuide_{name}_512.png')
print('Logos and img2img guides saved',flush=True)
