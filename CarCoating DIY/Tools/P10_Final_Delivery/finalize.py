import os,sys
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'Tools/P10_Final_Delivery/pythonlibs'))
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,PngImagePlugin
from pathlib import Path
import json,hashlib,zlib,secrets,datetime,io,time,gc
cv2.setNumThreads(4)
T=Path(str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'Tools/P10_Final_Delivery')); O=Path(str(__import__('pathlib').Path(__file__).resolve().parents[2] / '03_Renders'))
INPUT=O/'Aurora_P10_Remaster_Preview.png'
TEXT='cr：Subnautica - Aurora / UnknownWorld / Codex / Kevin L 第十版AI重制'
META={'Author':'Kevin L','Copyright':'Subnautica Aurora derivative design preview, edited by Kevin L','Project':'Aurora_P10','Watermark-ID':'KL-AURORA-P10-001','Date':'2026-10-28'}
CW,CH=4000,2363;N=16
payload=b'P10WM1|Kevin L|Aurora_P10|2026-10-28|KL-AURORA-P10-001'
packet=payload+zlib.crc32(payload).to_bytes(4,'big');bits=np.unpackbits(np.frombuffer(packet,dtype=np.uint8))
x=np.arange(N);k=x[:,None];C=(np.sqrt(2/N)*np.cos(np.pi*(2*x+1)*k/(2*N))).astype(np.float32);C[0]/=np.sqrt(2)

def log(s):print(s,flush=True)
def info():
 m=PngImagePlugin.PngInfo()
 for key,v in META.items():m.add_itxt(key,v)
 m.add_itxt('Description','Conservative Real-ESRGAN x4plus Vulkan detail fusion; reconstructed alpha from flattened RGB original; DCT pixel watermark KL-AURORA-P10-001.')
 return m

