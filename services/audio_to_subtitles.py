#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import requests
from pathlib import Path

# 添加utils目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.loggers import get_logger

# API 配置
API_URL = "http://116.211.238.68:8881/api/v1/transcribe"

# 日志记录器
logger = get_logger('audio_to_subtitles', silent=True)

# 兼容控制台编码
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def transcribe_audio(audio_path: str, api_url: str):
    """调用 API 转录音频文件"""
    with open(audio_path, 'rb') as f:
        resp = requests.post(api_url, files={'file': f})
    if resp.status_code != 200:
        raise RuntimeError(f"API请求失败: {resp.status_code}\n{resp.text}")
    return resp.json()


def format_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def create_srt(transcription: dict, srt_path: str) -> str:
    """将转录结果生成 SRT 字幕文件"""
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(transcription["segments"], 1):
            f.write(f"{i}\n")
            f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
            f.write(seg.get('text', '').strip() + "\n\n")
    return srt_path


def main():
    # 批量处理 resources/src/audios/ 目录下的所有音频文件
    project_root = Path(__file__).parent.parent
    input_dir = project_root / "resources" / "src" / "audios" / "processing"
    output_dir = project_root / "resources" / "src" / "srt_files"
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取所有音频文件
    audio_files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == ".mp3"]
    
    if not audio_files:
        logger.warning(f"在 {input_dir} 目录下没有找到 mp3 文件")
        return
    
    logger.info(f"找到 {len(audio_files)} 个音频文件，开始转录...")
    
    success_count = 0
    failed_count = 0
    
    for audio_file in audio_files:
        srt_file = output_dir / f"{audio_file.stem}.srt"
        txt_file = output_dir / "txt" / f"{audio_file.stem}.txt"
        
        try:
            logger.info(f"正在转录: {audio_file.name}")
            result = transcribe_audio(str(audio_file), API_URL)
            
            create_srt(result, str(srt_file))
            srt_to_txt(str(srt_file), str(txt_file))
            
            logger.info(f"✓ 转录成功: {audio_file.name} -> {srt_file.name}")
            success_count += 1
        except Exception as e:
            logger.error(f"✗ 转录失败 {audio_file.name}: {e}")
            failed_count += 1
    
    logger.info(f"转录完成！成功: {success_count}, 失败: {failed_count}")


if __name__ == "__main__":
    main()


