import pathlib,json,csv,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
validation=json.loads((root/'05_Report/PNG_Alpha_Validation.json').read_text());integrity=json.loads((root/'05_Report/Ship_Integrity.json').read_text());editable=json.loads((root/'05_Report/Editable_Validation.json').read_text());prior=json.loads((root/'05_Report/P1_P4_Unchanged.json').read_text())
assert len(validation)==8 and all(r['passes'] for r in validation)
assert integrity['geometry_uv_identical'] and editable['original_material_nodes_and_images_unchanged'] and editable['length_driver_works'] and all(r['unchanged'] for r in prior)
views=['Rear_ThreeQuarter','Front_ThreeQuarter','Left','Right'];timings=[json.loads((root/'05_Report'/f'{v}_8000_Render.json').read_text()) for v in views]
lines=['# P5 Aurora 蓝色电离子尾焰验收报告','','完成日期：2026-10-28（Asia/Shanghai）。本阶段仅本地制作，没有重新扫描/提取游戏资源，没有印刷、发布或上传。','',
'## 交付结论','',
'完成四视角 **8000 px 宽透明 RGBA PNG**、对应四张独立尾焰图层、1600 px 预览、深色/海蓝色背景检查图，以及带参数驱动的可编辑 Blender 工程。所有八张最终透明图均通过解码、Alpha 渐变、外边界与非空轮廓检查。',
f'此前 P4 交付哈希清单中的 {len(prior)} 个文件均保持原哈希；原模型几何/UV、材质节点及内嵌贴图的哈希也与 P4 一致。新文件全部位于 `{root}`。','',
'## 渲染设备与资源控制','',
'- Blender **4.5.9 LTS**，沿用既有便携版；未覆盖 Blender 环境、未修改显卡驱动。实际引擎为 **EEVEE Next / BLENDER_EEVEE_NEXT**，64 samples。',
'- **Intel Arc B390 GPU 成功参与渲染。** Cycles 设备枚举识别到 B390 ONEAPI；EEVEE 1024×733 实际试渲成功（约 12.5 秒，含初始化），后续 1600 px 试渲成功。EEVEE 渲染进程对应 Windows GPU 3D 引擎计数出现非零活动，并成功完成四张高清原始尾焰层。依据是设备枚举、实际输出、进程 GPU 活动和日志，不是任务管理器总利用率。',
'- `gpu.platform` 在 Blender 后台模式无法返回绘图上下文信息，这项查询失败已保留在 Device_Detection.json；不影响实际 EEVEE GPU 渲染。oneAPI **只完成设备识别，没有用于本次 Cycles 渲染**。',
'- **未触发 CPU 回退。** Blender 命令行 `--threads 4`、场景固定 4 线程、OMP_NUM_THREADS=4；进程设置 BelowNormal；按顺序执行单个渲染，再执行单个合成。GPU 驱动及内部调度线程不等同于 Cycles 渲染线程，未声称整个系统只运行四个线程。',
'- 渲染脚本包含 CPU 4 线程、16 samples、不使用大图去噪的回退分支。本次没有执行该分支。Windows GPU WMI 计数可能大于 100，报告只用其证明对应进程有 GPU 活动，不把这些读数解释为可靠百分比。','',
'| 角度 | EEVEE 原始尾焰尺寸 | 渲染耗时 | 最终透明 PNG |','|---|---|---|---|']
for r in timings:
 final=next(v for v in validation if pathlib.Path(v['file']).name==f'Aurora_Ion_{r["view"]}_8000.png')
 lines.append(f'| {r["view"]} | {r["render_width"]}×{r["render_height"]} | {r["seconds"]:.2f} 秒 | {final["size"][0]}×{final["size"][1]} |')
