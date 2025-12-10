#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
解说音频转字幕工具
将包含多个 mp3 音频文件的文件夹转换为对应的 srt 字幕文件
"""

import os
import sys
from pathlib import Path
from typing import List

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.audio_to_subtitles import transcribe_audio, create_srt, API_URL, API_KEY
from utils.config_loader import get_config, get_workspace_path
from utils.loggers import get_logger

# 初始化配置和日志记录器
config = get_config()
logger = get_logger('gen_jieShuo_srt', silent=True)


def batch_convert_mp3_to_srt(audio_dir: str, output_base_dir: str = None) -> str:
    """
    批量将音频文件转换为 SRT 字幕文件
    
    Args:
        audio_dir: 包含多个 mp3 文件的目录路径
        output_base_dir: 输出基础目录，默认为 workspace/srt_files/subtitles/
    
    Returns:
        输出目录路径
        
    Raises:
        FileNotFoundError: 音频目录不存在
        ValueError: 目录中没有找到 mp3 文件
    """
    # 转换为 Path 对象
    audio_path = Path(audio_dir)
    
    # 检查音频目录是否存在
    if not audio_path.exists():
        raise FileNotFoundError(f"音频目录不存在: {audio_dir}")
    
    if not audio_path.is_dir():
        raise ValueError(f"路径不是目录: {audio_dir}")
    
    # 获取所有 mp3 文件并排序
    mp3_files = sorted(audio_path.glob("*.mp3"))
    
    if not mp3_files:
        raise ValueError(f"目录中没有找到 mp3 文件: {audio_dir}")
    
    logger.info("=" * 60)
    logger.info(f"🎵 开始批量转换音频到字幕")
    logger.info(f"   音频目录: {audio_path}")
    logger.info(f"   找到 {len(mp3_files)} 个 mp3 文件")
    logger.info("=" * 60)
    
    # 确定输出目录
    if output_base_dir is None:
        output_base_dir = get_workspace_path("srt_files/subtitles")
    else:
        output_base_dir = Path(output_base_dir)
    
    # 创建与音频文件夹同名的子目录
    folder_name = audio_path.name
    output_dir = output_base_dir / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📁 输出目录: {output_dir}")
    logger.info("")
    
    # 批量处理每个音频文件
    success_count = 0
    failed_files = []
    
    for idx, mp3_file in enumerate(mp3_files, start=1):
        try:
            # 生成对应的 srt 文件名（保持原文件名，只改扩展名）
            srt_filename = mp3_file.stem + ".srt"
            srt_path = output_dir / srt_filename
            
            # 检查 srt 文件是否已存在
            if srt_path.exists():
                logger.info(f"[{idx}/{len(mp3_files)}] ⏭️  跳过（已存在）: {mp3_file.name}")
                success_count += 1
                continue
            
            logger.info(f"[{idx}/{len(mp3_files)}] 🔄 转录中: {mp3_file.name}")
            
            # 调用 API 转录音频
            transcription_result = transcribe_audio(str(mp3_file), API_URL, API_KEY)
            
            # 生成 SRT 文件
            create_srt(transcription_result, str(srt_path))
            
            logger.info(f"[{idx}/{len(mp3_files)}] ✅ 成功: {mp3_file.name} -> {srt_filename}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"[{idx}/{len(mp3_files)}] ❌ 失败: {mp3_file.name}")
            logger.error(f"   错误信息: {str(e)}")
            failed_files.append(mp3_file.name)
    
    # 输出总结
    logger.info("=" * 60)
    logger.info("📊 批量转换完成")
    logger.info(f"   成功: {success_count}/{len(mp3_files)}")
    logger.info(f"   失败: {len(failed_files)}/{len(mp3_files)}")
    
    if failed_files:
        logger.warning("   失败的文件:")
        for filename in failed_files:
            logger.warning(f"      - {filename}")
    
    logger.info(f"   输出目录: {output_dir}")
    logger.info("=" * 60)
    
    return str(output_dir)


def get_srt_files_from_audio_dir(audio_dir: str, output_base_dir: str = None) -> List[str]:
    """
    根据音频目录获取对应的 srt 字幕文件列表
    如果字幕文件不存在，则先进行转换
    
    Args:
        audio_dir: 包含多个 mp3 文件的目录路径
        output_base_dir: 输出基础目录，默认为 workspace/srt_files/subtitles/
    
    Returns:
        srt 文件路径列表（按文件名排序）
    """
    # 先执行批量转换（会自动跳过已存在的文件）
    output_dir = batch_convert_mp3_to_srt(audio_dir, output_base_dir)
    
    # 获取所有生成的 srt 文件
    output_path = Path(output_dir)
    srt_files = sorted(output_path.glob("*.srt"))
    
    return [str(f) for f in srt_files]


if __name__ == "__main__":
    try:
        output_dir = batch_convert_mp3_to_srt("C:/Users/leidc/Desktop/workspace/audios/20251202_201740/",
                                              "outputs")
        print(f"\n✅ 转换完成！输出目录: {output_dir}")
    except Exception as e:
        print(f"\n❌ 转换失败: {e}")
        sys.exit(1)

