#!/usr/bin/env python3
"""
智能字幕提取脚本
流程：内嵌字幕 → 烧录字幕检测(OCR) → Whisper语音转录
"""

import subprocess
import sys
import os
import tempfile
from pathlib import Path
import json
import re


def get_video_title(video_path: str) -> str:
    """
    从视频文件名或元数据中提取标题
    优先从文件名提取,如果没有则使用默认名称
    """
    # 尝试从文件名中提取
    filename = os.path.basename(video_path)
    name_without_ext = os.path.splitext(filename)[0]

    # 如果文件名是BV号格式,尝试从网络获取标题
    if re.match(r'^BV[a-zA-Z0-9]+$', name_without_ext):
        try:
            import yt_dlp
            # 从BV号构造B站URL
            url = f'https://www.bilibili.com/video/{name_without_ext}/'
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', '')
                if title:
                    # 清理标题中的非法字符
                    title = re.sub(r'[<>:"/\|?*]', '', title)
                    return title
        except:
            pass

    # 尝试从视频元数据获取标题
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        title = data.get("format", {}).get("tags", {}).get("title", "")
        if title:
            title = re.sub(r'[<>:"/\|?*]', '', title)
            return title
    except:
        pass

    # 返回处理后的文件名
    return name_without_ext

def sanitize_filename(filename: str) -> str:
    """
    清理文件名,移除非法字符
    """
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 移除前后空格
    filename = filename.strip()
    # 限制长度
    if len(filename) > 100:
        filename = filename[:100]
    return filename if filename else "video"


def check_embedded_subtitle(video_path: str) -> tuple[bool, str]:
    """
    检查视频是否包含内嵌字幕流
    返回: (是否有内嵌字幕, 字幕文件路径或错误信息)
    """
    try:
        # 使用 ffprobe 检查字幕流
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        streams = data.get("streams", [])
        subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]
        
        if subtitle_streams:
            # 提取第一个字幕流
            output_srt = video_path.rsplit(".", 1)[0] + "_embedded.srt"
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-map", f"0:s:0", output_srt
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return True, output_srt
        else:
            return False, "无内嵌字幕流"
    except Exception as e:
        return False, f"检测失败: {e}"


def capture_frame(video_path: str, timestamp: str = "00:00:05") -> str:
    """
    截取视频指定时间的帧
    默认截取第5秒（通常有字幕出现）
    """
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        output_path = tmp.name
    
    try:
        cmd = [
            "ffmpeg", "-y", "-ss", timestamp, "-i", video_path,
            "-frames:v", "1", "-q:v", "2", output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except Exception as e:
        if os.path.exists(output_path):
            os.remove(output_path)
        return ""


def detect_burned_subtitle(video_path: str) -> bool:
    """
    检测视频是否包含烧录字幕
    通过采样帧进行OCR识别
    """
    try:
        import paddleocr
    except ImportError:
        print("⚠️ PaddleOCR 未安装，跳过烧录字幕检测")
        return False
    
    # 截取多个时间点的帧进行检测
    timestamps = ["00:01:00", "00:03:00", "00:05:00"]
    
    for ts in timestamps:
        frame_path = capture_frame(video_path, ts)
        if not frame_path:
            continue
        
        try:
            ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang="ch")
            result = ocr.ocr(frame_path, cls=True)
            
            if result and result[0]:
                # 检测到文字
                os.remove(frame_path)
                return True
        except:
            pass
        finally:
            if os.path.exists(frame_path):
                os.remove(frame_path)
    
    return False


def extract_burned_subtitle_ocr(video_path: str, output_srt: str) -> bool:
    """
    使用OCR提取烧录字幕
    """
    try:
        import paddleocr
    except ImportError:
        print("⚠️ PaddleOCR 未安装，无法提取烧录字幕")
        return False
    
    try:
        # 获取视频时长
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0))
        
        if duration <= 0:
            return False
        
        # 每秒采样一帧
        ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang="ch")
        subtitles = []
        
        for i in range(0, int(duration), 1):
            frame_path = capture_frame(video_path, f"00:00:{i:02d}")
            if not frame_path:
                continue
            
            try:
                result = ocr.ocr(frame_path, cls=True)
                if result and result[0]:
                    text = " ".join([line[1][0] for line in result[0]])
                    if text.strip():
                        start_time = i
                        end_time = i + 2  # 每条字幕持续2秒
                        subtitles.append((start_time, end_time, text))
            except:
                pass
            finally:
                if os.path.exists(frame_path):
                    os.remove(frame_path)
        
        # 保存为SRT格式
        with open(output_srt, 'w', encoding='utf-8') as f:
            for idx, (start, end, text) in enumerate(subtitles, 1):
                f.write(f"{idx}\n")
                f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
                f.write(f"{text}\n\n")
        
        return True
    except Exception as e:
        print(f"⚠️ OCR 提取失败: {e}")
        return False


