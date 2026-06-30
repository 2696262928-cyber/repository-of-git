# OCR 图片读取说明

系统已经支持可选 OCR 通道，用于读取 PDF 扫描页或 DOCX 内嵌图片中的文字。

## 一、当前能力

- PDF：将前若干页渲染成图片，再尝试 OCR 识别页面中文字。
- DOCX：读取 `word/media/` 中的内嵌图片，再尝试 OCR 识别图片中文字。
- OCR 文本会合并到报告正文后，再交给大模型评阅。
- 页面会显示独立的“OCR 文本”标签页，便于检查识别结果。

## 二、使用方式

1. 启动系统。
2. 上传 PDF 或 DOCX 实验报告。
3. 勾选左侧“读取图片/扫描页文字 OCR”。
4. 如需大模型综合评阅，同时勾选“启用大模型评阅”。
5. 点击“开始检测”。

## 三、系统依赖

Python 依赖已经写入 `requirements.txt`：

```text
pillow
rapidocr-onnxruntime
opencv-python-headless
```

OCR 默认使用 `rapidocr-onnxruntime`，它可以通过 pip 安装，不需要额外安装系统级 Tesseract 程序。
OpenCV 用于 OCR 前的图像预处理、纠偏、文本区域检测和图片质量分析。

只要运行：

```powershell
pip install -r requirements.txt
```

即可安装 OCR 所需 Python 依赖。

## 四、局限性

- OCR 主要识别图片中的文字，不等于理解波形、电路图、流程图或实验现象。
- 图片质量差、字体太小、截图模糊时，识别效果会下降。
- DeepSeek 文本模型只能基于 OCR 出来的文字进行评阅，不能直接看图片。
- 表格、波形、代码截图等图片内容分析依赖 OpenCV 的规则检测，结果应作为辅助提示。

## 五、建议写入最终报告

可以将该能力描述为：

> 系统支持 PDF/DOCX 文档的文本解析，并提供可选 OCR 功能，用于读取扫描页或截图中的文字信息。系统还基于 OpenCV 对表格、波形图、代码截图、电路图等图片类型进行辅助识别和质量提示，但不等同于完整多模态视觉理解。
