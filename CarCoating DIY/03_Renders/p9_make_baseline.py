import pathlib,sys,json,time
root=pathlib.Path(__file__).parent;sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageCms
import numpy as np
work=root/'P9_Work';work.mkdir(exist_ok=True)
def resize_rgba_float(image,size):
 src=np.asarray(image.convert('RGBA'),dtype='float32')/255;sa=src[:,:,3]
 alpha=np.clip(np.asarray(Image.fromarray(sa).resize(size,Image.Resampling.LANCZOS)),0,1)
 out=np.empty((size[1],size[0],4),dtype='uint8');out[:,:,3]=np.round(alpha*255).astype('uint8')
 for c in range(3):
  pm=np.asarray(Image.fromarray(src[:,:,c]*sa).resize(size,Image.Resampling.LANCZOS))
  result=np.divide(pm,alpha,out=np.zeros_like(pm),where=alpha>1e-6);out[:,:,c]=np.round(np.clip(result,0,1)*255).astype('uint8')
 out[out[:,:,3]==0,:3]=0
 return Image.fromarray(out,'RGBA')
if __name__=='__main__':
 p=root/'Alterra_full_8000_Baseline.png'
 if p.exists():raise RuntimeError('Refusing to replace existing baseline')
 im=Image.open(root/'Alterra_full.png');size=(8000,round(im.height*8000/im.width));t=time.time();out=resize_rgba_float(im,size);profile=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes();out.save(p,icc_profile=profile)
 (work/'Baseline_Method.json').write_text(json.dumps({'method':'Lanczos in floating-point premultiplied RGBA, converted back to straight RGBA','size':size,'seconds':time.time()-t,'icc':'sRGB assumed for untagged original','original_alpha_retained':True},indent=2));print(str(p),size)