def format_timestamp(seconds: float) -> str:
    """
    将秒数转换为SRT时间戳格式
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def extract_with_whisper(video_path: str, output_srt: str, model: str = "large") -> bool:
    """
    使用Whisper进行语音转录
    """
    try:
        import whisper
    except ImportError:
        print("⚠️ Whisper 未安装，请先安装: pip install openai-whisper")
        return False
    
    try:
        print(f"🎤 使用 Whisper {model} 进行语音转录...")
        
        # 检测CUDA可用性
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            print("⚠️ CUDA 不可用，使用 CPU（速度较慢）")
        
        # 加载模型
        whisper_model = whisper.load_model(model, device=device)
        
        # 转录
        result = whisper_model.transcribe(
            video_path,
            language="zh",  # 默认中文
            verbose=False
        )
        
        # 保存为SRT格式
        with open(output_srt, 'w', encoding='utf-8') as f:
            for idx, segment in enumerate(result["segments"], 1):
                start = segment["start"]
                end = segment["end"]
                text = segment["text"].strip()
                f.write(f"{idx}\n")
                f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
                f.write(f"{text}\n\n")
        
        print(f"✅ Whisper 转录完成: {len(result['segments'])} 条字幕")
        return True
    except Exception as e:
        print(f"❌ Whisper 转录失败: {e}")
        return False


def smart_subtitle_extraction(video_path: str, output_srt: str) -> tuple[bool, str]:
    """
    智能字幕提取（三层优先级）
    """
    print("==================================================")
    print("🎬 智能字幕提取")
    print("==================================================")
    print(f"视频: {video_path}\n")
    
    # 第一层：检查内嵌字幕
    print("步骤 1/3: 检查内嵌字幕...")
    has_embedded, result = check_embedded_subtitle(video_path)
    if has_embedded:
        print(f"✅ 检测到内嵌字幕")
        if result != output_srt:
            shutil.copy(result, output_srt)
        return True, "embedded"
    else:
        print(f"⚠️ {result}")
    
    # 第二层：检测烧录字幕
    print("\n步骤 2/3: 检测烧录字幕...")
    if detect_burned_subtitle(video_path):
        print("✅ 检测到烧录字幕")
        if extract_burned_subtitle_ocr(video_path, output_srt):
            return True, "ocr"
    else:
        print("⚠️ 未检测到烧录字幕")
    
    # 第三层：使用Whisper
    print("\n步骤 3/3: 使用 Whisper 语音转录...")
    if extract_with_whisper(video_path, output_srt, "large"):
        return True, "whisper"
    
    return False, "failed"


def main():
    """
    主函数
    """
    import shutil
    
    if len(sys.argv) < 2:
        print("用法: python extract_subtitle.py <视频路径> [输出SRT路径]")
        print("注意: 如果不指定输出路径,将自动使用视频标题作为文件名")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        sys.exit(1)
    
    # 确定输出路径
    if len(sys.argv) >= 3:
        output_srt = sys.argv[2]
    else:
        # 自动生成输出文件名
        video_dir = os.path.dirname(video_path)
        if not video_dir:
            video_dir = "."
        
        title = get_video_title(video_path)
        title = sanitize_filename(title)
        output_srt = os.path.join(video_dir, f"{title}.srt")
    
    success, mode = smart_subtitle_extraction(video_path, output_srt)
    
    if success:
        print(f"\n✅ 字幕提取成功！")
        print(f"   模式: {mode}")
        print(f"   输出: {output_srt}")
        sys.exit(0)
    else:
        print(f"\n❌ 字幕提取失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
