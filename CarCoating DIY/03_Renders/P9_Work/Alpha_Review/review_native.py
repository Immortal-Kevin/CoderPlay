import pathlib,sys,json,hashlib
root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
work=pathlib.Path(__file__).parent;final=Image.open(root/'Alterra_full_8000_Enhanced.png').convert('RGBA');base=Image.open(root/'Alterra_full_8000_Baseline.png').convert('RGBA');font=ImageFont.truetype('arial.ttf',20)
areas=[('Hull seam',(3100,2450,3520,2870)),('Mechanical',(4000,3450,4420,3870)),('Logo',(2410,3070,2830,3490)),('Antenna tip',(5140,40,5560,460))]
sheet=Image.new('RGB',(1720,960),(220,220,220));draw=ImageDraw.Draw(sheet)
for i,(label,box) in enumerate(areas):
 for j,(name,im) in enumerate([('Baseline',base),('Enhanced',final)]):
  crop=im.crop(box);flat=Image.alpha_composite(Image.new('RGBA',crop.size,(220,220,220,255)),crop).convert('RGB');x=(i%2)*860+j*430;y=(i//2)*480;sheet.paste(flat,(x+5,y+50));draw.text((x+5,y+8),label+' / '+name,font=font,fill='black')
sheet.save(work/'Final_NativePixel_Review.jpg',quality=97)
method=json.loads((root/'P9_Work/Enhancement_Method.json').read_text());checks=[]
for box in method['logo_core_final_boxes']:
 f=np.array(final.crop(box));b=np.array(base.crop(box));d=np.any(f[:,:,:3]!=b[:,:,:3],axis=2);checks.append({'box':box,'visible_RGB_exactly_matches_original_lanczos':bool(not np.any(d & (f[:,:,3]>0))),'changed_fully_transparent_RGB_pixels':int((d & (f[:,:,3]==0)).sum())})
(work/'Logo_Native_Pixel_QA.json').write_text(json.dumps({'logos':checks,'original_sha256':hashlib.sha256((root/'Alterra_full.png').read_bytes()).hexdigest()},indent=2));print(checks)
