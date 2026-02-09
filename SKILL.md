---
name: video-summarizer
description: >
  视频内容快速总结工具。提取视频核心信息、生成结构化总结（基础信息/一句话总结/核心主题/关键要点/详细大纲/标签/资源汇总/评价）。
  使用场景：当用户需要快速了解视频内容、提取视频要点、查找视频中的资源时。
  关键词：总结视频、视频总结、视频内容提取、视频要点、视频大纲、视频资源、视频摘要
---

# 视频内容总结工具

一站式视频内容提取与智能总结，支持 B站、YouTube、抖音 等平台。

## 工作目录设置

使用**当前工作目录**作为输出目录（即运行命令时所在的目录）。

所有文件（视频、字幕、文字稿、总结报告）都将保存到当前目录。

## 依赖环境检测

运行前检测以下依赖，如缺失则提示安装：

```bash
# 1. yt-dlp
yt-dlp --version

# 2. FFmpeg
ffmpeg -version

# 3. Python 依赖
python -c "import pysrt; from dotenv import load_dotenv; print('OK')"

# 4. RapidOCR (用于烧录字幕识别，ONNX 轻量版)
python -c "from rapidocr_onnxruntime import RapidOCR; print('OK')"

# 5. FunASR (中文语音转录，推荐)
python -c "from funasr import AutoModel; print('OK')"

# 6. requests (用于抖音下载)
python -c "import requests; print('OK')"
```

**安装命令（如缺失）**：
```bash
# 基础依赖
pip install yt-dlp pysrt python-dotenv requests

# FunASR (中文语音转录，轻量且效果好)
pip install funasr modelscope

# RapidOCR (ONNX 轻量版，用于烧录字幕识别)
pip install rapidocr-onnxruntime

# Whisper (备选方案)
pip install openai-whisper
```

## 工作流程（4 阶段）

### 阶段 1: 下载视频

1. 获取用户视频 URL
2. **判断视频平台**：
   - **抖音链接**（douyin.com 或 v.douyin.com）：使用专用脚本下载
   - **其他平台**（B站、YouTube等）：使用 yt-dlp 下载

#### 抖音视频下载

对于抖音链接，使用 `scripts/download_douyin.py`：

```bash
python scripts/download_douyin.py "<抖音链接>" "<输出路径>"
```

**支持的抖音链接格式**：
- 短链接：`https://v.douyin.com/xxxxx`
- 长链接：`https://www.douyin.com/video/xxxxx`
- 精选页：`https://www.douyin.com/jingxuan?modal_id=xxxxx`
- 分享链接：`https://m.douyin.com/share/video/xxxxx`

**下载流程**：
```
抖音链接
    ↓
[Mobile UA 访问] ──→ 获取重定向后页面
    ↓
[提取 RENDER_DATA] ──→ 解析视频元数据
    ↓
[提取 play_addr] ──→ 获取无水印视频URL
    ↓
[下载视频] ──→ 保存到当前目录
```

#### 其他平台下载（yt-dlp）

对于 B站、YouTube 等平台：

```bash
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "./%(id)s.%(ext)s" \
  "<video_url>"
```

3. 记录视频文件路径

### 阶段 2: 智能字幕提取

使用 scripts/extract_subtitle_funasr.py 进行智能字幕提取，自动选择最佳方案：

```bash
python scripts/extract_subtitle_funasr.py <视频路径> <输出SRT路径>
```

**智能提取流程（三层优先级）**：

```
视频输入
    ↓
[1️⃣ 内嵌字幕检测] ──→ 检测到字幕流 ──→ 直接提取（准确度最高）
    ↓ 未检测到
[2️⃣ 烧录字幕检测] ──→ 采样帧 OCR 识别 ──→ 检测到文字 ──→ 全视频 OCR 提取
    ↓ 未检测到
[3️⃣ FunASR 语音转录] ──→ 中文优化转录（效果优于 Whisper）
    ↓
输出 SRT 字幕
```

**三层提取策略详解**：

| 层级 | 方法 | 适用场景 | 准确度 | 速度 |
|------|------|---------|--------|------|
| **L1** | 内嵌字幕提取 | 视频自带字幕流 | ⭐⭐⭐⭐⭐ | ⚡ 极快 |
| **L2** | RapidOCR 烧录字幕识别 | 字幕烧录在画面中 | ⭐⭐⭐⭐ | 🚀 快 |
| **L3** | FunASR Nano 语音转录 | 无字幕，纯语音 | ⭐⭐⭐ | 🐢 中等 |

**技术栈说明**：

- **RapidOCR (ONNX)**: 用于检测和提取烧录在视频画面中的字幕
  - 🚀 轻量级：ONNX Runtime 推理，无需 GPU
  - 🎯 跨平台：Windows/Linux/Mac 均支持
  - 📦 易部署：单 pip 安装，无复杂依赖
  - ✨ 高精度：基于 PaddleOCR 模型优化

- **FunASR Nano**: 阿里开源中文语音识别模型
  - 🚀 轻量级：~100MB vs Whisper Large ~1.5GB
  - 🎯 中文优化：针对中文语音专门训练，效果优于 Whisper
  - ⏱️ 时间戳：支持字级别时间戳
  - 💨 速度快：CPU 上也能快速运行

**备选方案**：

如需使用 Whisper（英文内容推荐）：
```bash
python scripts/extract_subtitle.py <视频路径> <输出SRT路径>
```

如需手动控制，可使用原 transcribe_audio.py：
```bash
python scripts/transcribe_audio.py <视频路径> <输出SRT路径> [模型] [语言] [设备]
```

### 阶段 3: 文稿校正

使用 scripts/correct_text.py 进行智能文稿校正：

