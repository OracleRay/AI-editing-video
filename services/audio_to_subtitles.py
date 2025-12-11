#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import requests
from pathlib import Path

# 添加utils目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.loggers import get_logger
from utils.config_loader import get_config

# 加载配置
config = get_config()

# 从配置文件读取 API 配置
API_URL = config.get('audio_to_subtitles.api_url', 'http://116.211.238.68:8881/api/v1/transcribe')
API_KEY = config.get('audio_to_subtitles.api_key', None)

# 日志记录器
logger = get_logger('audio_to_subtitles', silent=True)

# 兼容控制台编码
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def transcribe_audio(audio_path: str, api_url: str, api_key: str | None = None):
    """调用 API 转录音频文件"""
    headers = {"X-API-KEY": api_key} if api_key else {}
    with open(audio_path, 'rb') as f:
        resp = requests.post(api_url, files={'file': f}, headers=headers)
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
    project_root = Path("C:/Users/leidc/Desktop/视频转文字/temp")
    audio_file = project_root / "13408704556454612.mp3"
    srt_file = project_root / "temp.srt"

    try:
        logger.info(f"正在转录: {audio_file.name}")
        result = transcribe_audio(str(audio_file), API_URL, API_KEY)

        create_srt(result, str(srt_file))

        logger.info(f"✓ 转录成功: {audio_file.name} -> {srt_file.name}")
    except Exception as e:
        logger.error(f"✗ 转录失败 {audio_file.name}: {e}")



if __name__ == "__main__":
    main()


