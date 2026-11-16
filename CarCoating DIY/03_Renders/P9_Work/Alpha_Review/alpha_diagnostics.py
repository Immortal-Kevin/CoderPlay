import pathlib,sys,json
root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
work=pathlib.Path(__file__).parent;im=Image.open(root/'Alterra_full.png').convert('RGBA');a=np.array(im);font=ImageFont.truetype('arial.ttf',18)
for name,box in [('Far',(1140,240,1410,410)),('NearUpper',(1450,330,1632,530)),('NearLower',(1430,530,1632,760)),('Antenna',(970,0,1170,210))]:
 crop=im.crop(box);c=Image.new('RGBA',crop.size,(220,220,220,255));c=Image.alpha_composite(c,crop).convert('RGB').resize((crop.width*3,crop.height*3));d=ImageDraw.Draw(c)
 for x in range((box[0]//20+1)*20,box[2],20):d.line(((x-box[0])*3,0,(x-box[0])*3,c.height),fill=(180,50,50),width=1);d.text(((x-box[0])*3+2,0),str(x),font=font,fill=(255,30,30))
 for y in range((box[1]//20+1)*20,box[3],20):d.line((0,(y-box[1])*3,c.width,(y-box[1])*3),fill=(180,50,50),width=1);d.text((0,(y-box[1])*3),str(y),font=font,fill=(255,30,30))
 c.save(work/f'{name}_grid.jpg',quality=96)
stats={}
for name,(x,y,w,h) in {'background':(100,30,700,150),'farDarkMatte':(1280,285,50,20),'farCore':(1230,325,30,20),'farTip':(1350,310,25,20),'whiteHull':(450,500,100,60)}.items():
 p=a[y:y+h,x:x+w];stats[name]={'rgba_mean':p.mean((0,1)).tolist(),'alpha_percentiles':np.percentile(p[:,:,3],[0,25,50,75,100]).tolist()}
(work/'diagnostics.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2))
