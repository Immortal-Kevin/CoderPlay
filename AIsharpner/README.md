# AIsharpner · AI 锐化

Windows 本地照片处理工具。双击 `启动 AIsharpner.cmd` 打开。首次安装依赖需要联网，之后使用随附的模型在本机处理照片。当前版本使用 64 位 Python 3.14 和 OpenVINO 2026.4.1。

## 使用

1. 在左栏选择照片，查看格式、像素尺寸和文件大小。
2. 在中栏选择检测到的 Intel 核显或 Intel NPU，设置锐化率、细节补全自由度和输出分辨率。缩放支持 25% 至 300%，步进 25%。
3. 点击 **AI 优化**。编译完成并开始分块推理后，右栏按已处理分块估算剩余时间。
4. 点击 **1:1** 以实际像素大小检查毛孔、细纹和汗毛。用滚轮缩放，按住左键拖动。点击 **切换原图 / 优化图** 对比同一视野，点击 **另存为** 导出 PNG、JPEG、WebP 或 TIFF。

每次优化完成后，结果会自动以 PNG 保存到程序目录下的 `output draft`。编号从 0 开始，按目录中已有草稿的最大编号接续。例如锐化 55%、缩放 100%、细节补全 45% 的首张结果为 `AIDR-IMG-0- S55P100F45.png`。另存为可额外导出其他格式。

批量处理时，在导入窗口按住 Ctrl 或 Shift 多选照片，设置一组参数后点击 **批量 AI 优化**。右栏显示整批进度和当前文件，成功的图片逐张自动保存。单张读取或处理失败时会继续处理其余图片，最后列出失败原因。左栏下拉列表可切换预览本批照片及其已保存的优化图。

第一遍使用所选缩放比例。第二遍只处理第一遍未保存成功的照片，在 25% 步进档位中选用不超过原设定、符合输出像素上限且能编译模型的最高比例。首次推理失败时从下一档开始检查。文件名中的 `P` 记录实际比例，两遍后仍失败的照片会显示原因。

## 格式与限制

- 支持 JPEG、PNG、TIFF、WebP、BMP、HEIC/HEIF、AVIF，以及 LibRaw 能解码的 CR2、CR3、NEF、NRW、ARW、SR2、DNG、RAF、RW2、ORF、PEF 和 SRW。相机 RAW 兼容性取决于机型。多帧文件使用首帧。
- 输出限 4800 万像素。单张输入限 4800 万像素，批量输入单张限 9600 万像素。导出为 8 位图像，源 EXIF 等元数据不随结果写出。JPEG 导出时将透明区域合成到白色背景。
- AI 模型、锐化与输出缩放在明确选中的 Intel 核显或 Intel NPU 上运行。CPU 负责文件解码、分块、预览和导出编码。设备不可用或模型编译失败时会提示错误。
- 使用 Real-ESRGAN 的低降噪实拍通用权重 `realesr-general-wdn-x4v3`，随附转换后的 OpenVINO 模型。细节滑杆控制模型恢复的亮度纹理，锐化滑杆增强原图中已有的局部微对比。两项在 100% 输出分辨率下也生效。
- 默认锐化 55%、细节补全 45%。增强应用于整张照片。细节补全会生成估算纹理，调得过高时，原图噪点和压缩痕迹也可能变得明显。

## 模型与运行时

- [Real-ESRGAN 官方权重与发行说明](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0)
- [OpenVINO GPU 驱动与设备说明](https://docs.openvino.ai/2026/openvino-workflow/running-inference/inference-devices-and-modes/gpu-device.html)
- [OpenVINO NPU 驱动与设备说明](https://docs.openvino.ai/2026/openvino-workflow/running-inference/inference-devices-and-modes/npu-device.html)
