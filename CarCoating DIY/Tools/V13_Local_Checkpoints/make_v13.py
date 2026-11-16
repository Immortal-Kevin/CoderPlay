import os,sys,pathlib,json,hashlib,zlib,io,time
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
import numpy as np
from PIL import Image,ImageDraw,ImageFont,PngImagePlugin,ImageFilter
R=pathlib.Path(str(__import__('pathlib').Path(__file__).resolve().parents[2]));O=R/'03_Renders';T=pathlib.Path(__file__).parent
sys.path.insert(0,str(O));from p9_make_baseline import resize_rgba_float
SOURCE=R/'Tools/P10_Final_Delivery/matte_check.png'
TEXT='cr：Subnautica - Aurora / UnknownWorld / Codex / Kevin L 第13版AI重制'
SPECS=[{'name':'upper','center':[1203,332],'rx':27,'ry':36,'box':[1174,235,1390,395],'extent':88,'radius':20,'curve':[(235,1170),(270,1150),(280,1162),(290,1186),(300,1208),(310,1220),(320,1226),(330,1229),(340,1228),(350,1224),(356,1217),(360,1208),(395,1170)]},
 {'name':'middle','center':[1538,440],'rx':30,'ry':67,'box':[1490,320,1632,540],'extent':120,'radius':27,'curve':[(320,1485),(350,1485),(365,1505),(375,1527),(385,1542),(395,1554),(405,1561),(420,1566),(435,1568),(450,1566),(465,1559),(480,1545),(495,1525),(510,1498),(525,1485),(540,1485)]},
 {'name':'lower','center':[1534,665],'rx':29,'ry':62,'box':[1480,550,1632,790],'extent':120,'radius':27,'curve':[(550,1475),(585,1475),(600,1500),(610,1521),(620,1536),(630,1547),(640,1555),(650,1560),(665,1563),(680,1561),(695,1552),(710,1537),(725,1515),(740,1489),(755,1475),(790,1475)]}]
direction=np.array([1.,-.18]);direction/=np.linalg.norm(direction);perp=np.array([-direction[1],direction[0]])
def checkpoint(im,name):
 if name.startswith(('After_','Thruster_')):name=name.replace('.png','_v02.png')
 p=T/name
 if not p.exists():im.save(p)
 return p
def make_base():
 p=T/'Base_Complete_Unwatermarked_8000.png'
 if p.exists():return Image.open(p).convert('RGBA')
 src=Image.open(SOURCE).convert('RGBA');assert src.size==(1632,964)
 base=resize_rgba_float(src,(8000,round(8000*src.height/src.width)));base.save(p);return base
