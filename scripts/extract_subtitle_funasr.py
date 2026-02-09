#!/usr/bin/env python3
"""
智能字幕提取脚本 (FunASR + RapidOCR) - 优化版
流程：内嵌字幕 → 烧录字幕检测(OCR) → FunASR语音转录 → 质量检测 → Whisper回退
"""

import subprocess
import sys
import os
import tempfile
from pathlib import Path
import json
import re
import shutil


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
                    title = re.sub(r'[<>:"/\\|?*]', '', title)
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
            title = re.sub(r'[<>:"/\\|?*]', '', title)
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
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        print("⚠️ RapidOCR 未安装，跳过烧录字幕检测")
        return False
    
    # 截取多个时间点的帧进行检测
    timestamps = ["00:01:00", "00:03:00", "00:05:00"]
    
    for ts in timestamps:
        frame_path = capture_frame(video_path, ts)
        if not frame_path:
            continue
        
        try:
            ocr = RapidOCR()
            result, _ = ocr(frame_path)
            
            if result and len(result) > 0:
                # 检测到文字
                os.remove(frame_path)
                return True
        except Exception as e:
            print(f"⚠️ OCR 检测失败: {e}")
        finally:
            if os.path.exists(frame_path):
                os.remove(frame_path)
    
    return False


def extract_burned_subtitle_ocr(video_path: str, output_srt: str) -> bool:
    """
    使用OCR提取烧录字幕
    """
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        print("⚠️ RapidOCR 未安装，无法提取烧录字幕")
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
        
        # 每5秒采样一帧
        ocr = RapidOCR()
        subtitles = []
        
        for i in range(0, int(duration), 5):
            frame_path = capture_frame(video_path, f"00:00:{i:02d}")
            if not frame_path:
                continue
            
            try:
                result, _ = ocr(frame_path)
                if result and len(result) > 0:
                    text = " ".join([line[1] for line in result])
                    if text.strip():
                        start_time = i
                        end_time = i + 5
                        subtitles.append((start_time, end_time, text))
            except Exception as e:
                print(f"⚠️ OCR 识别失败: {e}")
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


