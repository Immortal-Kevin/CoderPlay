import pathlib,sys,json
base=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(base/'Tools/python'))
from PIL import Image,ImageDraw
paths=[]
for pat in ['starship_crashed__*.obj','starship_souvenir__*.obj','starship_exploded_exterior__*.obj']:
 for p in (base/'01_SourceAssets/Verified_Exports').rglob(pat):
  v=[list(map(float,l.split()[1:])) for l in p.read_text().splitlines() if l.startswith('v ')]
  print(p, 'verts',len(v),'bounds',[(min(x[i] for x in v),max(x[i] for x in v)) for i in range(3)])
for pat in ['starship_crashed__*.png','starship_souvenir__*.png','poster_aurora*.png']:
 paths.extend((base/'01_SourceAssets/Verified_Exports').rglob(pat))
sheet=Image.new('RGB',(1000,350*len(paths)),(45,45,45));d=ImageDraw.Draw(sheet)
for i,p in enumerate(paths):
 im=Image.open(p);print(p,im.size,im.mode);im.thumbnail((980,310));sheet.paste(im,(10,i*350+30));d.text((10,i*350+5),p.name,fill='white')
sheet.save(base/'05_Preview/Source_Texture_Overview.jpg')
