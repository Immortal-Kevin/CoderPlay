# P1/P2 已落盘成果

实测 Unity 2019.4.36f1。已解析 5,472 个 Unity 包/序列化资源文件，对象索引 177,256 条，候选 4,665 条（Mesh 216 条）。扫描错误日志为空。

实际找到并导出：starship_crashed、starship_exploded_exterior 与内部组件/LOD、starship_souvenir 纪念品模型、poster_aurora 海报。未确认高精度完整未损毁飞行场景原模。

资源索引见 Asset_Object_Index.csv、Candidate_Resources.csv。原始路径与导出路径见 Final_Export_Manifest.json。共有 10,349 条有效导出记录；其中包括大量 GameObject/Transform/Renderer 等场景依赖 JSON，不代表飞船模型数量。最终未解决导出错误为零。

Verified_Exports 按源包和 CAB 序列化文件分目录存储，防止不同 CAB 的 path ID 冲突。最初统计脚本在 OBJ 已成功写出后读取不存在的 m_VertexCount 字段，导致 280 条统计错误；已逐一重新读取 OBJ 验证顶点和面并更正清单，原错误日志保留供审计。

02_Models 中已完成坠毁船体 16 个材质槽、纪念模型 1 个材质槽、爆炸后外壳 7 个材质槽的依赖追踪。贴图来源及材质槽对应见 Model_Texture_Provenance.json。Unity 自定义着色器采用 Blender Principled 近似；源材质 JSON 与源贴图保留。

纪念品轮廓完整，但原色彩图仅 512×512。Aurora_Intact_Atlas2048 是纪念品几何搭配原生坠毁船体 2048×2048 图集的派生候选，图集中仍有损伤。不能将它视为恢复的高精度未损毁场景模型。

五个主要来源包的提取后 SHA-256 与提取时一致，见 Source_ReadOnly_Verification.json。游戏源目录未被改写。没有上传资产或进行公开传播。

Blender 4.5.9 LTS 官方镜像便携版已通过官方 SHA-256 校验；UnityPy 1.25.4 wheel 已通过 PyPI SHA-256 比对。Tools 目录 Defender 自定义扫描完成，安全防护保持开启。

后续最终渲染验收以 Aurora_Extraction_Report.md、PNG_Validation.json、Model_Validation.json 为准；本文件仅记录已经完成的扫描与提取事实。
