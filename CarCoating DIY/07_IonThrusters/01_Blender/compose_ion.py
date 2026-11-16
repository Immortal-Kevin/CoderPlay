import pathlib,sys,json,hashlib
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
import numpy as np
from PIL import Image,ImageFilter,ImageChops,ImageDraw
Image.MAX_IMAGE_PIXELS=180000000
def soft_rgba(im,radius):
 a=im.getchannel('A');prem=Image.merge('RGB',tuple(ImageChops.multiply(c,a) for c in im.convert('RGB').split()));prem=prem.filter(ImageFilter.GaussianBlur(radius));a=a.filter(ImageFilter.GaussianBlur(radius));aa=np.asarray(a,dtype=np.float32);rgb=np.array(prem,dtype=np.float32);rgb*=255/np.maximum(aa[:,:,None],1);rgb=np.clip(rgb,0,255).astype('uint8');return Image.merge('RGBA',(*Image.fromarray(rgb).split(),a))
def compose(view,width,rawpath=None,tag=''):
 final=width>=8000
 rawpath=pathlib.Path(rawpath) if rawpath else root/('04_ThrusterOnly' if final else '02_Preview')/f'{view}_ThrusterRaw_{width}.png'
 raw=Image.open(rawpath).convert('RGBA');size=raw.size
 source=root.parent/'04_PrintReady'/f'starship_souvenir_{view}_8000.png';body=Image.open(source).convert('RGBA')
 stats=json.loads((root.parent/'06_Reports/starship_souvenir_8000_Render_Stats.json').read_text());vh=next(v['height'] for v in stats['views'] if f'_{view}_8000' in v['file']);original_size=(width,round(vh*width/8000))
 if body.size!=original_size:body=body.resize(original_size,Image.Resampling.LANCZOS)
 # Work on a padded canvas so the Gaussian tail is not cut by the old frame.
 if size[0]>width:
  pad=(size[0]-width)//2;canvas=size;r=raw.copy();b=Image.new('RGBA',canvas);b.paste(body,(pad,pad))
 else:
  pad=round(width*.045);canvas=(size[0]+2*pad,size[1]+2*pad);r=Image.new('RGBA',canvas);r.paste(raw,(pad,pad));b=Image.new('RGBA',canvas);b.paste(body,(pad,pad))
 alpha=r.getchannel('A');far=alpha.filter(ImageFilter.GaussianBlur(width*.012));far=far.point(lambda x:round(x*.42));near=alpha.filter(ImageFilter.GaussianBlur(width*.006));near=near.point(lambda x:round(x*.35))
 layer=Image.new('RGBA',canvas,(0,88,255,0));layer.putalpha(far);n=Image.new('RGBA',canvas,(0,172,255,0));n.putalpha(near);layer=Image.alpha_composite(layer,n)
 layer=Image.alpha_composite(layer,soft_rgba(r,width*.0045))
 # A small blue halo is allowed to cross the rim as an optical glow; the 3D
 # holdout has already removed occluded core/plasma surfaces.
 combined=Image.alpha_composite(b,layer)
 # Preserve camera framing: do not crop/reproject. Uniform padding is the
 # only change; resample the padded image to the requested 8000/1600 width.
 output=(width,round(canvas[1]*width/canvas[0]));combined=combined.resize(output,Image.Resampling.LANCZOS);layer=layer.resize(output,Image.Resampling.LANCZOS)
 for im in [combined,layer]:
  arr=np.array(im);arr[arr[:,:,3]==0,:3]=0;im.paste(Image.fromarray(arr))
 dest=root/('03_FinalPNG' if final else '02_Preview')/f'Aurora_Ion_{view}_{width}{tag}.png';combined.save(dest)
 plume=root/'04_ThrusterOnly'/f'IonOnly_{view}_{width}{tag}.png';layer.save(plume)
 for name,color in [('Dark',(10,16,29)),('OceanBlue',(8,92,145))]:
  thumb=combined.copy();thumb.thumbnail((1800,1400));bg=Image.new('RGBA',thumb.size,(*color,255));bg=Image.alpha_composite(bg,thumb);bg.convert('RGB').save(root/'02_Preview'/f'{view}_{width}_{name}{tag}.jpg',quality=95)
 result={'view':view,'width':output[0],'height':output[1],'final':str(dest),'thruster_only':str(plume),'raw_3d':str(rawpath),'original_ship':str(source),'padding_each_side_fraction':pad/width,'method':'3D EEVEE emission surfaces + ship holdout; alpha-safe optical bloom; original P4 PNG ship plate'}
 (root/'05_Report'/f'{view}_{width}{tag}_Composite.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 return result
if __name__=='__main__':
 view=sys.argv[1] if len(sys.argv)>1 else 'Rear_ThreeQuarter';width=int(sys.argv[2]) if len(sys.argv)>2 else 1600
 compose(view,width,sys.argv[3] if len(sys.argv)>3 else None,sys.argv[4] if len(sys.argv)>4 else '')
