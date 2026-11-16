import os,pathlib,json,time,hashlib
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
import torch
from PIL import Image
from diffusers import StableDiffusionImg2ImgPipeline,DPMSolverMultistepScheduler
root=pathlib.Path(__file__).resolve().parents[1];torch.set_num_threads(4);torch.set_num_interop_threads(2)
device='xpu' if torch.xpu.is_available() else 'cpu';dtype=torch.float16 if device=='xpu' else torch.float32
pipe=StableDiffusionImg2ImgPipeline.from_pretrained(str(root.parent/'09_Aurora_AI_Rebuild/Tools/Models/TinySD'),torch_dtype=dtype,local_files_only=True,safety_checker=None,requires_safety_checker=False,low_cpu_mem_usage=False).to(device)
pipe.enable_attention_slicing('max');pipe.enable_vae_slicing();pipe.scheduler=DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
params={'model':'segmind/tiny-sd','revision':'cad0bd7495fa6c4bcca01b19a723dc91627fe84f','device':device,'torch':torch.__version__,'threads':4,'size':[384,384],'strength':.24,'steps':24,'guidance_scale':4.5,'seed':81001,'prompt':'close up scorched aerospace metal surface, original panel layout preserved, dark heat oxidation, subtle charred industrial metal grain, flat material swatch, no text','negative_prompt':'spaceship, vehicle, new panels, raised tiles, letters, text, robot, character, flames, scenery, logo'}
t=time.time();result=pipe(prompt=params['prompt'],negative_prompt=params['negative_prompt'],image=Image.open(root/'04_AI/Scorch_Input_512.png').convert('RGB').resize((384,384)),strength=params['strength'],num_inference_steps=params['steps'],guidance_scale=params['guidance_scale'],generator=torch.Generator(device='cpu').manual_seed(params['seed'])).images[0]
p=root/'04_AI/Scorch_AI_Raw_384.png';result.save(p);params.update(seconds=time.time()-t,output=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='Only masked rear burn roughness/grain. Not ship colour or geometry.')
(root/'04_AI/Inference_Record.json').write_text(json.dumps(params,indent=2));print(json.dumps(params),flush=True)
