import os,pathlib,json,time,hashlib,sys,traceback
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
import torch
from PIL import Image
from diffusers import StableDiffusionImg2ImgPipeline,DPMSolverMultistepScheduler
root=pathlib.Path(__file__).resolve().parents[1];torch.set_num_threads(4);torch.set_num_interop_threads(2)
device='xpu' if torch.xpu.is_available() else 'cpu';dtype=torch.float16 if device=='xpu' else torch.float32
model=root/'Tools/Models/TinySD';t=time.time();pipe=StableDiffusionImg2ImgPipeline.from_pretrained(str(model),torch_dtype=dtype,local_files_only=True,safety_checker=None,requires_safety_checker=False,low_cpu_mem_usage=False);pipe=pipe.to(device);pipe.enable_attention_slicing('max');pipe.enable_vae_slicing();pipe.scheduler=DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
print('PIPELINE READY',device,'load_seconds',time.time()-t,flush=True)
specs=[('WhiteArmor','flat seamless material texture swatch, aerospace white painted titanium armor, precision inset panel seams, clean satin white ceramic-metal coating, very fine industrial surface grain, orthographic straight-on flat even illumination, subtle milled edges, factory new high end science fiction prop, no words, no letters, no logo, no dirt'),('Silver','flat seamless material texture swatch, precision aerospace brushed silver aluminum and titanium, fine parallel machining marks, very subtle panel edges, factory clean satin silver metal, orthographic straight-on flat even illumination, no words, no letters, no logo'),('DarkMetal','flat seamless texture swatch, precision graphite titanium machinery, fine dark gunmetal machining, subtle industrial precision panels, clean factory fresh aerospace finish, flat even illumination, no letters no words no labels no logos'),('ChampagneGold','flat seamless texture swatch, champagne gold anodized brushed aerospace aluminum, refined satin golden metal, microscopic fine machining, clean luxury industrial material, flat even illumination, no letters no words no labels no logos')]
records=[]
for i,(name,prompt) in enumerate(specs):
 inp=root/'03_AI_Textures'/f'InputGuide_{name}_512.png';image=Image.open(inp).convert('RGB').resize((384,384),Image.Resampling.LANCZOS)
 params={'model':'segmind/tiny-sd','revision':json.loads((root/'09_Report/TinySD_Model_Metadata.json').read_text())['sha'],'pipeline':'StableDiffusionImg2ImgPipeline','device':device,'torch':torch.__version__,'dtype':str(dtype),'width':384,'height':384,'num_inference_steps':20,'strength':.58,'guidance_scale':6.0,'seed':71001+i,'prompt':prompt,'negative_prompt':'text, letters, numbers, logo, watermark, rust, dirty, scratches, spaceship, vehicle, perspective, dramatic lighting, black shadows, clutter, screws everywhere','input':str(inp)}
 print('GENERATING',name,flush=True);start=time.time()
 try:
  result=pipe(prompt=prompt,negative_prompt=params['negative_prompt'],image=image,num_inference_steps=20,strength=.58,guidance_scale=6.0,generator=torch.Generator(device='cpu').manual_seed(params['seed'])).images[0]
  path=root/'03_AI_Textures'/f'AI_Raw_{name}_384.png';result.save(path);params.update(output=str(path),seconds=time.time()-start,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),success=True);print('GENERATED',name,params['seconds'],flush=True)
 except Exception as e:
  params.update(success=False,error=str(e));traceback.print_exc()
 records.append(params);(root/'03_AI_Textures/Inference_Parameters_and_Results.json').write_text(json.dumps(records,indent=2));
 if device=='xpu':torch.xpu.empty_cache()
print('LOCAL GENERATIVE AI RUN COMPLETE',flush=True)
