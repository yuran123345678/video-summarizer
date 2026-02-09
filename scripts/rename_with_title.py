#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据视频标题重命名文件
"""

import subprocess
import sys
import os
import re

def get_video_title(url):
    """获取视频标题"""
    try:
        result = subprocess.run(
            ['yt-dlp', '--get-title', url],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            title = result.stdout.strip()
            # 清理文件名中的非法字符
            title = re.sub(r'[<>:"/\\|?*]', '', title)
            # 限制长度
            if len(title) > 100:
                title = title[:100]
            return title
    except Exception as e:
        print(f"⚠️ 获取视频标题失败: {e}")
    return None

def rename_files(old_pattern, new_title, base_dir="."):
    """重命名文件"""
    files_to_rename = []
    
    # 查找匹配的文件
    for filename in os.listdir(base_dir):
        if old_pattern in filename:
            old_path = os.path.join(base_dir, filename)
            
            # 生成新文件名
            if filename == old_pattern:
                # 完全匹配
                new_filename = new_title + os.path.splitext(filename)[1]
            else:
                # 部分匹配，替换部分
                new_filename = filename.replace(old_pattern, new_title)
            
            new_path = os.path.join(base_dir, new_filename)
            
            files_to_rename.append((old_path, new_path, filename, new_filename))
    
    if not files_to_rename:
        print(f"⚠️ 未找到匹配 '{old_pattern}' 的文件")
        return False
    
    print("=" * 50)
    print("📁 文件重命名")
    print("=" * 50)
    print(f"旧模式: {old_pattern}")
    print(f"新标题: {new_title}")
    print()
    
    # 执行重命名
    for old_path, new_path, old_name, new_name in files_to_rename:
        try:
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                print(f"✅ {old_name} → {new_name}")
            else:
                print(f"⚠️ 文件不存在: {old_name}")
        except Exception as e:
            print(f"❌ 重命名失败 {old_name}: {e}")
    
    print()
    print(f"✅ 共重命名 {len(files_to_rename)} 个文件")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法:")
        print("  根据URL获取标题并重命名: python rename_with_title.py <video_url> [old_pattern]")
        print("  使用自定义标题重命名: python rename_with_title.py --title \"标题\" [old_pattern]")
        sys.exit(1)
    
    base_dir = os.getcwd()
    
    if sys.argv[1] == '--title':
        # 使用自定义标题
        new_title = sys.argv[2]
        old_pattern = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        # 从URL获取标题
        url = sys.argv[1]
        old_pattern = sys.argv[2] if len(sys.argv) > 2 else None
        
        print(f"正在获取视频标题: {url}")
        new_title = get_video_title(url)
        
        if not new_title:
            print("❌ 无法获取视频标题")
            sys.exit(1)
        
        print(f"✅ 获取到标题: {new_title}")
    
    # 如果没有指定旧模式，尝试从当前目录推断
    if not old_pattern:
        # 查找视频或SRT文件
        for filename in os.listdir(base_dir):
            if filename.endswith(('.mp4', '.srt', '.mkv', '.avi')):
                old_pattern = os.path.splitext(filename)[0]
                break
    
    if not old_pattern:
        print("❌ 无法确定要重命名的文件模式")
        sys.exit(1)
    
    rename_files(old_pattern, new_title, base_dir)
