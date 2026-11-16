import pathlib,json,hashlib,csv,math
root=pathlib.Path(__file__).resolve().parents[1]
stats=json.loads((root/'06_Report/Remaster_Model_Stats.json').read_text());geom=json.loads((root/'06_Report/Geometry_Refinement.json').read_text());tex=json.loads((root/'06_Report/Texture_Remaster.json').read_text());valid=json.loads((root/'06_Report/Final_PNG_Validation.json').read_text());project=json.loads((root/'06_Report/Project_Validation.json').read_text());prior=json.loads((root/'06_Report/Prior_Delivery_Integrity.json').read_text());ring=json.loads((root/'06_Report/Ring_Repair.json').read_text())
assert len(valid)==4 and all(r['passes'] for r in valid)
assert project['test_render_success'] and not project['missing_images'] and project['p5_thrusters_geometry_transforms_unchanged']
assert all(r['unchanged'] for r in prior)
views=['Rear_ThreeQuarter','Front_ThreeQuarter','Left','Right']
lines=['# Aurora HD Remaster：P6 验收报告','','完成日期：2026-10-28（Asia/Shanghai）。实际执行了局部几何重建、选择性曲面细分、4096 材质制作及四视角原生 8000 px 渲染；不是把旧成图简单放大。全部操作在本地，无游戏资源重新扫描/提取、无对外上传或印刷。','',
'## 结果','',
'- 已优先保存 1800×1800 圆环修复特写和同条件前后对比。圆环由 12 径向分段改为 128，发光环为 128×16；灰色外壳和后连接座都改为连续圆滑几何。',
'- 已保存 2048×1528 带原有蓝色尾焰的整船重制预览，以及原版/重制在相同相机、光照、缩放下的整船对比。',
'- 已保存四张 8000 px 宽 RGBA PNG，均通过透明度、半透明边缘、外边界与非空轮廓检查。',
'- 主 Blender 工程内嵌纹理，已重新打开并实际渲染，图片依赖无缺失。P5 的 12 个尾焰网格及空间变换哈希与输入一致。',
f'- 先前 P1–P5 交付清单中的 {len(prior)} 个文件哈希均未变化。全部新成果位于 `{root}`。','',
'## 几何修复','',
'| 范围（不含尾焰、隐藏归档和灯光） | 顶点 | 多边形面 | 三角形 |','|---|---:|---:|---:|',
f'| 原生纪念品模型 | 3,723（焊接后拓扑分析为 2,482） | 4,471 | 4,471 |',
f'| 重制船体与两侧圆环/连接座 | {stats["remaster_vertices"]:,} | {stats["remaster_faces"]:,} | {stats["remaster_triangles"]:,} |','',
'1. 对两侧圆环端面做几何拟合，保留中心、空间朝向和前壳原半径约 0.029951。重建 128 径向分段的外壳、浅凹端面、128×16 发光环及圆滑连接座。原连接座边界约 0.03067，重建圆形座半径 0.03075，差异约 0.3%；没有改变整船尺寸比例。',
'2. 修复原壳体后方仍可见的 12 边连接轮廓：边界细分为 132 段并投影至原圆周，再用 128 段圆座衔接。外圆理论弦高误差由 12 段的约 3.41% 半径降至 128 段的约 0.0301% 半径；这是真实轮廓变化，不只是把法线设为平滑。',
f'3. 选择 {geom["selectively_subdivided_edges"]:,} 条船体低夹角曲面边细分，投影 {geom["phong_projected_new_vertices"]:,} 个新增边顶点至混合切平面（Phong tessellation），每点最大位移限制为 0.0007 局部单位。没有对整船使用高等级 Subdivision。',
'4. 高夹角装甲、机械接合处保留硬边；UV 使用原拓扑插值。天线、小喷口等未全面重做。原始整个船体完整保存在隐藏的 P5_Original_Archived 集合内，未破坏性删除输入资产。',
'5. 圆环灰色外壳、暗色凹面和青色环为局部材质重建，用来消除旧低清贴图中的多边形边缘；不声称该处逐像素复原了原始游戏表面花纹。','',
'重制对象统计：','', '| 对象 | 顶点 | 面 | 三角形 |','|---|---:|---:|---:|']
for o in stats['remaster_objects']:lines.append(f'| {o["name"]} | {o["vertices"]} | {o["faces"]} | {o["triangles"]} |')
lines+=['','## 材质与纹理','',
'输入为已提取的未损毁 souvenir 512×512 色彩图、256×256 发光/法线素材，以及 starship_crashed 2048×2048 图集和已解码法线。没有重新提取。',
'实际输出 4096×4096：BaseColor、Normal、Roughness、Metallic、Emission；另保留 Damage_Replacement_Mask 与 Existing_Yellow_Paint_Mask。',
f'采用真实 2048 源细节，依据未损毁 512 版本的亮度/颜色差异遮罩替换烧损和污损区域；遮罩覆盖约 {tex["mask_coverage_fraction"]*100:.1f}%。文字与标志差异区域保留原低清来源，不猜测或生成新文字。只对已有黄色漆线边缘作抗锯齿轮廓收紧，未添加新条纹、铆钉、重复机械结构或标识。',
'原有接缝、面板和灯带利用最佳现有图集重连并作保守锐化；另外制作分离的粗糙度/金属度、恢复法线和弱微表面变化，发光图保留原 illumination 并结合原有青色区域。新增微表面是程序化重制细节，不是原游戏提取细节。',
'**4096 是重制工作纹理尺寸，并非恢复到了原生 4K 游戏纹理。** 未损毁替换区域仍受 512 输入限制；极小字样、天线和部分机械装饰依然受原素材质量限制。未把源烧损直接放大并称为新增细节，也未承诺所有污迹均已完美移除。','',
'## AI 检测与使用','',
'未使用 AI 图像增强或整船 AI 重绘，没有下载模型。检查常见 ComfyUI 路径及当前进程；本地模型目录 中只有 lmstudio-community 的 Qwen2.5-VL-7B-Instruct-GGUF / Qwen3.5-9B-GGUF 目录，未找到可直接运行的纹理超分/重绘工作流。本次使用 Blender、Pillow、NumPy 和传统图像算法。检测范围与原因见 03_AI_Enhanced，不能据此声称机器所有目录绝无其他模型。','',
'## 渲染、尾焰和透明度','',
'Blender 4.5.9 LTS，EEVEE Next 64 samples，Intel Arc B390 GPU 实际参与；P6 渲染进程出现对应 GPU 3D 引擎活动，见 GPU_Activity.json。未触发 CPU 回退。Blender 固定 4 线程、BelowNormal 优先级，单任务顺序渲染；不使用高分辨率 CPU 去噪。未更改显卡驱动或覆盖已有 Blender 环境。',
'船体是重新渲染的重制几何与材质；最终成图合成 P5 对应各视角的原生 8000 px 独立尾焰层，保持原相机与 P5 扩展画布完全一致。没有把同一张尾焰复制到四个视角。工程同时保留完整 P5 三维尾焰对象、材质和控制器，可以直接渲染；PNG 中的柔和光晕使用已验证的 P5 Alpha 图层。',
'P6 选择性几何修改未涉及喷口后方的遮挡轮廓，因此沿用 P5 各视角尾焰遮挡。若用户之后继续改动引擎，应重新生成对应尾焰层。',
'局部与整船前后对比均使用同一相机、光照、投影和显示缩放；Texture_Comparison_Consistent.jpg 两侧统一使用 Lanczos 缩放。早期中间纹理检查图包含最近邻放大版，仅作为过程记录，不用于主要对比结论。','',
'| 视角 | 最终 PNG 尺寸 | 原生船体渲染耗时 | 外边界最大 Alpha |','|---|---|---|---|']
for view in views:
 timing=json.loads((root/'06_Report'/f'HD_{view}_8000_Render.json').read_text());v=next(r for r in valid if f'_{view}_8000' in r['file']);lines.append(f'| {view} | {v["size"][0]}×{v["size"][1]} | {timing["seconds"]:.2f} 秒 | {v["border_max_alpha"]} |')
