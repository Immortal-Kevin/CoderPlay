# Aurora 极光号提取与车膜素材报告


## 结论与交付等级

**保守评定 Level C，另附游戏原生完整轮廓纪念模型及其材质重配候选。** 没有在本次资源扫描中找到可确认的、用于飞行场景的完整未损毁高精度 Aurora 原模。找到了游戏内 `starship_souvenir`：它是原生、未损毁轮廓的纪念品模型，不能把它称为找回了完整版场景模型。

已实际交付三组、共 12 张 8,000 px 宽透明 PNG，并交付可编辑 Blender 工程、嵌入纹理 GLB、原始 OBJ/UV/贴图、候选资源索引及扫描证据。全部处理仅在本地完成；游戏目录只读，未上传游戏资产。

## P1：扫描证据与来源

解析了 5,472 个包/序列化资源文件，索引记录 177,256 条对象（GameObject、Mesh、Texture2D、Material、Sprite、AssetBundle、MonoBehaviour）。候选关键词 Aurora、Alterra、Starship、Crash、Spaceship、Ship exterior，命中 4,665 条候选，其中 Mesh 216 条。扫描错误日志为空。不是仅凭文件名判断。
检查范围包括 Aurora 场景、main 场景、资源依赖包、纪念品、海报、损毁/爆炸/LOD 模型。独立的开场完整飞行船模未在此次对象索引中确认；这不等于证明所有游戏版本均不存在此模型。

主要资源（均位于游戏 `Subnautica_Data/StreamingAssets/aa/StandaloneWindows64/`）：

| 资源 | 原包 | 结果 |
|---|---|---|
| starship_crashed | aurora.unity_c58052952278deb41432a90d929a7a40.bundle | 原始坠毁船体；32,921 顶点、36,596 三角形，16 材质槽；含原有损坏 |
| starship_exploded_exterior | 同一 Aurora 场景包；另有 duplicateassetssorted_assets_bundle679_02ebd4209d95eb74a02ecf796026c976.bundle 中的版本 | 爆炸后外壳、内部结构及 LOD；已导出，不能当作完整飞船 |
| starship_souvenir | starship_souvenir.prefab_79229df7fa5c8b69cb84b6abc2453f68.bundle | 完整轮廓纪念品，3,723 顶点、4,471 三角形；原色彩图 512×512 |
| starship_crashed 图集 | duplicateassetssorted_assets_bundle1744_9e8d9c4b078a01489d3e5cdd54dd2b46.bundle | 2048×2048 原始色彩图、法线与高光图；图集含损伤 |
| poster_aurora | poster_aurora.prefab_cdb053c01e3261f07d87f31dc8e84161.bundle | 1024×512 原始海报，仅作为原图/设计参考保存；没有把其背景混入最终渲染 |

最终导出清单记录 10,349 项：GameObject 4033、Material 440、Mesh 280、MeshFilter 733、MeshRenderer 733、Texture2D 97、Transform 4033。大量条目是场景对象与组件 JSON，不代表有这么多飞船模型。
原始导出位于 `01_SourceAssets/Verified_Exports`，按源包及序列化 CAB 分目录，避免不同文件 path ID 重复。初步导出目录保留作中间记录；应以 Verified_Exports 与 Final_Export_Manifest.json 为准。

## P2/P3：模型、材质与修复界限

1. **starship_souvenir**：原生纪念品几何与原始贴图；完整轮廓，低精度来源。未补造高精度船体。
2. **starship_crashed**：保留原始坠毁几何、UV、16 材质引用及解析出的依赖贴图；不掩盖损伤。
3. **Aurora_Intact_Atlas2048**：在原生纪念品几何/UV 上重配原始 2048 船体图集。名称中的 Intact 仅指轮廓，**贴图仍有原有烧损、破口图案**，不是无损完整船模。该候选细节高于 512 原图，但不能代替未损毁原始设计。
4. 另附 starship_exploded_exterior 的 OBJ、材质、纹理、Blender 和 GLB，作为实际可用组件。
未做镜像补造或猜测性几何重建。完成的是资源依赖恢复、UV/材质重连、Unity DXT5nm 法线解包（A/G→X/Y，重建 Z）、中性灯光及透明渲染。Unity 自定义着色器转换为 Blender Principled，粗糙度/金属度采用统一近似；高光图原文件保留，未声称像素级还原游戏着色器。
几何原有孔洞、分离壳体、UV 接缝保留；不是可直接 3D 打印的封闭流形模型。未能可靠恢复完整高精度无损船体，因此按可验证资源转入渲染，不把推测模型标作原始提取。

## P4：透明 PNG 与尺寸验证

Blender Cycles CPU，16 samples + 去噪，正交投影，透明 Film，RGBA 8-bit PNG。左右侧及前/后 3/4 都来自实际三维相机；船头朝局部 -Y，上方为 +Z；Left 相机在 +X。整个包围盒留出约 12% 画幅余量。所有最终文件逐一解码、校验 Alpha、非空轮廓及边界。

**8,000 px 是实际新渲染像素宽度，不代表源贴图有 8K 细节。** 纪念品色彩图只有 512×512；重配图集为 2048×2048；坠毁版本使用原有多材质贴图。没有把二维插值放大冒充原始高清。尚无车身尺寸、出血、色彩 ICC 或厂家工艺参数，PrintReady 文件是透明素材，未做车辆贴合/分片和印厂色彩打样。

