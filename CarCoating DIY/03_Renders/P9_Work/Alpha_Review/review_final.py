import pathlib,sys,json
root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
work=pathlib.Path(__file__).parent;src=Image.open(root/'P9_Work/Clean_Source_RGBA.png').convert('RGBA');final=Image.open(root/'Alterra_full_8000_Enhanced.png');final.verify();final=Image.open(root/'Alterra_full_8000_Enhanced.png').convert('RGBA');alpha=final.getchannel('A');a=np.asarray(alpha);small=final.resize(src.size,Image.Resampling.LANCZOS)
font=ImageFont.truetype('arial.ttf',22)
sheet=Image.new('RGB',(2400,1500),(235,235,235));draw=ImageDraw.Draw(sheet)
for i,(label,box) in enumerate([('Antenna',(980,0,1160,180)),('Hull logo',(460,600,590,710)),('Far engine',(1150,270,1360,390)),('Near upper plume',(1470,350,1632,510)),('Cyan ring',(600,650,750,815)),('Nose edge',(0,610,150,820))]):
 for j,(lab,im) in enumerate([('Clean source',src),('Final downscaled to source',small)]):
  crop=im.crop(box);bg=Image.new('RGBA',crop.size,(230,230,230,255));out=Image.alpha_composite(bg,crop).convert('RGB');out.thumbnail((360,600));out=out.resize((out.width*2,out.height*2),Image.Resampling.NEAREST);out.thumbnail((380,650));x=(i%3)*800+j*400;y=(i//3)*750;sheet.paste(out,(x+10,y+70));draw.text((x+10,y+10),label,font=font,fill='black');draw.text((x+10,y+37),lab,font=font,fill='black')
sheet.save(work/'Final_Downscaled_Detail_Review.jpg',quality=96)
baseline=Image.open(root/'Alterra_full_8000_Baseline.png').getchannel('A');samealpha=np.array_equal(a,np.asarray(baseline))
info={'final_size':final.size,'final_rgba':final.mode,'decodes':True,'alpha_matches_baseline_exactly':samealpha,'alpha_min':int(a.min()),'alpha_max':int(a.max()),'semi_transparent_pixels':int(((a>0)&(a<255)).sum()),'zero_alpha_pixels':int((a==0).sum()),'source_size':src.size,'target_aspect_ratio_rounding_error_pixels':float(src.height*8000/src.width-final.height)}
(work/'Final_Independent_QA.json').write_text(json.dumps(info,indent=2));print(json.dumps(info,indent=2))
