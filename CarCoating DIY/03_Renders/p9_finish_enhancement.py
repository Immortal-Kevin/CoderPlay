import pathlib,sys,json,time,hashlib,math
root=pathlib.Path(__file__).parent;sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageFilter,ImageDraw,ImageCms
import numpy as np
from p9_make_baseline import resize_rgba_float
work=root/'P9_Work';dest=root/'Alterra_full_8000_Enhanced.png'
if dest.exists():raise RuntimeError('Refusing to overwrite existing requested output')
t=time.time();source=Image.open(root/'Alterra_full.png').convert('RGBA');clean=Image.open(work/'Clean_Source_RGBA.png').convert('RGBA');size=(8000,round(source.height*8000/source.width))
ai=Image.open(work/'AI_SR_RGB_4x.png').convert('RGB');assert ai.size==(source.width*4,source.height*4),ai.size
ai=ai.resize(size,Image.Resampling.LANCZOS)
base=resize_rgba_float(clean,size)
srcgray=np.asarray(source.convert('L'),dtype='float32');srcblur=np.asarray(source.convert('L').filter(ImageFilter.GaussianBlur(1.0)),dtype='float32')
detail=np.clip(np.abs(srcgray-srcblur)/15,0,1)
# Opaque interior receives inferred detail; the silhouette and transparent exhaust do not.
source_alpha=np.asarray(clean.getchannel('A'));interior=Image.fromarray(((source_alpha>=248)*255).astype('uint8')).filter(ImageFilter.MinFilter(7)).filter(ImageFilter.GaussianBlur(1.0))
weight=(.24+.34*detail)*(np.asarray(interior,dtype='float32')/255)
protection=Image.new('L',source.size,0);pd=ImageDraw.Draw(protection);logo_boxes=[(478,610,593,704),(958,197,1016,268)]
for box in logo_boxes:pd.rectangle((box[0]-7,box[1]-7,box[2]+7,box[3]+7),fill=255)
protection=protection.filter(ImageFilter.GaussianBlur(3));weight*=1-np.asarray(protection,dtype='float32')/255
Image.fromarray(np.round(weight*255).astype('uint8')).save(work/'AI_Detail_Weight_Mask.png');protection.save(work/'Logo_Protection_Mask.png')
weights=np.asarray(Image.fromarray(weight).resize(size,Image.Resampling.BILINEAR))
basegray=base.convert('L');aigray=ai.convert('L')
b=np.asarray(basegray,dtype='float32');a=np.asarray(aigray,dtype='float32')
low_b=np.asarray(basegray.filter(ImageFilter.GaussianBlur(10)),dtype='float32');low_a=np.asarray(aigray.filter(ImageFilter.GaussianBlur(10)),dtype='float32')
# Only bounded luminance detail from SR; broad tonal fields and chroma remain original.
delta=np.clip((a-b)-(low_a-low_b),-14,14)*weights
micro=np.clip(b-np.asarray(basegray.filter(ImageFilter.GaussianBlur(1.3)),dtype='float32'),-4,4)*.12*(weights/.58)
delta+=micro
out=np.asarray(base).copy()
for c in range(3):out[:,:,c]=np.round(np.clip(out[:,:,c].astype('float32')+delta,0,255)).astype('uint8')
# Exact baseline RGB inside logo cores, including every original letter and symbol.
baseline=Image.open(root/'Alterra_full_8000_Baseline.png').convert('RGBA');scale=size[0]/source.width;protected=[]
for box in logo_boxes:
 x0,y0,x1,y1=[round(v*scale) for v in box];patch=np.asarray(baseline.crop((x0,y0,x1,y1)));out[y0:y1,x0:x1,:3]=patch[:,:,:3];protected.append([x0,y0,x1,y1])
out[out[:,:,3]==0,:3]=0;result=Image.fromarray(out,'RGBA');icc=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes();result.save(dest,icc_profile=icc)
for label,bg in [('Dark',(16,22,31)),('White',(240,240,240)),('OceanBlue',(8,88,135))]:
 thumb=result.copy();thumb.thumbnail((2000,1400));Image.alpha_composite(Image.new('RGBA',thumb.size,(*bg,255)),thumb).convert('RGB').save(work/f'Enhanced_Overview_{label}.jpg',quality=96)
info={'input':str(root/'Alterra_full.png'),'output':str(dest),'model':'realesrgan-x4plus','backend':'ncnn Vulkan GPU 0 / Intel Arc B390','raw_sr_size':[source.width*4,source.height*4],'final_size':size,'tile_size':128,'processing_threads':'1:1:1; BelowNormal','blend':'Bounded AI luminance detail, 24–58% weight by original local contrast; no low-frequency/chroma replacement','max_sr_delta_before_weight':14,'micro_sharpen':'1.3px radius, 0.12 amount, clipped 4/255, opaque interior only','logo_core_source_boxes':logo_boxes,'logo_core_final_boxes':protected,'logo_core_RGB':'Exact copy of original Lanczos baseline','alpha':'Source-based repair; no AI alpha prediction','sr_raw_is_inferred_detail_not_native_8k':True,'seconds_final_processing':time.time()-t,'enhanced_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
(work/'Enhancement_Method.json').write_text(json.dumps(info,indent=2));print(str(dest),size,flush=True)