def replace_plumes(base):
 out=base.copy();sx=base.width/1632;sy=base.height/964;roi=np.zeros((base.height,base.width),dtype=bool);engine_lock=np.zeros_like(roi);summaries=[]
 for spec in SPECS:
  box=tuple(round(v*(sx if i%2==0 else sy)) for i,v in enumerate(spec['box']));old=np.array(base.crop(box));H,W=old.shape[:2];yy,xx=np.mgrid[:H,:W];x=(xx+box[0]+.5)/sx;y=(yy+box[1]+.5)/sy;cx,cy=spec['center'];rx=spec['rx'];ry=spec['ry']
  # Explicit curved nozzle exclusion. No rectangular replacement over an engine.
  curve=np.interp(y,[p[0] for p in spec['curve']],[p[1] for p in spec['curve']])
  mask=np.clip((x-curve-1.7)/1.1,0,1);mask=mask*mask*(3-2*mask)
  # Independent colour/alpha guard retains opaque metal even at a traced boundary.
  original_rgb=old[:,:,:3].astype('int16');structural=(old[:,:,3]>=254)&(((original_rgb.max(2)-original_rgb.min(2))<45)|(original_rgb[:,:,2]<210));mask[structural]=0
  if spec['name']=='upper':
   # The intact foreground deck crosses under the far exhaust.
   mask[y>=352+.16*(x-1225)]=0
  tip=np.array([cx+rx+1.,cy]);dx=x-tip[0];dy=y-tip[1];u=dx*direction[0]+dy*direction[1];v=dx*perp[0]+dy*perp[1]
  available=(1632-4-tip[0])/direction[0];length=min(spec['extent'],available);r=spec['radius'];root_gate=1/(1+np.exp(-np.clip((u+2)/1.7,-30,30)))
  end=np.clip((length-u)/max(15,length*.35),0,1);end=end*end*(3-2*end)
  broad=np.exp(-((np.maximum(u,0)/(length*.86))**4))*end*root_gate
  radius=r*(1+.12*np.clip(u/length,0,1))
  layers=[((.012,.19,1.),.28*broad*np.exp(-(v/(radius*1.50))**2)),
   ((.025,.43,1.),.83*broad*np.exp(-(v/radius)**2)),
   ((.10,.78,1.),.75*np.exp(-((u-5)/11)**2-(v/(r*.70))**2)*root_gate),
   ((.96,.995,1.),.99*np.exp(-((u-3.0)/(4.1 if spec['name']=='upper' else 5.0))**2-(v/(8.5 if spec['name']=='upper' else 11.5))**2))]
  a=np.zeros((H,W),dtype='float32');p=np.zeros((H,W,3),dtype='float32')
  for color,aa in layers:
   aa=np.clip(aa,0,1);p=np.array(color)[None,None,:]*aa[:,:,None]+p*(1-aa[:,:,None]);a=aa+a*(1-aa)
  # A vertical final 4px transparent margin guarantees no cropped exhaust.
  margin=np.clip((1632-3-x)/3,0,1);margin=margin*margin*(3-2*margin);a*=margin;p*=margin[:,:,None];a[a<1/1024]=0;p[a==0]=0
  straight=np.divide(p,a[:,:,None],out=np.zeros_like(p),where=a[:,:,None]>1e-8);layer=np.uint8(np.clip(np.dstack((straight,a))*255+.5,0,255));layer[layer[:,:,3]==0,:3]=0
  # Blend in premultiplied space; protected source pixels remain byte-identical.
  original=old.astype('float32')/255;oa=original[:,:,3];op=original[:,:,:3]*oa[:,:,None];na=a*mask+oa*(1-mask);nprem=p*mask[:,:,None]+op*(1-mask[:,:,None]);rgb=np.divide(nprem,na[:,:,None],out=np.zeros_like(nprem),where=na[:,:,None]>1e-8)
  merged=np.uint8(np.clip(np.dstack((rgb,na))*255+.5,0,255));merged[merged[:,:,3]==0,:3]=0;merged[mask==0]=old[mask==0]
  assert np.array_equal(merged[mask==0],old[mask==0])
  out.paste(Image.fromarray(merged,'RGBA'),(box[0],box[1]));roi[box[1]:box[3],box[0]:box[2]]|=mask>0
  guard=((x<=curve+1.7)&(y>cy-ry-8)&(y<cy+ry+8))|structural;engine_lock[box[1]:box[3],box[0]:box[2]]|=guard
  assert np.array_equal(old[guard],merged[guard])
  checkpoint(Image.fromarray(layer,'RGBA'),f'Thruster_{spec["name"]}_{base.width}_RGBA.png')
  visible=(layer[:,:,3]>40)&(mask>.9);white=(layer[:,:,0]>180)&(layer[:,:,1]>220)&(layer[:,:,2]>225)&(layer[:,:,3]>128)&(mask>.9)&(u<12)
  assert visible.sum()>100 and white.sum()>3
  summaries.append({'name':spec['name'],'tip_source':tip.tolist(),'visible_extent_source_px':length,'radius_source_px':r,'outside_alpha_at_right':int(merged[:,-1,3].max()) if box[2]==base.width else 0,'engine_guard_pixels':int(guard.sum()),'engine_guard_changed':0,'visible_glow_pixels_at_alpha_gt40':int(visible.sum()),'attached_cold_white_core_pixels':int(white.sum()),'glow_visible_not_a_point':True})
 b=np.asarray(base);a=np.asarray(out);changed=np.any(a!=b,axis=2)
 assert not np.any(changed&~roi);assert np.array_equal(a[engine_lock],b[engine_lock])
 assert not np.any((b[:,:,3]>=254)&(a[:,:,3]<254)&~roi)
 return out,roi,engine_lock,{'non_roi_changed':int((changed&~roi).sum()),'engine_guard_changed':0,'plumes':summaries}
