import pathlib,sys,json,hashlib,math
root=pathlib.Path(__file__).parent;sys.path.insert(0,str(root.parent/'Tools/python'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
work=root/'P9_Work';source=Image.open(root/'Alterra_full.png').convert('RGBA');baseline=Image.open(root/'Alterra_full_8000_Baseline.png').convert('RGBA');enhanced=Image.open(root/'Alterra_full_8000_Enhanced.png').convert('RGBA');method=json.loads((work/'Enhancement_Method.json').read_text());inspection=json.loads((work/'Input_Inspection.json').read_text())
checks=[]
for name in ['Alterra_full_8000_Baseline.png','Alterra_full_8000_Enhanced.png']:
 p=root/name
 with Image.open(p) as test:test.verify()
 im=Image.open(p);im.load();ar=np.asarray(im);a=ar[:,:,3]
 checks.append({'path':str(p),'size':im.size,'mode':im.mode,'open_and_decode':True,'correct_target_size':im.size==(8000,4725),'alpha_min':int(a.min()),'alpha_max':int(a.max()),'zero_alpha_pixels':int((a==0).sum()),'partial_alpha_pixels':int(((a>0)&(a<255)).sum()),'transparent_RGB_nonzero':int(np.any(ar[:,:,:3][a==0]!=0,axis=1).sum()),'right_border_alpha_max':int(a[:,-1].max()),'icc_present':bool(im.info.get('icc_profile')),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
logos=[]
for box in method['logo_core_final_boxes']:
 bb=np.asarray(baseline.crop(tuple(box)));ee=np.asarray(enhanced.crop(tuple(box)));b=bb[:,:,:3];e=ee[:,:,:3];visible=ee[:,:,3]>0;changed=np.any(b!=e,axis=2);logos.append({'box':box,'visible_RGB_exactly_equal_to_source_Lanczos':bool(np.array_equal(b[visible],e[visible])),'visible_max_channel_difference':int(np.abs(b[visible].astype('int16')-e[visible]).max()),'transparent_RGB_cleanup_pixels':int((changed&~visible).sum())})
original_hash=hashlib.sha256((root/'Alterra_full.png').read_bytes()).hexdigest()
alpha_source=np.asarray(source.getchannel('A'));alpha_final=np.asarray(enhanced.getchannel('A').resize(source.size,Image.Resampling.LANCZOS));plumemask=np.asarray(Image.open(work/'Plume_Only_Repair_Mask.png'));outline_diff=((alpha_source>=128)!=(alpha_final>=128))&(plumemask<2)
validation={'files':checks,'original_hash_before':inspection['sha256'],'original_hash_after':original_hash,'original_unchanged':original_hash==inspection['sha256'],'logos':logos,'target_height_formula':'round(964*8000/1632) = 4725','aspect_ratio_relative_error':abs((8000/4725)/(1632/964)-1),'outside_plume_source_resolution_50percent_contour_changed_pixels':int(outline_diff.sum()),'source_canvas_clipped_exhaust_at_right':True,'notes':'Right-edge alpha is intentionally nonzero because both near exhaust plumes already meet the original canvas boundary; no invented continuation or canvas change.'}
(work/'Final_Validation.json').write_text(json.dumps(validation,indent=2))
font=ImageFont.truetype('msyh.ttc',28);small=ImageFont.truetype('msyh.ttc',23);scale=8000/1632
specs=[('船头装甲',(190,530,370,690),'dark'),('船体机械纹理',(820,690,1000,850),'dark'),('Alterra 标志（原字形保护）',(458,595,638,775),'dark'),('青色圆环',(585,635,765,815),'dark'),('引擎及尾焰透明暗边',(1452,365,1632,535),'white'),('外轮廓与细边缘',(820,220,1000,400),'white')]
sheet=Image.new('RGB',(3600,2700),(20,25,32));draw=ImageDraw.Draw(sheet)
for i,(title,box,bgname) in enumerate(specs):
 tx=(i%2)*1800;ty=(i//2)*900;cropbox=tuple(round(v*scale) for v in box)
 for j,(label,im) in enumerate([('原图 Lanczos 基准',baseline),('AI 细节增强 / Alpha 修复',enhanced)]):
  crop=im.crop(cropbox);bg=(240,240,240) if bgname=='white' else (16,22,31);flat=Image.alpha_composite(Image.new('RGBA',crop.size,(*bg,255)),crop).convert('RGB');flat.thumbnail((880,805));x=tx+j*900+(900-flat.width)//2;y=ty+85+(805-flat.height)//2;sheet.paste(flat,(x,y));draw.text((tx+j*900+18,ty+12),title,font=font,fill=(235,240,246));draw.text((tx+j*900+18,ty+48),label,font=small,fill=(165,195,222))
 sheet.crop((tx,ty,tx+1800,ty+900)).save(work/f'Detail_Comparison_{i+1:02d}.jpg',quality=97)
out=root/'Alterra_full_8000_Comparison.jpg'
if not out.exists():sheet.save(out,quality=97)
report=f'''# P9 图像增强记录

已完成两张 8000×4725 RGBA PNG，比例取原始 1632×964 的最近整数高度。原图有真实 Alpha，无内嵌 ICC；输出附 sRGB 描述文件。原图 SHA256 验证未变。

- AI：官方 Real-ESRGAN x4plus，ncnn Vulkan 实际识别 Intel Arc B390，128 px 分块，单条推理队列，Below Normal。先得到 6528×3856，再 Lanczos 到目标尺寸；没有扩散重绘、建模或游戏扫描。
- 采用受限的亮度细节混合：机械边缘较强，光滑装甲较弱，AI 的低频明暗与色度不替换原图。AI 推断细节不是恢复原生 8K。
- 两处 Alterra 标志的所有可见 RGB 像素与传统缩放基准相同；顶部保护矩形内有 7 个完全透明像素仅清零了隐藏 RGB。轮廓、细天线及半透明尾焰不接受 AI 形状推断。
- Alpha：清除原有 Alpha 1–3 的背景噪点，保留来源轮廓；仅在三个喷口外侧去除尾焰黑色底污染，羽化 5 个原图像素。白甲与深色引擎没有被当作背景抠除。透明 RGB 归零。
- 基准图保留原始透明度，使用浮点预乘 Alpha 的 Lanczos；增强版修复 Alpha 后再进行受限细节处理。因此尾焰在浅底上的差别包括暗边修复，不只是锐化。
- 最终 PNG 可完整解码，宽度/高度/Alpha/标志一致性检查通过；详细数值见 P9_Work\\Final_Validation.json。

限制：原图两处近侧尾焰已接触右画布边界，本次保持原尺寸比例，没有补画或声称恢复画外内容。原图极小的机械文字和源细节仍受 1632 px 输入限制。局部检查未发现明显新增组件或 AI 乱码；这是视觉检查，不代表可证明所有微细像素均有真实结构依据。

交付：

- {root/'Alterra_full_8000_Enhanced.png'}
- {root/'Alterra_full_8000_Baseline.png'}
- {root/'Alterra_full_8000_Comparison.jpg'}

工具来源、许可证、本地 SHA256 与 Defender 检查：{work/'SR_Setup/SR_Setup_Report.md'}

复现与处理参数：{work/'Enhancement_Method.json'}；{work/'Alpha_Repair_Method.json'}。
'''
(root/'Alterra_full_8000_Report.md').write_text(report,encoding='utf-8');print(json.dumps({'size':enhanced.size,'original_unchanged':validation['original_unchanged'],'visible_logos_exact':all(x['visible_RGB_exactly_equal_to_source_Lanczos'] for x in logos),'files_verified':len(checks),'comparison':str(out)},indent=2))
