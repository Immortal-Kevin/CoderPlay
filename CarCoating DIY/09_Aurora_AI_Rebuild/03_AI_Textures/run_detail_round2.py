import os,pathlib,json,time,hashlib
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['OMP_NUM_THREADS']='4'
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
root=pathlib.Path(__file__).resolve().parents[1];torch.set_num_threads(4);torch.set_num_interop_threads(2)
p=StableDiffusionImg2ImgPipeline.from_pretrained(str(root/'Tools/Models/TinySD'),torch_dtype=torch.float32,local_files_only=True,safety_checker=None,requires_safety_checker=False,low_cpu_mem_usage=False).to('cpu');p.enable_attention_slicing('max');p.enable_vae_slicing()
records=[]
for i,name in enumerate(['WhiteArmor','Silver']):
 prompt=('white painted titanium spacecraft armor' if name=='WhiteArmor' else 'brushed silver titanium precision machinery')+', macro material texture, detailed science fiction hard surface panels, small raised inspection covers, milled edges, fine engraved seams, exquisite industrial engineering, clean factory new finish, flat orthographic even light, no text, no logos'
 inp=root/'03_AI_Textures'/f'InputGuide_{name}_512.png';t=time.time();print('DETAIL ROUND2',name,flush=True)
 im=p(prompt=prompt,negative_prompt='letters, words, labels, numbers, logo, watermark, dirt, rust, scratches, perspective, spaceship, vehicle, outer space, hands',image=Image.open(inp).convert('RGB'),num_inference_steps=24,strength=.88,guidance_scale=7.0,generator=torch.Generator('cpu').manual_seed(72010+i)).images[0]
 out=root/'03_AI_Textures'/f'AI_Detail_{name}_512.png';im.save(out);records.append({'model':'segmind/tiny-sd','device':'cpu','pipeline':'StableDiffusionImg2ImgPipeline','seed':72010+i,'num_inference_steps':24,'strength':.88,'guidance_scale':7,'input':str(inp),'output':str(out),'prompt':prompt,'size':list(im.size),'seconds':time.time()-t,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'success':True});(root/'03_AI_Textures/Detail_Round2_Parameters.json').write_text(json.dumps(records,indent=2));print('DETAIL COMPLETE',name,records[-1]['seconds'],flush=True)