def signature(image):
 out=image.copy();font=ImageFont.truetype('msyh.ttc',max(12,round(image.width*.0065)));d=ImageDraw.Draw(out);bb=d.textbbox((0,0),TEXT,font=font);m=round(image.width*.014);x=image.width-m-(bb[2]-bb[0])-bb[0];y=image.height-m-(bb[3]-bb[1])-bb[1];bounds=(x+bb[0],y+bb[1],x+bb[2],y+bb[3]);aa=np.asarray(image.getchannel('A').crop(bounds));assert aa.max()==0,'Signature must remain fully outside hull and FX'
 d.text((x,y),TEXT,font=font,fill=(165,174,184,238));return out,bounds
def embed_in_tail(im,roi,seed):
 arr=np.array(im);rgb=arr[:,:,:3].astype('int16');eligible=np.flatnonzero((roi&(arr[:,:,3]>48)&(arr[:,:,3]<235)&(rgb[:,:,2]-rgb[:,:,0]>65)).ravel());payload=b'AV13WM1|Kevin L|AuroraV13|2026-10-28';packet=payload+zlib.crc32(payload).to_bytes(4,'big');bits=np.unpackbits(np.frombuffer(packet,dtype='uint8'));count=len(bits)*7;assert len(eligible)>count
 rng=np.random.default_rng(seed);idx=rng.choice(eligible,count,replace=False);flat=arr.reshape(-1,4);flat[idx,2]=(flat[idx,2]&254)|np.tile(bits,7)
 m={'algorithm':'keyed repeated B-channel LSB in tail-only carrier pixels; CRC32; preview re-embedded independently','payload':payload.decode(),'crc32':zlib.crc32(payload),'bit_length':len(bits),'repetitions':7,'positions':idx.tolist(),'image_size':im.size,'seed':seed}
 return Image.fromarray(arr,'RGBA'),m
def detect(im,m):
 arr=np.asarray(im).reshape(-1,4);bits=(arr[np.array(m['positions']),2]&1).reshape(m['repetitions'],m['bit_length']);v=(bits.sum(0)>m['repetitions']/2).astype('uint8');packet=np.packbits(v).tobytes();p=packet[:-4];return {'payload_match':p.decode(errors='replace')==m['payload'],'crc_pass':zlib.crc32(p)==int.from_bytes(packet[-4:],'big')}
def audit(before,after,roi,guard,signature_box=None):
 b=np.asarray(before);a=np.asarray(after);allowed=roi.copy()
 if signature_box:
  x0,y0,x1,y1=signature_box;allowed[y0:y1,x0:x1]=True
 changed=np.any(a!=b,axis=2);outside=int((changed&~allowed).sum());assert outside==0;assert np.array_equal(b[guard],a[guard]);assert not np.any((b[:,:,3]>250)&(a[:,:,3]<250)&~allowed)
 return {'non_tail_ship_pixels_identical':True,'outside_tail_and_required_signature_changed':outside,'engine_shell_pixels_identical':True,'new_opaque_hull_holes':0}
