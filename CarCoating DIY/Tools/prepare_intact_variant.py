import sys,pathlib,json,shutil,math
base=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(base/'Tools/python'))
from PIL import Image
src=base/'02_Models/starship_souvenir';dst=base/'02_Models/Aurora_Intact_Atlas2048';dst.mkdir(exist_ok=True)
materials=json.loads((src/'materials.json').read_text());obj=(src/'starship_souvenir.obj').read_text().replace('starship_souvenir.mtl','Aurora_Intact_Atlas2048.mtl');(dst/'Aurora_Intact_Atlas2048.obj').write_text(obj)
atlasdir=next((base/'01_SourceAssets/Verified_Exports').glob('duplicateassetssorted_assets_bundle1744*'))
for key,patt in [('_MainTex','starship_crashed__*.png'),('_BumpMap','starship_crashed_normal__*.png'),('_SpecTex','starship_crashed_spec__*.png')]:
 p=next(atlasdir.rglob(patt));shutil.copy2(p,dst/p.name);im=Image.open(p);materials[0]['textures'][key].update(file=p.name,width=im.width,height=im.height)
for p in src.glob('*.png'):
 if not (dst/p.name).exists():shutil.copy2(p,dst/p.name)
(dst/'materials.json').write_text(json.dumps(materials,ensure_ascii=False,indent=2),encoding='utf8')
(dst/'source.json').write_text(json.dumps({'geometry':'Game original starship_souvenir; no geometric repair','texture_change':'Original starship_crashed 2048 atlas assigned to intact souvenir UVs; derivative candidate, not recovered full-scale intact model','original_souvenir_texture':'512x512','new_atlas':'2048x2048','emission':'Original souvenir emission 256x256'},indent=2))
for folder in [base/'02_Models'/n for n in ['starship_crashed','starship_souvenir','starship_exploded_exterior','Aurora_Intact_Atlas2048']]:
 mats=json.loads((folder/'materials.json').read_text())
 for mat in mats:
  te=mat['textures'].get('_BumpMap')
  if not te:continue
  p=folder/te['file'];im=Image.open(p).convert('RGBA');dest=folder/(p.stem+'_OpenGL.png')
  if not dest.exists():
   pixels=[]
   for r,g,b,a in im.getdata():
    x=a/127.5-1;y=g/127.5-1;z=math.sqrt(max(0,1-x*x-y*y));pixels.append((a,g,round((z+1)*127.5),255))
   decoded=Image.new('RGBA',im.size);decoded.putdata(pixels);decoded.save(dest)
  te['decoded_file']=dest.name
 (folder/'materials_decoded.json').write_text(json.dumps(mats,ensure_ascii=False,indent=2),encoding='utf8')