lines+=['','上述耗时只包含三维尾焰/遮挡层渲染，不包含 PNG 合成/保存，不能与 P4 整船 Cycles 渲染直接作同等工作量的速度比较。','',
'## 尾焰制作、参考与遮挡','',
f'已实际读取指定原版宣传海报：`{root.parent/"01_SourceAssets/poster/poster_aurora__-963771210458364377.png"}`。参考船尾短、宽、柔和的蓝色推进光，未复制海报天空、星空、文字或其他背景。',
'从既有原生纪念模型喷口端面顶点测得四个喷口：X=±0.120033212，Y=0.33250665，Z=0.044989898 / -0.040943504，半径约 0.01668825，统一轴向 +Y。单位为模型局部单位，不是实际飞船米制尺寸。',
'每个喷口有 Core、Plasma、Halo 三个独立三维椭球对象；采用 Transparent/Emission 混合、朝向边缘衰减、Noise Texture 微扰。冷白青色核心靠近喷口，蓝色宽光晕向后展开；几何尾焰最远约 0.065，即喷口直径的约 1.95 倍。没有激光束、橙红火焰、烟雾或爆炸。',
'同一组三维对象通过四个既有相机分别渲染。另建船体 Holdout 副本用于遮挡，原船体及材质不改动；近远喷口重叠关系由三维深度决定。侧视自然只见近侧两束，前方 3/4 的部分核心被船体遮挡，这是正常结果，不是少建了引擎。',
'最终方法为 **三维尾焰渲染 + 原始 P4 船体 PNG 合成**，不是纯二维手绘/复制尾焰的回退方案。独立尾焰图层含可见光学辉光，已按该视角的船体遮挡裁去不可见部分。先在预乘 Alpha 空间柔化发光，再恢复正确直通 RGBA；蓝色 Bloom 的 Alpha 由模糊后的发光遮罩生成，避免透明 PNG 的辉光丢失。光学光晕可少量跨过喷口边缘。',
'相机位置、方向不变；为容纳尾焰及光晕，四边各增加原宽度 6% 的透明画布，保持原像素投影比例后，再统一缩放到 8000 px 宽。故船体在最终画面中略小，未改变其形状/贴图，也没有裁切船尾光晕。此缩放不应被描述为船体像素逐点不变。','',
'## 可编辑工程','',
f'主工程：`{root/"01_Blender/Aurora_IonThrusters_Editable.blend"}`。已回读，内嵌原有四张图片。',
'在 `ION_MASTER_PARAMETERS` 空对象上调整 LengthScale、RadiusScale、Brightness、OpacityScale；均通过驱动连接尾焰几何/发光/透明度。长度驱动已实测从 1 调至 1.2，Plasma Y 半轴从 0.031 变为 0.0372。颜色可在三个 Ion 材质的 Emission 节点修改。各喷口对象和材质均有明确命名。',
'工程有 Beauty（船体+尾焰）和 ThrusterOnly_Occluded（遮挡尾焰层）两个 View Layer。最终 PNG 保留 P4 船体底图的光照；若直接渲染 Beauty，会采用 EEVEE 对船体着色，与 P4 Cycles 底图存在光照差异。要复现本次最终 PNG，应渲染尾焰层后运行 compose_ion.py。',
'`render_ion_view.py` 为默认 v02 配置的可复现渲染脚本，`compose_ion.py` 为 Alpha 安全合成脚本；自定义参数请在 Editable 工程中先调整并输出尾焰层，再调用合成。v01/v02 工程及初版预览保留，没有删除或覆盖此前阶段成果。','',
'## 透明度与边缘验收','',
'| 文件 | 尺寸 | 半透明像素数 | 外边界最大 Alpha | 验收 |','|---|---|---|---|---|']
for r in validation:lines.append(f'| {pathlib.Path(r["file"]).name} | {r["size"][0]}×{r["size"][1]} | {r["gradient_alpha_pixels"]:,} | {r["border_max_alpha"]} | 通过 |')
lines+=['','最终 PNG 没有深色、海蓝色或矩形背景。背景色仅存在于 02_Preview 的 JPEG 检查图。透明像素 RGB 清零，发光边缘按预乘 Alpha 模糊后解除预乘；已在深色与海蓝色背景下检查，没有发现明显黑边/白边或裁切末端。','',
'## 全部交付路径','',
'全部文件（包括原始尾焰层、低清试渲、日志、脚本和证据）的绝对路径、大小与 SHA-256 见：',f'`{root/"05_Report/Delivery_Manifest.csv"}`。清单不包含清单自身。','',
'主要成品：','']
for view in views:
 for p in [root/'03_FinalPNG'/f'Aurora_Ion_{view}_8000.png',root/'04_ThrusterOnly'/f'IonOnly_{view}_8000.png']:lines.append(f'- `{p}`')
for p in [root/'01_Blender/Aurora_IonThrusters_Editable.blend',root/'01_Blender/Ion_Parameters_v02.json',root/'02_Preview/P5_AllViews_Background_Check.jpg']:
 lines.append(f'- `{p}`')
lines+=['','背景检查图：','']
for view in views:
 for bg in ['Dark','OceanBlue']:lines.append(f'- `{root/"02_Preview"/f"{view}_8000_{bg}.jpg"}`')
lines+=['','## 尚未解决的问题','',
'尾焰是依据海报的本地程序化重建，并非提取到了游戏原始粒子/推进特效。体积散射和海报艺术处理不可能逐像素一致；本版采用轻量三维发光面与光学柔化，没有真实流体模拟。',
'沿用的船体仍为 P4 原生纪念模型，原色彩图 512×512；本阶段未增加船体原生纹理细节。海蓝色背景为 RGB(8,92,145) 的视觉近似，不是蝴蝶谷蓝实车漆色测量或色彩打样。',
'透明图是个人本地设计素材，仍需用户后续确认印刷授权与印厂工艺；本阶段未进行实际印刷或对外发布。']
report=root/'05_Report/Aurora_IonThrusters_Report.md';report.write_text('\n'.join(lines)+'\n',encoding='utf8')
files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='Delivery_Manifest.csv')
with (root/'05_Report/Delivery_Manifest.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['absolute_path','bytes','sha256'])
 for p in files:w.writerow([str(p),p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()])
print('P5 report complete;',len(files),'files,',len(validation),'transparent PNG validations')
