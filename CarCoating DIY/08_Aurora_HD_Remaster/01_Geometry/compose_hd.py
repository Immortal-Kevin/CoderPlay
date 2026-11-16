import pathlib,sys,json
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
Image.MAX_IMAGE_PIXELS=180000000
view=sys.argv[1];width=int(sys.argv[2]);original='original' in sys.argv;label='Original' if original else 'HD';body=Image.open(root/'04_Comparison'/f'{label}_{view}_{width}_Body.png').convert('RGBA');tailpath=root.parent/'07_IonThrusters/04_ThrusterOnly'/f'IonOnly_{view}_8000.png';tail=Image.open(tailpath).convert('RGBA')
if tail.size!=body.size:tail=tail.resize(body.size,Image.Resampling.LANCZOS)
im=Image.alpha_composite(body,tail);arr=np.array(im);arr[arr[:,:,3]==0,:3]=0;im=Image.fromarray(arr)
folder='05_FinalPNG' if width==8000 and not original else '04_Comparison';path=root/folder/f'Aurora_{label}_{view}_{width}.png';im.save(path)
for bg,color in [('Dark',(10,16,29)),('OceanBlue',(8,92,145))]:
 thumb=im.copy();thumb.thumbnail((2000,1600));background=Image.new('RGBA',thumb.size,(*color,255));Image.alpha_composite(background,thumb).convert('RGB').save(root/'04_Comparison'/f'{label}_{view}_{width}_{bg}.jpg',quality=95)
print(path,im.size,flush=True)
