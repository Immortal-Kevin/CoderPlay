import sys,pathlib,json,hashlib,shutil,csv
base=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(base/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
Image.MAX_IMAGE_PIXELS=200_000_000
def render_order(p):
 name=p.name;group=0 if name.startswith('starship_souvenir') else 1 if name.startswith('Aurora_Intact') else 2
 view=next((i for i,key in enumerate(['_Left_','_Right_','_Front_','_Rear_']) if key in name),9)
 return group,view
paths=sorted((base/'04_PrintReady').glob('*.png'),key=render_order);results=[]
font=ImageFont.truetype('msyh.ttc',19)
sheet=Image.new('RGB',(1800,390*((len(paths)+1)//2)),(235,235,235));draw=ImageDraw.Draw(sheet)
for i,p in enumerate(paths):
 with Image.open(p) as im:im.verify()
 im=Image.open(p);im.load();alpha=im.getchannel('A');hist=alpha.histogram();bbox=alpha.getbbox();w,h=im.size
 border=max(alpha.crop((0,0,w,1)).getextrema()[1],alpha.crop((0,h-1,w,h)).getextrema()[1],alpha.crop((0,0,1,h)).getextrema()[1],alpha.crop((w-1,0,w,h)).getextrema()[1])
 rec={'file':str(p),'width':w,'height':h,'mode':im.mode,'transparent_pixels':hist[0],'opaque_pixels':hist[255],'antialiased_pixels':sum(hist[1:255]),'alpha_bbox':bbox,'outer_border_max_alpha':border,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'opens':True,'passes':im.mode=='RGBA' and hist[0]>0 and hist[255]>0 and border==0}
 results.append(rec)
 thumb=im.copy();thumb.thumbnail((880,335));x=(i%2)*900;y=(i//2)*390
 for yy in range(y+40,y+380,20):
  for xx in range(x+5,x+895,20):draw.rectangle((xx,yy,xx+19,yy+19),fill=(180,180,180) if ((xx-x)//20+(yy-y)//20)%2 else (220,220,220))
 sheet.paste(thumb,(x+10+(880-thumb.width)//2,y+40+(335-thumb.height)//2),thumb)
 draw.text((x+10,y+5),p.stem,fill=(20,20,20),font=font)
 target=base/'03_Renders'/p.name
 if not target.exists():shutil.copy2(p,target)
 print(p.name,w,h,'alpha',hist[0],sum(hist[1:255]),'border',border,flush=True)
if paths:
 sheet.save(base/'05_Preview/Final_Render_ContactSheet.jpg',quality=92)
 if len(paths)>=4:sheet.crop((0,0,1800,780)).save(base/'05_Preview/Intact_Souvenir_Overview.jpg',quality=92)
(base/'06_Reports/PNG_Validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
