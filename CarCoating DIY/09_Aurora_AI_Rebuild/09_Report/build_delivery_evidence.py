import sys,pathlib,json,csv,hashlib
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
Image.MAX_IMAGE_PIXELS=180000000
font=ImageFont.truetype('arial.ttf',26)
def flatten(path,bg=(8,14,25)):
 im=Image.open(path).convert('RGBA');return Image.alpha_composite(Image.new('RGBA',im.size,(*bg,255)),im).convert('RGB')
def sheet(items,path,columns=2,cell=(1200,950)):
 out=Image.new('RGB',(columns*cell[0],((len(items)+columns-1)//columns)*cell[1]),(8,14,25));draw=ImageDraw.Draw(out)
 for n,(label,im) in enumerate(items):
  im=im.copy();im.thumbnail((cell[0]-24,cell[1]-65));x=(n%columns)*cell[0];y=(n//columns)*cell[1]
  out.paste(im,(x+(cell[0]-im.width)//2,y+50+(cell[1]-60-im.height)//2));draw.text((x+20,y+14),label,font=font,fill=(225,232,242))
 out.save(path,quality=95)
preview=root/'06_Preview';comp=root/'08_Comparison'
sheet([('P6 - same camera / P7 studio lighting',flatten(preview/'Aurora_P7_P6_Control_Front_ThreeQuarter_2048.png')),('P7 - rebuilt geometry / AI PBR',flatten(preview/'Aurora_P7_StandardFinal_Front_ThreeQuarter_2048.png'))],comp/'P6_P7_SameCamera_SameLight.jpg')
sheet([('P7 Standard',flatten(preview/'Aurora_P7_StandardFinal_Front_ThreeQuarter_2048.png')),('P7 Metallic enhancement',flatten(preview/'Aurora_P7_MetallicFinal_Front_ThreeQuarter_2048.png'))],comp/'Standard_Metallic_2048_Comparison.jpg')
sheet([('P6 Engine - same camera and lighting',flatten(preview/'Engine_P6_SameLight_1800.png')),('P7 Engine - independent mechanical parts',flatten(preview/'Engine_P7_1800.png'))],comp/'Engine_Geometry_SameLight.jpg',cell=(1200,1050))
cropbox=(650,450,1162,962)
sheet([(label,flatten(preview/name).crop(cropbox).resize((1024,1024),Image.Resampling.NEAREST)) for label,name in [('P6 - 512px crop at 200%','Engine_P6_SameLight_1800.png'),('P7 - matching 512px crop at 200%','Engine_P7_1800.png')]],comp/'Engine_200Percent_Comparison.jpg',cell=(1100,1090))
sheet([(label,flatten(preview/name)) for label,name in [('Hull side +1 / exact ALTERRA','Logo_Hull_1_Final_v03_1800.png'),('Hull side -1 / exact ALTERRA','Logo_Hull_-1_Final_v03_1800.png'),('Top fin +1 / exact ALTERRA','Logo_TopFin_1_1800.png'),('Top fin -1 / exact ALTERRA','Logo_TopFin_-1_1800.png')]],comp/'Alterra_Logo_Inspection.jpg',cell=(1000,900))
validation=[]
for variant in ['Standard','Metallic']:
 items=[]
 for view in ['Front_ThreeQuarter','Rear_ThreeQuarter','Left','Right']:
  p=root/'07_FinalPNG'/f'Aurora_P7_{variant}_{view}_8000.png'
  with Image.open(p) as im:im.verify()
  with Image.open(p) as im:
   im.load();assert im.mode=='RGBA';a=np.asarray(im);alpha=a[:,:,3];ys,xs=np.where(alpha>0)
   bounds=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
   entry={'path':str(p),'width':im.width,'height':im.height,'mode':im.mode,'alpha_min':int(alpha.min()),'alpha_max':int(alpha.max()),'transparent_pixels':int((alpha==0).sum()),'partial_alpha_pixels':int(((alpha>0)&(alpha<255)).sum()),'visible_bounds':bounds,'outer_border_alpha_max':int(max(alpha[0].max(),alpha[-1].max(),alpha[:,0].max(),alpha[:,-1].max())),'transparent_rgb_nonzero':int(np.any(a[:,:,:3][alpha==0]!=0,axis=1).sum())}
   entry['pass']=entry['outer_border_alpha_max']==0 and entry['transparent_rgb_nonzero']==0 and entry['partial_alpha_pixels']>0 and im.width==8000
   validation.append(entry)
  items.append((variant+' / '+view,flatten(preview/f'P7_{variant}_{view}_8000_Dark.jpg')))
 sheet(items,comp/f'P7_{variant}_FourViews.jpg',cell=(1300,1000))
(root/'09_Report/Final_PNG_Validation.json').write_text(json.dumps(validation,indent=2))
old=[]
for manifest in [root.parent/'06_Reports/Delivery_File_Hashes.csv',root.parent/'07_IonThrusters/05_Report/Delivery_Manifest.csv',root.parent/'08_Aurora_HD_Remaster/06_Report/Delivery_Manifest.csv']:
 with manifest.open(encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f):
   p=pathlib.Path(row['absolute_path']);digest=hashlib.file_digest(p.open('rb'),'sha256').hexdigest() if p.exists() else None
   old.append({'path':str(p),'expected':row['sha256'],'actual':digest,'unchanged':digest==row['sha256']})
(root/'09_Report/P1_P6_Preservation_Check.json').write_text(json.dumps({'records':len(old),'unchanged':sum(r['unchanged'] for r in old),'items':old},indent=2))
print(json.dumps({'final_png_count':len(validation),'all_png_pass':all(r['pass'] for r in validation),'prior_records':len(old),'unchanged':sum(r['unchanged'] for r in old)},indent=2))
