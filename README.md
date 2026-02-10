# Video Summarizer

视频内容快速总结工具。提取视频核心信息、生成结构化总结（基础信息/一句话总结/核心主题/关键要点/详细大纲/标签/资源汇总/评价）。

## 功能特性

- 🎬 **多平台支持**：支持 B站、YouTube、抖音等主流视频平台
- 🤖 **智能字幕提取**：三层优先级提取策略（内嵌字幕 → 烧录字幕 OCR → FunASR 语音转录）
- ✍️ **文稿自动校正**：修正同音字错误、专业术语、补充标点符号
- 📝 **结构化总结**：生成包含基础信息、核心主题、详细大纲、资源汇总等维度的完整总结
- 🔄 **文件自动重命名**：根据视频标题批量重命名所有相关文件

## 使用场景

- 快速了解视频内容
- 提取视频要点和大纲
- 查找视频中的资源（书籍、工具、链接等）
- 视频内容归档和整理

## 技术栈

- **yt-dlp**：视频下载
- **FunASR Nano**：中文语音转录（阿里开源，轻量且效果好）
- **RapidOCR (ONNX)**：烧录字幕识别
- **Python 3.7+**：核心开发语言

## 安装依赖

```bash
# 基础依赖
pip install yt-dlp pysrt python-dotenv requests

# FunASR（中文语音转录）
pip install funasr modelscope

# RapidOCR（烧录字幕识别）
pip install rapidocr-onnxruntime

# Whisper（备选方案，英文内容推荐）
pip install openai-whisper
```

## 工作流程

1. **下载视频**：自动识别平台并下载视频
2. **智能字幕提取**：三层优先级自动选择最佳提取方案
3. **文稿校正**：基于上下文语义进行智能校正
4. **文件重命名**：根据视频标题批量重命名
5. **生成总结**：基于校正后的文字稿生成结构化总结

## 项目说明

本项目是基于 [video-copy-analyzer](https://github.com/ALBEDO-TABAI/video-copy-analyzer) 项目进行二次开发的版本。

**主要改进和优化：**

1. **优化字幕提取流程**：采用三层优先级智能提取策略（内嵌字幕 → RapidOCR 烧录字幕识别 → FunASR 语音转录）
2. **增强文稿校正能力**：改进同音字修正、专业术语识别和标点符号补充
3. **完善总结结构**：新增核心主题、详细大纲、资源汇总等结构化内容维度
4. **添加文件重命名功能**：支持根据视频标题批量重命名相关文件
5. **优化中文语音转录**：采用 FunASR Nano 模型，针对中文语音优化，效果优于 Whisper
6. **简化依赖安装**：整理和优化了 Python 依赖包的安装流程

**感谢原项目作者 ALBEDO-TABAI 的开源贡献！**

## 致谢

- 原项目：[video-copy-analyzer](https://github.com/ALBEDO-TABAI/video-copy-analyzer) by [ALBEDO-TABAI](https://github.com/ALBEDO-TABAI)
- FunASR: 阿里巴巴达摩院语音技术实验室
- RapidOCR: 基于 PaddleOCR 优化的 ONNX 版本

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue 或 Pull Request。