def extract_with_funasr(video_path: str, output_srt: str) -> bool:
    """
    使用FunASR进行语音转录 (优化版)
    """
    try:
        from funasr import AutoModel
    except ImportError:
        print("⚠️ FunASR 未安装，请先安装: pip install funasr modelscope")
        return False
    
    try:
        print(f"🎤 使用 FunASR Nano 进行语音转录...")
        print(f"   模型: iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
        
        # 加载模型 (优化配置)
        model = AutoModel(
            model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            disable_update=True
        )
        
        # 转录 (优化参数)
        print(f"   正在转录...")
        res = model.generate(
            input=video_path,
            batch_size_s=60,  # 减小batch_size以提高质量
            disable_pbar=False,  # 显示进度
            sentence_timestamp=True  # 启用句子级时间戳
        )
        
        # 保存为SRT格式 (优化处理逻辑)
        subtitle_count = 0
        with open(output_srt, 'w', encoding='utf-8') as f:
            if isinstance(res, list) and len(res) > 0:
                for idx, item in enumerate(res, 1):
                    # 优先使用 sentence_info
                    if "sentence_info" in item and item["sentence_info"]:
                        for seg in item["sentence_info"]:
                            start = seg.get("start", 0) / 1000  # 转换毫秒为秒
                            end = seg.get("end", 0) / 1000  # 转换毫秒为秒
                            text = seg.get("text", "").strip()
                            
                            # 只保存有内容的字幕
                            if text and len(text) > 1:
                                f.write(f"{idx}\n")
                                f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
                                f.write(f"{text}\n\n")
                                subtitle_count += 1
                                idx += 1
                    else:
                        # 回退到简单转录
                        start = item.get("start", 0) / 1000  # 转换毫秒为秒
                        end = item.get("end", 0) / 1000  # 转换毫秒为秒
                        text = item.get("text", "").strip()
                        
                        if text and len(text) > 1:
                            f.write(f"{idx}\n")
                            f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
                            f.write(f"{text}\n\n")
                            subtitle_count += 1
        
        print(f"✅ FunASR 转录完成: {subtitle_count} 条字幕")
        return subtitle_count > 0
        
    except Exception as e:
        print(f"❌ FunASR 转录失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_subtitle_quality(srt_path: str) -> dict:
    """
    检查字幕质量
    """
    try:
        import pysrt
    except ImportError:
        print("⚠️ pysrt 未安装，跳过质量检测")
        return {"has_errors": False, "count": 0}
    
    try:
        subs = pysrt.open(srt_path)
        
        stats = {
            "count": len(subs),
            "avg_length": 0,
            "has_errors": False,
            "repetition_rate": 0,
            "max_consecutive_same": 0,
            "empty_count": 0
        }
        
        if len(subs) == 0:
            stats["has_errors"] = True
            stats["error_reason"] = "无字幕"
            return stats
        
        # 计算平均长度
        total_length = sum(len(sub.text.strip()) for sub in subs)
        stats["avg_length"] = total_length / len(subs) if len(subs) > 0 else 0
        
        # 统计空字幕
        empty_count = sum(1 for sub in subs if len(sub.text.strip()) < 2)
        stats["empty_count"] = empty_count
        
        # 检查重复
        texts = [sub.text.strip() for sub in subs if len(sub.text.strip()) > 1]
        if len(texts) > 0:
            unique_texts = set(texts)
            stats["repetition_rate"] = 1 - (len(unique_texts) / len(texts))
        
        # 检查连续重复
        max_consecutive = 1
        current_consecutive = 1
        for i in range(1, len(subs)):
            if subs[i].text.strip() == subs[i-1].text.strip() and len(subs[i].text.strip()) > 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1
        stats["max_consecutive_same"] = max_consecutive
        
        # 质量判断
        error_reasons = []
        
        if stats["count"] < 10:
            stats["has_errors"] = True
            error_reasons.append(f"字幕条数过少 ({stats['count']})")
        
        if stats["repetition_rate"] > 0.7:
            stats["has_errors"] = True
            error_reasons.append(f"重复率过高 ({stats['repetition_rate']:.1%})")
        
        if stats["max_consecutive_same"] > 10:
            stats["has_errors"] = True
            error_reasons.append(f"连续重复过多 ({stats['max_consecutive_same']}次)")
        
        if stats["avg_length"] < 2:
            stats["has_errors"] = True
            error_reasons.append(f"平均长度过短 ({stats['avg_length']:.1f}字)")
        
        if stats["empty_count"] > stats["count"] * 0.5:
            stats["has_errors"] = True
            error_reasons.append(f"空字幕过多 ({stats['empty_count']}/{stats['count']})")
        
        stats["error_reason"] = ", ".join(error_reasons) if error_reasons else "质量良好"
        
        return stats
        
    except Exception as e:
        print(f"⚠️ 质量检测失败: {e}")
        return {"has_errors": True, "error_reason": f"检测异常: {e}"}


def extract_with_whisper_fallback(video_path: str, output_srt: str) -> bool:
    """
    使用Whisper作为回退方案
    """
    try:
        import whisper
    except ImportError:
        print("⚠️ Whisper 未安装，无法回退")
        return False
    
    try:
        print(f"🔄 回退到 Whisper 进行转录...")
        
        # 检测CUDA可用性
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 加载模型
        whisper_model = whisper.load_model("large", device=device)
        
        # 转录
        result = whisper_model.transcribe(
            video_path,
            language="zh",
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
        
        print(f"✅ Whisper 回退成功: {len(result['segments'])} 条字幕")
        return True
        
    except Exception as e:
        print(f"❌ Whisper 回退失败: {e}")
        return False


def smart_subtitle_extraction(video_path: str, output_srt: str) -> tuple[bool, str]:
    """
    智能字幕提取（三层优先级 + 质量检测 + 自动回退）
    """
    print("==================================================")
    print("🎬 智能字幕提取 (RapidOCR + FunASR + Whisper回退)")
    print("==================================================")
    print(f"视频: {video_path}\n")
    
    # 第一层：检查内嵌字幕
    print("步骤 1/4: 检查内嵌字幕...")
    has_embedded, result = check_embedded_subtitle(video_path)
    if has_embedded:
        print(f"✅ 检测到内嵌字幕")
        if result != output_srt:
            shutil.copy(result, output_srt)
        return True, "embedded"
    else:
        print(f"⚠️ {result}")
    
    # 第二层：检测烧录字幕
    print("\n步骤 2/4: 检测烧录字幕 (RapidOCR)...")
    if detect_burned_subtitle(video_path):
        print("✅ 检测到烧录字幕")
        if extract_burned_subtitle_ocr(video_path, output_srt):
            return True, "ocr"
    else:
        print("⚠️ 未检测到烧录字幕")
    
    # 第三层：使用FunASR
    print("\n步骤 3/4: 使用 FunASR Nano 语音转录...")
    if extract_with_funasr(video_path, output_srt):
        # 第四层：质量检测
        print("\n步骤 4/4: 检测字幕质量...")
        quality = check_subtitle_quality(output_srt)
        
        print(f"   字幕条数: {quality['count']}")
        print(f"   平均长度: {quality['avg_length']:.1f}字")
        print(f"   重复率: {quality['repetition_rate']:.1%}")
        print(f"   质量评估: {quality['error_reason']}")
        
        if quality["has_errors"]:
            print(f"\n⚠️ FunASR 质量不佳,自动回退到 Whisper...")
            # 删除低质量字幕
            if os.path.exists(output_srt):
                os.remove(output_srt)
            
            # 回退到 Whisper
            if extract_with_whisper_fallback(video_path, output_srt):
                return True, "whisper_fallback"
            else:
                return False, "whisper_fallback_failed"
        else:
            return True, "funasr"
    else:
        # FunASR失败,直接回退到Whisper
        print(f"\n⚠️ FunASR 转录失败,回退到 Whisper...")
        if extract_with_whisper_fallback(video_path, output_srt):
            return True, "whisper_fallback"
        else:
            return False, "all_failed"
    
    return False, "unknown_error"


def main():
    """
    主函数
    """
    if len(sys.argv) < 2:
        print("用法: python extract_subtitle_funasr.py <视频路径> [输出SRT路径]")
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
        print(f"\n❌ 字幕提取失败: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
