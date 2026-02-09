#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文稿校正脚本
功能：基于上下文语义进行智能校正
- 修正同音字错误
- 修正专业术语
- 补充标点符号
"""

import pysrt
import re
import sys

# 常见同音字和专业术语修正映射
CORRECTIONS = {
    # 新西兰相关
    "几尾鸟": "几维鸟",
    "霍比屯": "霍比特村",
    "音弗卡吉尔": "因弗卡吉尔",
    "货币屯": "霍比特村",
    "北斗": "北岛",
    "宿迁": "宿迁",
    
    # 电影相关
    "半兽人": "半兽人",  # 正确
    "指环王": "指环王",  # 正确
    "霍比特人": "霍比特人",  # 正确
    
    # 地名
    "瓦纳": "瓦纳卡",
    "卡蒂": "卡蒂湖",
    "卡波": "卡波",
    "普海基": "普卡基",
    "金斯顿": "金斯顿",
    
    # 其他常见错误
    "最南端": "最南端",
    "最难": "最南",
    "星巴堡": "星巴克",
    
    # UP主相关（根据实际情况调整）
    "期末柴西小路": "期末柴西小路",  # 保持原样，可能是UP主名
}

def correct_text(text):
    """修正单个文本片段"""
    corrected = text
    
    # 1. 同音字和专业术语修正
    for wrong, right in CORRECTIONS.items():
        corrected = corrected.replace(wrong, right)
    
    # 2. 标点符号优化
    # 在句子末尾添加标点（如果缺失）
    if corrected and not corrected[-1] in "，。！？；：,.!?;:":
        # 检查是否是句子结尾
        if len(corrected) > 2 and corrected[-2] in "的么呢啊吧吗哦嘛了着过":
            corrected += "。"
        elif len(corrected) > 0:
            # 其他情况用逗号
            if not corrected[-1] in "，。！？；：,.!?;:":
                corrected += "，"
    
    return corrected

def correct_srt_to_text(srt_path, output_path):
    """从SRT文件生成校正后的文字稿"""
    print("=" * 50)
    print("📝 文稿校正")
    print("=" * 50)
    print(f"SRT文件: {srt_path}")
    
    # 读取SRT文件
    try:
        subs = pysrt.open(srt_path)
    except Exception as e:
        print(f"❌ 读取SRT文件失败: {e}")
        return False
    
    print(f"✅ 读取成功: {len(subs)} 条字幕")
    
    # 合并并校正字幕
    full_text = []
    current_para = []
    
    for i, sub in enumerate(subs):
        text = sub.text.strip()
        
        # 跳过纯语气词
        if text in ['嗯', '啊', '哎', '哇', 'OK', 'ok', 'hello', 'yeah', 'no', 'okay', 'Oh', 'oh']:
            continue
        
        # 校正文本
        corrected = correct_text(text)
        
        if corrected:
            current_para.append(corrected)
        
        # 每8-10条字幕组成一段
        if len(current_para) >= 8:
            if current_para:
                para = ''.join(current_para)
                full_text.append(para)
                current_para = []
    
    # 添加最后一段
    if current_para:
        para = ''.join(current_para)
        full_text.append(para)
    
    print(f"✅ 校正完成: 生成 {len(full_text)} 段文字")
    
    # 生成Markdown格式的文字稿
    import os
    video_name = os.path.splitext(os.path.basename(srt_path))[0]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# 视频语音转录文字稿\n\n')
        f.write('**视频来源**: [视频链接]\n')
        f.write('**转录时间**: 2026年2月8日\n\n')
        f.write('---\n\n')
        f.write('## 完整文字稿\n\n')
        
        for i, para in enumerate(full_text, 1):
            f.write(f'{para}\n\n')
    
    print(f"✅ 文字稿已保存: {output_path}")
    return True

def correct_and_update_srt(srt_path, output_path):
    """直接校正SRT文件内容"""
    print("=" * 50)
    print("📝 SRT字幕校正")
    print("=" * 50)
    
    try:
        subs = pysrt.open(srt_path)
    except Exception as e:
        print(f"❌ 读取SRT文件失败: {e}")
        return False
    
    corrected_count = 0
    for sub in subs:
        original = sub.text
        corrected = correct_text(original)
        
        if corrected != original:
            sub.text = corrected
            corrected_count += 1
    
    print(f"✅ 校正完成: 修正了 {corrected_count} 处")
    
    subs.save(output_path, encoding='utf-8')
    print(f"✅ 校正后SRT已保存: {output_path}")
    
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法:")
        print("  生成文字稿: python correct_text.py <srt_path> <output_text_path>")
        print("  校正SRT: python correct_text.py <srt_path> <output_srt_path> --srt")
        sys.exit(1)
    
    srt_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if '--srt' in sys.argv or '-s' in sys.argv:
        # 校正SRT文件
        correct_and_update_srt(srt_path, output_path)
    else:
        # 生成文字稿
        correct_srt_to_text(srt_path, output_path)