def canonical(image):return np.asarray(image.convert('RGB').resize((CW,CH),Image.Resampling.LANCZOS),dtype=np.float32)
def blockify(y):return y[:CH//N*N,:CW//N*N].reshape(CH//N,N,CW//N,N).transpose(0,2,1,3).reshape(-1,N,N)
def restore(b):return b.reshape(CH//N,CW//N,N,N).transpose(0,2,1,3).reshape(CH//N*N,CW//N*N)
def make_manifest(image):
 rgb=canonical(image);y=rgb@np.array([.299,.587,.114],np.float32);b=blockify(y);a=blockify(np.asarray(image.getchannel('A').resize((CW,CH),Image.Resampling.LANCZOS),dtype=np.float32))
 eligible=np.flatnonzero((a.min((1,2))>=254)&(b.min((1,2))>35)&(b.max((1,2))<249)&(b.std((1,2))<35))
 seed=secrets.randbits(32);rng=np.random.default_rng(seed);rng.shuffle(eligible)
 assert len(eligible)>len(bits)*6,('insufficient carriers',len(eligible),len(bits))
 return {'canonical':[CW,CH],'block':N,'positions':eligible.tolist(),'seed':seed,'payload':payload.decode(),'crc32':zlib.crc32(payload),'strength':18.,'bit_length':len(bits),'algorithm':'keyed repeated mid-frequency DCT coefficient-pair differential sign; canonical scale normalization; CRC32'}

def embed(image,m):
 rgb=canonical(image);y=rgb@np.array([.299,.587,.114],np.float32);allb=blockify(y).copy();idx=np.array(m['positions']);sel=allb[idx]
 co=C@sel@C.T;sign=2*bits[np.arange(len(idx))%len(bits)].astype(np.float32)-1
 diff=co[:,3,4]-co[:,4,3];shift=sign*np.maximum(0,m['strength']-sign*diff)*.5
 co[:,3,4]+=shift;co[:,4,3]-=shift
 allb[idx]=C.T@co@C
 delta=np.zeros((CH,CW),np.float32);delta[:CH//N*N,:CW//N*N]=restore(allb)-y[:CH//N*N,:CW//N*N]
 # Modify opaque hull carriers only; alpha/glow and all transparent pixels are untouched.
 deltaim=Image.fromarray(delta,'F').resize(image.size,Image.Resampling.BICUBIC)
 out=Image.new('RGBA',image.size)
 for top in range(0,image.height,192):
  box=(0,top,image.width,min(image.height,top+192));arr=np.array(image.crop(box));d=np.array(deltaim.crop(box));d*=np.asarray(arr[:,:,3]>=254,dtype=np.float32)
  arr[:,:,:3]=np.uint8(np.clip(arr[:,:,:3].astype(np.float32)+d[:,:,None],0,255)+.5);arr[arr[:,:,3]==0,:3]=0
  out.paste(Image.fromarray(arr,'RGBA'),(0,top))
 return out

def detect(image,m):
 y=canonical(image)@np.array([.299,.587,.114],np.float32);idx=np.array(m['positions']);co=C@blockify(y)[idx]@C.T;diff=co[:,3,4]-co[:,4,3]
 # Clip isolated strong crop/JPEG artifacts before repeated-bit voting.
 diff=np.clip(diff,-80,80);sums=np.bincount(np.arange(len(idx))%len(bits),weights=diff,minlength=len(bits));decoded=np.uint8(sums>0)
 raw=np.packbits(decoded).tobytes();body=raw[:-4];crc=int.from_bytes(raw[-4:],'big')
 return {'bit_accuracy':float(np.mean(decoded==bits)),'bit_errors':int(np.sum(decoded!=bits)),'crc_pass':zlib.crc32(body)==crc,'payload_match':body==payload,'decoded':body.decode('utf-8',errors='replace')}

def signature(image):
 out=image.copy();font=ImageFont.truetype('msyh.ttc',max(26,round(image.width*.0065)))
 draw=ImageDraw.Draw(out);bb=draw.textbbox((0,0),TEXT,font=font);margin=round(image.width*.014)
 x=image.width-margin-(bb[2]-bb[0])-bb[0];y=image.height-margin-(bb[3]-bb[1])-bb[1]
 assert x>0 and y>0
 # The transparent bottom-right safety strip avoids the hull and fin.
 alpha=np.asarray(image.getchannel('A').crop((int(x),int(y+bb[1]),image.width-margin,image.height-margin)))
 assert np.mean(alpha>220)<.01,('signature overlap',np.mean(alpha>220))
 draw.text((x,y),TEXT,font=font,fill=(165,174,184,238))
 return out,{'text':TEXT,'font':'Microsoft YaHei (system font, rasterized only)','bbox':[x+bb[0],y+bb[1],x+bb[2],y+bb[3]],'margin':margin}

if __name__=='__main__':
 started=time.time();input_sha=hashlib.sha256(INPUT.read_bytes()).hexdigest();src=Image.open(INPUT).convert('RGB');W=8000;H=round(W*src.height/src.width);size=(W,H)
 log(f'Processing to {size}; GPU SR already completed')
 base=src.resize(size,Image.Resampling.LANCZOS);sr=Image.open(T/'Aurora_SR4.png').convert('RGB').resize(size,Image.Resampling.LANCZOS)
 fg=Image.open(T/'foreground_original.png').resize(size,Image.Resampling.LANCZOS);alpha=Image.open(T/'alpha_original.png').resize(size,Image.Resampling.LANCZOS)
 gray=src.convert('L');edge=np.abs(np.asarray(gray,dtype=np.float32)-np.asarray(gray.filter(ImageFilter.GaussianBlur(1.1)),dtype=np.float32));edge=np.clip(edge/11,0,1)
 detail=Image.fromarray(np.uint8(edge*255)).resize(size,Image.Resampling.BILINEAR);glow=Image.open(T/'glow_mask.png').resize(size,Image.Resampling.BILINEAR)
 clean=Image.new('RGBA',size)
 for top in range(0,H,160):
  box=(0,top,W,min(H,top+160));b=np.asarray(base.crop(box),dtype=np.float32);s=np.asarray(sr.crop(box),dtype=np.float32);f=np.asarray(fg.crop(box),dtype=np.float32);a=np.asarray(alpha.crop(box));e=np.asarray(detail.crop(box),dtype=np.float32)/255;g=np.asarray(glow.crop(box),dtype=np.float32)/255
  weight=(.10+.26*e)*(a>=250)*(1-g)
  delta=np.clip(s-b,-12,12)*weight[:,:,None]
  # Limited local sharpening only on already present high-frequency hull detail.
  soft=np.asarray(base.crop((0,max(0,top-6),W,min(H,top+160+6))).filter(ImageFilter.GaussianBlur(1.1)),dtype=np.float32)
  offset=top-max(0,top-6);soft=soft[offset:offset+b.shape[0]]
  sharp=np.clip(b-soft,-8,8)*(.14*e*(a>=254)*(1-g))[:,:,None]
  rgb=np.uint8(np.clip(f+delta+sharp,0,255)+.5);rgb[a==0]=0
  clean.paste(Image.fromarray(np.dstack((rgb,a))),(0,top))
 del base,sr,fg,detail,glow;gc.collect();log('Conservative fusion complete')
 m=make_manifest(clean);(T/'watermark_manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
 log(f"Embedding {len(bits)} bits over {len(m['positions'])} repeated opaque-hull blocks")
 marked=embed(clean,m);r=detect(marked,m);log('Clean watermark '+str(r));assert r['payload_match'] and r['crc_pass']
 signed,sig=signature(marked);preview=signed.resize((4500,round(4500*src.height/src.width)),Image.Resampling.LANCZOS)
 # Re-enforce the same normalized watermark after preview reduction.
 preview=embed(preview,m)
 names=['Aurora_P10_Clean_8000.png','Aurora_P10_Final_8000.png','Aurora_P10_Preview_For_PrintShop.png']
 results={}
 for name,image in zip(names,[marked,signed,preview]):
  path=O/name
  if path.exists():raise FileExistsError('Refuse to overwrite an existing delivery: '+str(path))
  image.save(path,pnginfo=info(),compress_level=6)
  check=Image.open(path);check.load();results[name]={'size':list(check.size),'mode':check.mode,'watermark':detect(check,m),'alpha_extrema':check.getchannel('A').getextrema(),'metadata':all(check.info.get(k)==v for k,v in META.items())}
  assert results[name]['watermark']['payload_match'] and results[name]['watermark']['crc_pass'] and results[name]['metadata'];log('Saved '+name)
 # Robustness checks are actual transformations, not metadata reads.
 checks={}
 for name,im in [('scale50',signed.resize((4000,round(H*.5)),Image.Resampling.LANCZOS)),('sharpen',signed.filter(ImageFilter.UnsharpMask(radius=1.2,percent=65,threshold=3)))]:checks[name]=detect(im,m)
 flat=Image.new('RGB',preview.size,(238,238,238));flat.paste(preview,mask=preview.getchannel('A'));buff=io.BytesIO();flat.save(buff,format='JPEG',quality=88,subsampling=0);buff.seek(0);jpeg=Image.open(buff);checks['JPEG88']=detect(jpeg,m)
 negative=detect(clean,m);checks['unwatermarked_control']=negative
 # Comparison: both sides use identical crop, display scale and reconstructed alpha.
 original=Image.open(T/'foreground_original.png').convert('RGBA');original.putalpha(Image.open(T/'alpha_original.png'));original=original.resize(size,Image.Resampling.LANCZOS);enh=marked
 crops=[('船头装甲',(45,565,450,820)),('舷窗与面板',(700,450,1070,590)),('Aurora 标志',(465,596,615,725)),('Alterra 标志',(907,199,1017,282)),('蓝色圆环',(615,655,765,835)),('引擎与柔和辉光',(1150,263,1360,380)),('透明轮廓与底部细节',(180,812,490,953))]
 panel=Image.new('RGB',(1600,7*360+70),(29,34,42));d=ImageDraw.Draw(panel);font=ImageFont.truetype('msyh.ttc',24);d.text((25,18),'原图同尺度局部（左） / 保守增强（右） · 灰白棋盘仅用于展示透明度',font=font,fill=(225,230,238))
 for row,(label,box) in enumerate(crops):
  y=70+row*360;d.text((20,y),label,font=font,fill=(220,225,235))
  for col,img in enumerate([original,enh]):
   scaled=tuple(round(v*W/src.width) for v in box);piece=img.crop(scaled);piece.thumbnail((755,305),Image.Resampling.LANCZOS)
   # Enlarge small crops equally on both sides for inspection.
   ratio=min(755/piece.width,305/piece.height);piece=piece.resize((round(piece.width*ratio),round(piece.height*ratio)),Image.Resampling.NEAREST if ratio>3 else Image.Resampling.LANCZOS)
   grid=np.indices((piece.height,piece.width)).sum(0)//18 # overwritten below with square checkerboard
   gy,gx=np.indices((piece.height,piece.width));v=np.where(((gx//18+gy//18)%2)==0,225,195).astype('uint8');tile=Image.fromarray(np.repeat(v[:,:,None],3,2),'RGB').convert('RGBA');tile.alpha_composite(piece);panel.paste(tile.convert('RGB'),(20+col*800,y+40))
 panel.save(O/'Aurora_P10_Comparison.jpg',quality=94,subsampling=0)
 assert hashlib.sha256(INPUT.read_bytes()).hexdigest()==input_sha
 report={'input_sha256':input_sha,'input_mode':'RGB (no alpha); matte reconstructed from baked background','method':'Real-ESRGAN ncnn Vulkan realesrgan-x4plus / Intel Arc B390 GPU / tiled128 / 1:1:1 threads; capped10-36% detail fusion; original plume pixels/alpha preserved from reconstructed matte','signature':sig,'metadata':META,'files':results,'robustness':checks,'seconds':time.time()-started,'date':'2026-10-28'}
 (T/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');log(json.dumps(checks,ensure_ascii=False))
 # Small composited QA assets, not extra user-facing deliverables.
 thumb=signed.copy();thumb.thumbnail((1800,1200));canvas=Image.new('RGBA',thumb.size,(232,232,232,255));canvas.alpha_composite(thumb);canvas.convert('RGB').save(T/'final_QA_light.jpg',quality=95)
 log('COMPLETE')
