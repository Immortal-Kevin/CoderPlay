# P9 超分工具验证

- 下载来源：官方 xinntao/Real-ESRGAN 发布页 https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0
- 便携包：realesrgan-ncnn-vulkan-20220424-windows.zip，发行页列出 45,474,481 字节。验证包大小一致、ZIP 每个文件 CRC 正常。
- SHA256：`abc02804e17982a3be33675e4d471e91ea374e65b70167abc09e31acb412802d`。这是本地校验记录；官方该旧版资产未提供 SHA256，不冒称与发布方摘要比对。
- 来源工具许可：Real-ESRGAN 为 BSD-3-Clause，ncnn Vulkan 封装为 MIT；文本已保存。这不授予飞船图像版权。
- 可执行文件未数字签名。Windows Defender 实时防护保持开启，执行了便携目录自定义扫描；扫描命令成功，无该目录相关威胁检测记录。未关闭防护或更改执行策略。

## 实际推理结果



模型：`realesrgan-x4plus`，通用图片超分。未使用动漫模型，也未使用扩散生成。

256×256 输入 → 1024×1024 输出，耗时 **3.88 秒**，退出码 0。实际启动日志识别 `Intel(R) Arc(TM) B390 GPU`，Vulkan GPU 0；FP16 存储/运算可用。采用 `-t 128 -g 0 -j 1:1:1 -s 4`，进程 Below Normal。

```powershell
```

## 视觉观察与选择

测试裁切包含白色装甲、细缝、金色饰条、部分青环和 Alterra 字形。模型提高线条边缘连续性，白色表面较干净，未发现明显分块接缝；细小黑色开孔附近存在局部形状推断。整体较锐，建议最终与传统 Lanczos 以中等权重混合，低频装甲弱化，文字及标志保留原图缩放版本。

此包 README 提到 `realesrnet-x4plus`，但实际打包模型目录不含该模型；不能将本次推理声称为 ESRNet。现有 x4plus 已可在 GPU 正常工作，因此没有另行搭建 CPU 环境或安装大型依赖。

原始 `Alterra_full.png` 未写入或修改。首次普通整包下载速度较慢，已停止；可用的是上面的完整分段下载校验包。未采用下载残片。
