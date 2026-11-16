import sys,pathlib,json
p=pathlib.Path(str(__import__('pathlib').Path(__file__).resolve().parents[3]));sys.path.insert(0,str(p/'Tools/python'))
from PIL import Image
im=Image.open(p/'03_Renders/Alterra_full.png');print(im.size,im.mode)
box=(430,510,686,766)
crop=im.crop(box).convert('RGBA');bg=Image.new('RGBA',crop.size,(40,45,50,255));Image.alpha_composite(bg,crop).convert('RGB').save(p/'03_Renders/P9_Work/SR_Setup/TestCrop256.png')
(p/'03_Renders/P9_Work/SR_Setup/TestCrop_Info.json').write_text(json.dumps({'input':str(p/'03_Renders/Alterra_full.png'),'size':im.size,'mode':im.mode,'crop':box},indent=2))