lines+=['','最终 PNG 为 RGBA 真透明，无背景矩形；检查时用的深色、海蓝色 JPEG 仅存在于对比目录。所有最终图均含半透明像素且四周 Alpha 为 0，未裁切船头、引擎和尾焰。','',
'## 主要交付文件绝对路径','']
for p in [root/'01_Geometry/Aurora_HD_Remaster_Editable.blend',root/'04_Comparison/Ring_Before_After.jpg',root/'04_Comparison/Ring_HD_Final_1800.png',root/'04_Comparison/Aurora_HD_Rear_ThreeQuarter_2048.png',root/'04_Comparison/WholeShip_Before_After_2048.jpg',root/'04_Comparison/Texture_Comparison_Consistent.jpg',root/'04_Comparison/HD_FourViews_Overview.jpg']:
 lines.append(f'- `{p}`')
for view in views:lines.append(f'- `{root/"05_FinalPNG"/f"Aurora_HD_{view}_8000.png"}`')
for p in sorted((root/'02_Textures').glob('*.png')):lines.append(f'- `{p}`')
lines+=['',f'全部交付文件（包括中间模型、原始渲染层、脚本和校验证据）的绝对路径、字节数与 SHA-256 见 `{root/"06_Report/Delivery_Manifest.csv"}`；清单不包含其自身。','',
'## 尚未解决的质量问题','',
'这是一版基于游戏纪念品的局部高清重制，尚不是重新获得的官方高精度无损 Aurora 原模。圆环表面局部采用清洁程序化材质，和原贴图花纹、旧磨损不会逐像素一致；原始隐藏版本可供回退比较。',
'细小机械件、部分引擎外壳和微小文字仍沿用低精度来源，未无限添加猜测性结构。4096 图集的部分清洁补片来自 512 素材，因此不应被宣传为全船每处都具有原生 4K 信息。',
'尚未进行厂家 ICC 色彩打样、车身贴合和实际印刷；本阶段只交付本地设计素材，不包含印刷或传播授权。']
(root/'06_Report/Aurora_HD_Remaster_Report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='Delivery_Manifest.csv')
with (root/'06_Report/Delivery_Manifest.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['absolute_path','bytes','sha256'])
 for p in files:w.writerow([str(p),p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()])
print('P6 report and manifest written:',len(files),'files')
