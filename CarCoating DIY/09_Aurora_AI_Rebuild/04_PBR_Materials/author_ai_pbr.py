import pathlib,sys,json,hashlib
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent/'Tools/python'))
import numpy as np
from PIL import Image,ImageFilter,ImageOps,ImageDraw,ImageFont
specs={'WhiteArmor':((232,236,240),.27,.16),'Silver':((170,182,196),.23,.9),'DarkMetal':((42,57,72),.31,.68),'ChampagneGold':((192,145,67),.21,.82)}
records=[];proof=Image.new('RGB',(1536,len(specs)*550),(25,32,42));draw=ImageDraw.Draw(proof);font=ImageFont.truetype('msyh.ttc',24)
for i,(name,(base,rough,metal)) in enumerate(specs.items()):
 source=root/'03_AI_Textures'/f'AI_Raw_{name}_384.png'
 assert source.exists(),'Generative output missing '+name
 raw=Image.open(source).convert('RGB');W,H=raw.size
 tile=Image.new('RGB',(W*2,H*2));tile.paste(raw,(0,0));tile.paste(ImageOps.mirror(raw),(W,0));tile.paste(ImageOps.flip(raw),(0,H));tile.paste(ImageOps.flip(ImageOps.mirror(raw)),(W,H));tile=tile.resize((4096,4096),Image.Resampling.LANCZOS)
 lum=tile.convert('L');low=lum.filter(ImageFilter.GaussianBlur(30));l=np.asarray(lum,dtype='float32')/255;lo=np.asarray(low,dtype='float32')/255;hi=l-lo;wide=l-float(np.mean(l))
 # Remove baked studio gradients, retain actual AI-created panel and grain structure.
 variation=np.clip(hi*.65+wide*.08,-.16,.12);color=np.array(base,dtype='float32')[None,None,:]*(1+variation[:,:,None]);color=np.clip(color,0,255).astype('uint8');Image.fromarray(color).save(root/'04_PBR_Materials'/f'{name}_BaseColor_4096.png')
 rr=np.clip(rough+hi*.65+wide*.1,.08,.7);Image.fromarray((rr*255).astype('uint8')).save(root/'04_PBR_Materials'/f'{name}_Roughness_4096.png')
 mm=np.clip(metal+hi*.12,0,.97);Image.fromarray((mm*255).astype('uint8')).save(root/'04_PBR_Materials'/f'{name}_Metallic_4096.png')
 height=np.clip(.5+hi*1.8,0,1);Image.fromarray((height*255).astype('uint8')).save(root/'04_PBR_Materials'/f'{name}_Height_4096.png');dy,dx=np.gradient(height);n=np.dstack((-dx*18,dy*18,np.ones_like(dx)));n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-5);Image.fromarray(np.clip((n+1)*127.5,0,255).astype('uint8')).save(root/'04_PBR_Materials'/f'{name}_Normal_4096.png')
 Image.new('RGB',(4096,4096),(0,0,0)).save(root/'04_PBR_Materials'/f'{name}_Emission_4096.png')
 inp=Image.open(root/'03_AI_Textures'/f'InputGuide_{name}_512.png').convert('RGB');ai=raw.resize((512,512),Image.Resampling.LANCZOS);mat=Image.fromarray(color).resize((512,512),Image.Resampling.LANCZOS)
 for j,im in enumerate([inp,ai,mat]):proof.paste(im,(j*512,i*550+38))
 draw.text((12,i*550+5),name+' / Input -> Local Generative AI -> Adopted PBR',font=font,fill='white')
 records.append({'group':name,'generative_source':str(source),'generative_source_size':[W,H],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'pbr_working_size':[4096,4096],'projection':'object-space triplanar shared across views','metallic_mean':metal,'roughness_mean':rough,'process':'Mirror-seamless AI tile, low-frequency lighting removal, authored PBR channel extraction. Not native 4K model inference.'})
 print('PBR GROUP COMPLETE',name,flush=True)
proof.save(root/'03_AI_Textures/AI_Input_Generated_Adopted_Comparison.jpg',quality=95);(root/'09_Report/AI_PBR_Provenance.json').write_text(json.dumps(records,indent=2));print('AI PBR AUTHORING COMPLETE',flush=True)
