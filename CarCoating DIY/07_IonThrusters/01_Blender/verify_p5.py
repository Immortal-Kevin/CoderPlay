import pathlib,sys,json,csv,hashlib
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
Image.MAX_IMAGE_PIXELS=180000000
records=[]
for folder,pattern in [('03_FinalPNG','*.png'),('04_ThrusterOnly','IonOnly_*_8000.png')]:
 for p in sorted((root/folder).glob(pattern)):
  with Image.open(p) as test:test.verify()
  im=Image.open(p);im.load();a=im.getchannel('A');hist=a.histogram();w,h=im.size
  border=max(a.crop((0,0,w,1)).getextrema()[1],a.crop((0,h-1,w,h)).getextrema()[1],a.crop((0,0,1,h)).getextrema()[1],a.crop((w-1,0,w,h)).getextrema()[1])
  bbox=a.getbbox();rec={'file':str(p),'size':[w,h],'mode':im.mode,'transparent_pixels':hist[0],'gradient_alpha_pixels':sum(hist[1:255]),'alpha_bbox':bbox,'border_max_alpha':border,'passes':im.mode=='RGBA' and w==8000 and hist[0]>0 and sum(hist[1:255])>0 and border==0,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()};records.append(rec);print(p.name,rec['passes'],rec['size'],flush=True)
(root/'05_Report/PNG_Alpha_Validation.json').write_text(json.dumps(records,indent=2))
prior=[]
for r in csv.DictReader((root.parent/'06_Reports/Delivery_File_Hashes.csv').open(encoding='utf-8-sig')):
 p=pathlib.Path(r['absolute_path']);actual=hashlib.sha256(p.read_bytes()).hexdigest();prior.append({'file':str(p),'unchanged':actual==r['sha256']})
(root/'05_Report/P1_P4_Unchanged.json').write_text(json.dumps(prior,indent=2))
views=['Rear_ThreeQuarter','Front_ThreeQuarter','Left','Right'];sheet=Image.new('RGB',(1800,4*680),(25,32,45));draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('msyh.ttc',24)
for i,view in enumerate(views):
 for j,name in enumerate(['Dark','OceanBlue']):
  p=root/'02_Preview'/f'{view}_8000_{name}.jpg'
  if not p.exists():continue
  im=Image.open(p);im.thumbnail((890,620));x=j*900+(900-im.width)//2;y=i*680+45+(620-im.height)//2;sheet.paste(im,(x,y));draw.text((j*900+16,i*680+10),view+' / '+name,fill='white',font=font)
sheet.save(root/'02_Preview/P5_AllViews_Background_Check.jpg',quality=94)
print('P1-P4 unchanged',sum(r['unchanged'] for r in prior),'/',len(prior))
