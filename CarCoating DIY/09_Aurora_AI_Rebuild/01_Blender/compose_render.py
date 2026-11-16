import pathlib,sys,json
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image
import numpy as np
Image.MAX_IMAGE_PIXELS=180000000
view=sys.argv[1];width=int(sys.argv[2]);variant=sys.argv[3];bodypath=pathlib.Path(sys.argv[4]);body=Image.open(bodypath).convert('RGBA');tail=Image.open(root.parent/'07_IonThrusters/04_ThrusterOnly'/f'IonOnly_{view}_8000.png').convert('RGBA')
if tail.size!=body.size:tail=tail.resize(body.size,Image.Resampling.LANCZOS)
out=Image.alpha_composite(body,tail);a=np.array(out);a[a[:,:,3]==0,:3]=0;out=Image.fromarray(a)
dest=root/('07_FinalPNG' if width==8000 else '06_Preview')/f'Aurora_P7_{variant}_{view}_{width}.png';out.save(dest)
for bg,color in [('Dark',(8,14,25)),('OceanBlue',(8,92,145))]:
 im=out.copy();im.thumbnail((2048,1600));background=Image.new('RGBA',im.size,(*color,255));Image.alpha_composite(background,im).convert('RGB').save(root/'06_Preview'/f'P7_{variant}_{view}_{width}_{bg}.jpg',quality=95)
print(str(dest),out.size,flush=True)