```bash
python scripts/correct_text.py <SRT路径> <输出文字稿路径>
```

**校正功能**：
- ✅ 修正同音字错误（如"几尾鸟"→"几维鸟"）
- ✅ 修正专业术语（如"霍比屯"→"霍比特村"）
- ✅ 补充标点符号
- ✅ 合并字幕为连续段落

**校正示例**：
```bash
python scripts/correct_text.py ./BV1z9FszpEup.srt ./BV1z9FszpEup_文字稿.md
```

**常见修正映射**：
| 错误 | 正确 |
|------|------|
| 几尾鸟 | 几维鸟 |
| 霍比屯 | 霍比特村 |
| 音弗卡吉尔 | 因弗卡吉尔 |
| 普海基湖 | 普卡基湖 |
| 星巴堡 | 星巴克 |

**校正输出格式**：
```markdown
# 视频语音转录文字稿

**视频来源**: [URL]
**转录时间**: [日期]

---

## 完整文字稿

[校正后的正文内容]

---

## 原始 SRT 字幕

[带时间戳的原始转录]
```

### 阶段 4: 文件重命名（新增）

使用 scripts/rename_with_title.py 根据视频标题重命名所有文件：

```bash
python scripts/rename_with_title.py <视频URL> [旧文件名模式]
```

**重命名功能**：
- ✅ 自动获取视频标题
- ✅ 批量重命名所有相关文件
- ✅ 清理文件名中的非法字符

**重命名示例**：
```bash
# 从URL获取标题并重命名
python scripts/rename_with_title.py "https://www.bilibili.com/video/BV1z9FszpEup/"

# 使用自定义标题
python scripts/rename_with_title.py --title "一辈子值不值得去一次新西兰" "BV1z9FszpEup"
```

**重命名效果**：
```
BV1z9FszpEup.mp4        → 一辈子值不值得去一次新西兰_出行参考5.mp4
BV1z9FszpEup.srt        → 一辈子值不值得去一次新西兰_出行参考5.srt
BV1z9FszpEup_文字稿.md  → 一辈子值不值得去一次新西兰_出行参考5_文字稿.md
BV1z9FszpEup_总结.md    → 一辈子值不值得去一次新西兰_出行参考5_总结.md
```

### 阶段 5: 智能视频内容总结

基于校正后的文字稿，生成结构化的视频内容总结。使用 references/summary_prompt.md 中的提示词模板。

**总结包含以下维度**：

1. **基础信息** - 标题、作者、视频时长、发布时间
2. **一句话总结** - 极致精简的核心观点，阐明基本内容（50字内）
3. **核心主题** - 请根据视频文案，提取其核心论点、因果逻辑与关键数据，生成一份无冗余、可读性强的逻辑报告
4. **详细大纲** - 根据文案给视频分段落，分段总结详细内容，要求逻辑缜密
5. **内容标签** - 高频词云（5-10个标签）
6. **资源汇总** - 提取视频里提到的书籍、链接、工具
7. **总结评价** - 价值评估、适合人群、推荐指数

**总结输出格式**：
```markdown
# 视频内容总结

---

## 📋 基础信息

| 项目 | 内容 |
|------|------|
| 标题 | [视频标题] |
| 作者 | [UP主/频道名称] |
| 视频时长 | [时长] |
| 发布时间 | [日期] |
| 视频来源 | [URL] |
| 总结时间 | [日期] |

---


## 🎯 一句话总结

[极致精简的核心观点，阐明基本内容（50字内）]

---

## 📌 核心主题

[请根据视频文案，提取其核心论点、因果逻辑与关键数据，生成一份无冗余、可读性强的逻辑报告]

---


---

## 📝 详细大纲

[根据文案给视频分段落，分段总结详细内容，要求逻辑缜密]


---

## 🏷️ 内容标签

[标签1] [标签2] [标签3] [标签4] [标签5] [标签6] [标签7] [标签8]

---

## 📚 资源汇总

### 书籍推荐
- [书名] - [简短描述]
- [书名] - [简短描述]

### 工具/软件
- [工具名] - [用途/链接]
- [工具名] - [用途/链接]

### 学习资源
- [资源名称] - [简短说明]
- [资源名称] - [简短说明]

### 其他链接
- [链接/名称] - [简短说明]

---

## 💡 总结评价

**价值评估**：[视频的独特价值和贡献]

**适合人群**：[推荐给谁观看]

**推荐指数**：⭐⭐⭐⭐⭐ (5/5)

**观看建议**：[是否需要预备知识、建议观看方式等]
```

## 完成后输出

完成所有阶段后，向用户播报：

```
✅ 视频内容总结完成！

📁 输出目录: <当前工作目录>

📄 生成文件:
  - <视频标题>.mp4         (原始视频)
  - <视频标题>.srt         (原始字幕)
  - <视频标题>_文字稿.md    (校正后文字稿)
  - <视频标题>_总结.md      (智能总结)

🔗 快速打开:
  [文字稿](<文字稿路径>)
  [总结](<总结路径>)
```

## 参考文件

- [download_douyin.py](scripts/download_douyin.py): 抖音视频下载脚本
- [extract_subtitle_funasr.py](scripts/extract_subtitle_funasr.py): 智能字幕提取脚本（FunASR + RapidOCR）
- [extract_subtitle.py](scripts/extract_subtitle.py): 字幕提取脚本（Whisper）
- [transcribe_audio.py](scripts/transcribe_audio.py): 音频转录脚本
- [correct_text.py](scripts/correct_text.py): 文稿校正脚本（同音字修正、专业术语修正）
- [rename_with_title.py](scripts/rename_with_title.py): 文件重命名脚本（根据视频标题）
- [summary_prompt.md](references/summary_prompt.md): 视频总结提示词模板
