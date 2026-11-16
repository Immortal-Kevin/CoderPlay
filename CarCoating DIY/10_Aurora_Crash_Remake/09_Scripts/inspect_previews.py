import pathlib,sys,json
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
font=ImageFont.truetype('arial.ttf',25)
def flat(im,bg):
 im=im.convert('RGBA');return Image.alpha_composite(Image.new('RGBA',im.size,(*bg,255)),im).convert('RGB')
for view in ['Front_ThreeQuarter','Rear_ThreeQuarter']:
 im=Image.open(root/'06_Preview'/f'Aurora_P8_{view}_2048.png')
 for name,bg in [('Dark',(12,20,31)),('OceanBlue',(8,88,135)),('Light',(220,225,230))]:flat(im,bg).save(root/'06_Preview'/f'Aurora_P8_{view}_{name}.jpg',quality=95)
sheet=Image.new('RGB',(2000,1500),(12,20,31));draw=ImageDraw.Draw(sheet)
for i,label in enumerate(['Front','Rear','Port','Starboard']):
 im=flat(Image.open(root/'06_Preview'/f'Bridge_Connection_{label}_1400.png'),(12,20,31));im.thumbnail((1000,700));x=(i%2)*1000;y=(i//2)*750;sheet.paste(im,(x+(1000-im.width)//2,y+40));draw.text((x+20,y+10),label+' / original connected bridge',font=font,fill='white')
sheet.save(root/'07_Comparison/Bridge_Connection_FourDirections.jpg',quality=95)
print('Background and four-direction inspection images saved')
