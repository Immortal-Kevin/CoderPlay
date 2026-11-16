import pathlib,sys,json,hashlib,csv
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
Image.MAX_IMAGE_PIXELS=180000000
font=ImageFont.truetype('msyh.ttc',36)
def pair(pa,pb,path,labels):
 a=Image.open(pa).convert('RGBA');b=Image.open(pb).convert('RGBA');assert a.size==b.size
 w,h=a.size;out=Image.new('RGB',(w*2,h+70),(12,19,31));draw=ImageDraw.Draw(out)
 for i,im in enumerate([a,b]):
  bg=Image.new('RGBA',im.size,(10,16,29,255));im=Image.alpha_composite(bg,im).convert('RGB');out.paste(im,(w*i,70));draw.text((w*i+25,12),labels[i],font=font,fill='white')
 out.save(path,quality=96)
pair(root/'04_Comparison/Ring_Original_1800.png',root/'04_Comparison/Ring_HD_Final_1800.png',root/'04_Comparison/Ring_Before_After.jpg',['原版：12 段轮廓 / 512 纹理','重制：128 段真实几何 / 局部材质重建'])
pair(root/'04_Comparison/Aurora_Original_Rear_ThreeQuarter_2048.png',root/'04_Comparison/Aurora_HD_Rear_ThreeQuarter_2048.png',root/'04_Comparison/WholeShip_Before_After_2048.jpg',['原版模型与材质，同相机/光照','高清重制，同相机/光照，保留 P5 尾焰'])
original=Image.open(next((root.parent/'02_Models/starship_souvenir').glob('starship_souvenir__*.png'))).convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS);new=Image.open(root/'02_Textures/Aurora_BaseColor_4096.png').resize((1024,1024),Image.Resampling.LANCZOS);texture=Image.new('RGB',(2048,1080),(20,28,35));texture.paste(original,(0,56));texture.paste(new,(1024,56));draw=ImageDraw.Draw(texture);draw.text((20,8),'原版 512，同为 Lanczos 缩放',font=font,fill='white');draw.text((1044,8),'重制 4096，缩放至相同显示尺寸',font=font,fill='white');texture.save(root/'04_Comparison/Texture_Comparison_Consistent.jpg',quality=96)
records=[]
for p in sorted((root/'05_FinalPNG').glob('*.png')):
 with Image.open(p) as test:test.verify()
 im=Image.open(p);im.load();a=im.getchannel('A');hist=a.histogram();w,h=im.size;border=max(a.crop((0,0,w,1)).getextrema()[1],a.crop((0,h-1,w,h)).getextrema()[1],a.crop((0,0,1,h)).getextrema()[1],a.crop((w-1,0,w,h)).getextrema()[1]);records.append({'file':str(p),'size':[w,h],'mode':im.mode,'bbox':a.getbbox(),'border_max_alpha':border,'transparent_pixels':hist[0],'partial_alpha_pixels':sum(hist[1:255]),'passes':w==8000 and im.mode=='RGBA' and border==0 and hist[0]>0 and sum(hist[1:255])>0,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()});print(p.name,records[-1]['passes'],flush=True)
(root/'06_Report/Final_PNG_Validation.json').write_text(json.dumps(records,indent=2))
prior=[]
for listfile in [root.parent/'06_Reports/Delivery_File_Hashes.csv',root.parent/'07_IonThrusters/05_Report/Delivery_Manifest.csv']:
 for r in csv.DictReader(listfile.open(encoding='utf-8-sig')):
  p=pathlib.Path(r['absolute_path']);prior.append({'file':str(p),'unchanged':p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']})
(root/'06_Report/Prior_Delivery_Integrity.json').write_text(json.dumps(prior,indent=2));print('Prior unchanged',sum(r['unchanged'] for r in prior),'/',len(prior),flush=True)
views=['Rear_ThreeQuarter','Front_ThreeQuarter','Left','Right'];sheet=Image.new('RGB',(2000,4*850),(10,16,29));draw=ImageDraw.Draw(sheet)
for i,v in enumerate(views):
 p=root/'04_Comparison'/f'HD_{v}_8000_Dark.jpg'
 if not p.exists():continue
 im=Image.open(p);im.thumbnail((1960,780));sheet.paste(im,((2000-im.width)//2,i*850+65+(780-im.height)//2));draw.text((30,i*850+10),v+' / HD Remaster',font=font,fill='white')
sheet.save(root/'04_Comparison/HD_FourViews_Overview.jpg',quality=94)