def preview(im):
 tiny=im.copy();tiny.thumbnail((2000,1400));source=Image.open(SOURCE);sx=tiny.width/source.width;sy=tiny.height/source.height;sheet=Image.new('RGB',(1800,960),(22,27,34));d=ImageDraw.Draw(sheet)
 for row,s in enumerate(SPECS):
  cx,cy=s['center'];box=(round((cx-55)*sx),round((cy-85)*sy),min(tiny.width,round((cx+180)*sx)),round((cy+85)*sy));crop=tiny.crop(box)
  for col,(label,color) in enumerate([('BLACK',(0,0,0)),('WHITE',(245,245,245)),('ALPHA',None)]):
   if color:bg=Image.new('RGBA',crop.size,(*color,255))
   else:
    yy,xx=np.indices((crop.height,crop.width));v=np.where(((xx//12+yy//12)%2)==0,205,245).astype('uint8');bg=Image.fromarray(np.dstack((v,v,v,np.full_like(v,255))),'RGBA')
   bg.alpha_composite(crop);bg.thumbnail((590,285));sheet.paste(bg.convert('RGB'),(col*600+5,row*320+25));d.text((col*600+8,row*320+4),s['name']+' '+label,fill='white')
 sheet.save(T/'Three_Thrusters_Three_Backgrounds.jpg',quality=95)
 full=Image.new('RGBA',tiny.size,(16,22,30,255));full.alpha_composite(tiny);full.convert('RGB').save(T/'Final_2000_Dark_Check.jpg',quality=96)
def main():
 names=['AuroraV13_Clean_8000.png','AuroraV13_Watermarked_8000.png','AuroraV13_Watermarked_2000.png']
 assert all(not (O/n).exists() for n in names),'Refusing existing V13 outputs'
 prior_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in O.glob('AuroraV12*.png')}
 source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest();base=make_base();base2000=resize_rgba_float(base,(2000,round(2000*964/1632)));checkpoint(base2000,'Base_Complete_Unwatermarked_2000.png')
 clean,roi,guard,details=replace_plumes(base);low,roi2,guard2,details2=replace_plumes(base2000);checkpoint(clean,'After_Tail_Composite_8000.png');checkpoint(low,'After_Tail_Composite_2000.png');Image.fromarray(roi.astype('uint8')*255).save(T/'Tail_Only_ROI_8000.png')
 signed,bounds=signature(clean);marked,m=embed_in_tail(signed,roi,13008000);signed2,bounds2=signature(low);marked2,m2=embed_in_tail(signed2,roi2,13002000)
 checks=[audit(base,clean,roi,guard),audit(base,marked,roi,guard,bounds),audit(base2000,marked2,roi2,guard2,bounds2)]
 assert detect(marked,m)['crc_pass'] and detect(marked2,m2)['crc_pass'];assert not detect(clean,m)['crc_pass']
 preview(marked2)
 validation={'selected_base':str(SOURCE),'rejected_version':'AuroraV12_Clean_8000.png: visible engine cut-outs','source_sha256':source_hash,'source_size':Image.open(SOURCE).size,'output_checks':checks,'details_8000':details,'details_2000':details2,'watermark_8000':detect(marked,m),'watermark_2000':detect(marked2,m2),'clean_has_known_watermark':detect(clean,m)['crc_pass'],'signature':TEXT,'signature_boxes':[bounds,bounds2],'signature_is_explicit_output_exception':True,'no_full_image_segmentation_or_AI_or_blender':True}
 (T/'Validation_Before_Save.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
 if '--save' not in sys.argv:print('CHECKPOINTS READY, INSPECT BEFORE SAVE');return
 for n,im,wm in zip(names,[clean,marked,marked2],[None,m,m2]):
  meta=PngImagePlugin.PngInfo()
  if wm:
   meta.add_itxt('Watermark-ID','KL-AURORA-V13');meta.add_itxt('Visible-Signature',TEXT);meta.add_itxt('Pixel-Watermark-Parameters',json.dumps(wm,separators=(',',':')))
  im.save(O/n,pnginfo=meta,compress_level=6)
  test=Image.open(O/n);test.load();assert test.mode=='RGBA';assert test.width==(2000 if '2000' in n else 8000)
  if wm:assert detect(test,wm)['crc_pass']
  else:assert not test.info
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
 assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h for p,h in prior_hashes.items())
 validation['prior_V12_files_unchanged']=True
 validation['saved']=[str(O/n) for n in names];validation['png_reopen_pass']=True;(T/'Validation_Final.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'saved':validation['saved'],'pixel_lock':'PASS','engines':'PASS','watermark':'PASS'},indent=2))
if __name__=='__main__':main()