| 文件 | 尺寸 | Alpha | 外边界最大 Alpha |
|---|---|---|---|
| starship_souvenir_Left_8000.png | 8000×4033 | RGBA，透明及半透明边缘有效 | 0 |
| starship_souvenir_Right_8000.png | 8000×4033 | RGBA，透明及半透明边缘有效 | 0 |
| starship_souvenir_Front_ThreeQuarter_8000.png | 8000×5723 | RGBA，透明及半透明边缘有效 | 0 |
| starship_souvenir_Rear_ThreeQuarter_8000.png | 8000×5723 | RGBA，透明及半透明边缘有效 | 0 |
| Aurora_Intact_Atlas2048_Left_8000.png | 8000×4033 | RGBA，透明及半透明边缘有效 | 0 |
| Aurora_Intact_Atlas2048_Right_8000.png | 8000×4033 | RGBA，透明及半透明边缘有效 | 0 |
| Aurora_Intact_Atlas2048_Front_ThreeQuarter_8000.png | 8000×5723 | RGBA，透明及半透明边缘有效 | 0 |
| Aurora_Intact_Atlas2048_Rear_ThreeQuarter_8000.png | 8000×5723 | RGBA，透明及半透明边缘有效 | 0 |
| starship_crashed_Left_8000.png | 8000×3983 | RGBA，透明及半透明边缘有效 | 0 |
| starship_crashed_Right_8000.png | 8000×3983 | RGBA，透明及半透明边缘有效 | 0 |
| starship_crashed_Front_ThreeQuarter_8000.png | 8000×5691 | RGBA，透明及半透明边缘有效 | 0 |
| starship_crashed_Rear_ThreeQuarter_8000.png | 8000×5691 | RGBA，透明及半透明边缘有效 | 0 |

模型检查：

| 模型 | 顶点/三角形 | UV | 边界边/非流形边 | 缺失纹理 | GLB 回读 |
|---|---|---|---|---|---|
| starship_souvenir | 3723/4471 | True | 2659/2659 | 0 | 成功 |
| starship_crashed | 32921/36596 | True | 24716/24716 | 0 | 成功 |
| Aurora_Intact_Atlas2048 | 3723/4471 | True | 2659/2659 | 0 | 成功 |

FourViews.blend 内嵌纹理并保存四台命名正交相机。每台相机有 render_width、render_height 和 render_output 自定义属性；切换 3/4 视角时按属性设置对应纵横比。GLB 已重新导入验证。

## 工具、来源、许可证与安全检查

- UnityPy **1.25.4**，MIT；来源 [上游仓库](https://github.com/K0lb3/UnityPy) 与 PyPI 官方项目。依赖局部安装于 Tools/python；pip_install_report.json 记录下载 URL、版本、SHA-256。UnityPy wheel 实际哈希比对成功，见 UnityPy_Download_Verification.json。
- Blender **4.5.9 LTS**，GPL；便携版来源 [Blender 官方镜像](https://mirror.blender.org/release/Blender4.5/)。官方主下载站遇到访问验证，切换官方镜像，未绕过访问保护。ZIP SHA-256：`41da973b9bf95bb312cbeff4d1982feb13259b43c821686b9bafea4dfe5477cf`，与官方 .sha256 一致。
- Pillow **13.0.0**（HPND），用于格式/Alpha 检查及棋盘预览；Python **3.12.14** 使用已配置的本地运行时。
- 未安装付费或破解工具；没有执行管理员安装、系统设置修改、DRM 绕过或安全防护关闭。Windows Defender 实时保护已开启，Tools 自定义扫描命令完成；任务路径检测结果见 Defender_Tool_Scan.json。这不是对所有软件作绝对安全保证。
- 本次使用 UnityPy 直接解析 Unity 2019.4 数据及依赖，已得到有效 Mesh/UV/Texture，故无需额外安装 AssetRipper/AssetStudio。工具许可证只覆盖工具，不是游戏资产授权。

## 尚未解决的问题与许可

- 未找到可确认的高精度未损毁场景/序章 Aurora；最接近完整外形的是原生纪念品模型，细节受低精度网格与贴图限制。
- 2048 重配候选保留损伤图案；没有用不可靠方法宣称恢复无损版本。未来若获得官方高精度原模或获准的官方设计素材，可替换低精度来源重新渲染。
- 不具备个人汽车贴膜印刷授权证明；本地技术成果不等于取得游戏资产使用权。用户后续自行联系版权方和印厂确认授权。未联系版权方、未发布、未上传资产。
- 先前 280 条 Mesh 错误来自导出后读取不存在的统计字段 m_VertexCount，不是 OBJ 导出失败；已逐一解析对应 OBJ，补齐顶点/面数，最终 Unresolved_Export_Errors.json 为 []。



中间 1600 预览用于观察和材质检查，光照可能与最终渲染不同；最终以 04_PrintReady 的 8000 文件及 Final_Render_ContactSheet.jpg 为准。03_Renders 保存最终图副本。Tools 内的 Python 脚本可复现扫描、依赖恢复、渲染与校验。
