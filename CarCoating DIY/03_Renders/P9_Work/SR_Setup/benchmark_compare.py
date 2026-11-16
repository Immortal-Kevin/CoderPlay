import pathlib,sys
base=pathlib.Path(str(__import__('pathlib').Path(__file__).resolve().parents[3]));sys.path.insert(0,str(base/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
root=base/'03_Renders/P9_Work/SR_Setup';original=Image.open(root/'TestCrop256.png').convert('RGB');baseline=original.resize((1024,1024),Image.Resampling.LANCZOS);enhanced=Image.open(root/'TestCrop256_RealESRGAN_x4.png').convert('RGB')
out=Image.new('RGB',(2048,1070),(25,30,40));out.paste(baseline,(0,46));out.paste(enhanced,(1024,46));d=ImageDraw.Draw(out);font=ImageFont.truetype('arial.ttf',24);d.text((20,10),'Source 256px / Lanczos x4',font=font,fill='white');d.text((1044,10),'Real-ESRGAN x4plus / Intel Arc Vulkan',font=font,fill='white');out.save(root/'Benchmark_Lanczos_RealESRGAN.jpg',quality=95)
