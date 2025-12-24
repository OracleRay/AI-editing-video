#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
音频合并工具
使用ffmpeg合并多条音频为一条音频
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from utils.config_loader import get_config
from utils.loggers import get_logger

# 加载配置和日志
config = get_config()
logger = get_logger('concat_audio', silent=True)


def concat_audio_files(audio_files, output_file):
    """
    使用ffmpeg合并多条音频为一条音频
    
    Args:
        audio_files: 音频文件路径列表（按顺序）
        output_file: 输出音频文件路径
    
    Returns:
        成功返回True，失败返回False
    
    Raises:
        ValueError: 音频文件列表为空
        FileNotFoundError: ffmpeg不存在或音频文件不存在
    
    Examples:
        >>> audio_files = ["audio1.mp3", "audio2.mp3", "audio3.mp3"]
        >>> success = concat_audio_files(audio_files, "merged_audio.mp3")
        >>> if success:
        ...     print("合并成功")
    """
    if not audio_files:
        raise ValueError("音频文件列表不能为空")
    
    # 获取ffmpeg路径
    ffmpeg_path = config.get_absolute_path(config.get('ffmpeg.ffmpeg_path'))
    if not os.path.exists(ffmpeg_path):
        raise FileNotFoundError(f"未找到ffmpeg: {ffmpeg_path}")
    
    # 确保所有音频文件存在
    for audio_file in audio_files:
        audio_abs_path = config.get_absolute_path(audio_file)
        if not os.path.exists(audio_abs_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_abs_path}")
    
    # 创建临时拼接列表文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        concat_list = f.name
        for audio_file in audio_files:
            # 使用绝对路径，避免路径问题
            audio_abs_path = config.get_absolute_path(audio_file)
            abs_path = os.path.abspath(audio_abs_path).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")
    
    try:
        # 确保输出目录存在
        output_abs_path = config.get_absolute_path(output_file)
        output_dir = os.path.dirname(output_abs_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Windows 下隐藏命令行窗口
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        
        # 使用ffmpeg合并音频
        # 对于音频，不能直接用 -c copy，需要重新编码以确保兼容性
        # 使用MP3编码器（libmp3lame）以匹配输出文件格式
        cmd = [
            ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-acodec", "libmp3lame",
            "-b:a", "192k",
            "-ar", "44100",  # 统一采样率为44.1kHz
            "-ac", "2",      # 统一为立体声
            output_abs_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=creation_flags
        )
        
        if result.returncode != 0:
            logger.error(f"合并音频失败: {result.stderr}")
            return False
        
        return True
    finally:
        # 清理临时文件
        try:
            os.unlink(concat_list)
        except Exception:
            pass


if __name__ == "__main__":
    # 测试示例
    import sys
    if len(sys.argv) < 3:
        print("用法: python concat_audio.py <输出文件> <音频文件1> [音频文件2] ...")
        sys.exit(1)
    
    output_file = sys.argv[1]
    audio_files = sys.argv[2:]
    
    try:
        success = concat_audio_files(audio_files, output_file)
        if success:
            print(f"✅ 合并成功: {output_file}")
        else:
            print("❌ 合并失败")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

