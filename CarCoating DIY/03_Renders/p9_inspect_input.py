import pathlib,sys,json,hashlib
root=pathlib.Path(__file__).parent;sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
work=root/'P9_Work';work.mkdir(exist_ok=True)
path=root/'Alterra_full.png';im=Image.open(path).convert('RGBA');a=np.asarray(im);alpha=a[:,:,3];font=ImageFont.truetype('arial.ttf',24)
sheet=Image.new('RGB',(1632*2,964*2),(32,35,40));d=ImageDraw.Draw(sheet)
for n,(name,bg) in enumerate([('Original on dark',(16,22,31)),('Original on white',(240,240,240)),('Original on ocean blue',(8,88,135))]):
 flat=Image.alpha_composite(Image.new('RGBA',im.size,(*bg,255)),im).convert('RGB');flat.save(work/f'Input_{name.split()[-1]}.jpg',quality=96);sheet.paste(flat,((n%2)*1632,(n//2)*964));d.text(((n%2)*1632+20,(n//2)*964+20),name,font=font,fill=(255,90,20))
mask=Image.fromarray(alpha).convert('RGB');sheet.paste(mask,(1632,964));d.text((1652,984),'Original alpha',font=font,fill=(255,90,20));sheet.thumbnail((2448,1446));sheet.save(work/'Input_Background_Inspection.jpg',quality=95)
info={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':im.size,'mode':im.mode,'embedded_icc':bool(Image.open(path).info.get('icc_profile')),'assumed_colour_space':'sRGB; no embedded profile','target_size':[8000,round(im.height*8000/im.width)],'alpha_histogram':np.bincount(alpha.ravel(),minlength=256).tolist(),'nonzero_alpha_bbox':im.getchannel('A').getbbox(),'border_alpha_max':int(max(alpha[0].max(),alpha[-1].max(),alpha[:,0].max(),alpha[:,-1].max()))}
(work/'Input_Inspection.json').write_text(json.dumps(info,indent=2));print(json.dumps({k:v for k,v in info.items() if k!='alpha_histogram'},indent=2))
