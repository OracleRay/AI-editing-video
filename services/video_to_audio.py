#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import shutil
import os
from pathlib import Path
import sys

# 添加utils目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.loggers import get_logger

logger = get_logger('video_to_audio', silent=True)


def _select_codec(output_suffix: str) -> list:
    """根据输出后缀选择合适的音频编码参数（尽量简洁）。"""
    suffix = output_suffix.lower()
    if suffix == ".mp3":
        return ["-acodec", "libmp3lame", "-b:a", "192k"]
    if suffix in (".m4a", ".aac"):
        return ["-acodec", "aac", "-b:a", "192k"]
    if suffix == ".wav":
        return ["-acodec", "pcm_s16le"]
    if suffix == ".flac":
        return ["-acodec", "flac"]
    # 默认用aac，兼容性较好
    return ["-acodec", "aac", "-b:a", "192k"]


def convert_video_to_audio(input_path: Path, output_path: Path) -> None:
    """
    使用本地 ffmpeg 将视频转音频，保存到指定路径。
    - input_path: 输入视频文件路径
    - output_path: 输出音频文件路径（通过后缀决定编码）
    """
    # 使用项目中的 ffmpeg
    project_root = Path(__file__).parent.parent
    ffmpeg_path = project_root / "resources" / "src" / "ffmpeg" / "ffmpeg.exe"
    
    if not ffmpeg_path.exists():
        raise RuntimeError(f"未找到 ffmpeg: {ffmpeg_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    # 规范化输出文件路径：
    # - 若给的是目录或无后缀，则自动以输入文件名生成 .mp3
    # - 若给的是具体文件（有后缀），按后缀选择编码
    if output_path.suffix == "":
        output_dir = output_path
        output_file = output_dir / f"{input_path.stem}.mp3"
    else:
        output_dir = output_path.parent
        output_file = output_path

    output_dir.mkdir(parents=True, exist_ok=True)

    codec_args = _select_codec(output_file.suffix)

    cmd = [
        ffmpeg_path,       # 使用找到的ffmpeg路径
        "-y",              # 覆盖输出
        "-i", str(input_path),
        "-vn",             # 去除视频流
        *codec_args,
        str(output_file),
    ]

    # 避免 Windows 控制台编码问题（GBK/UTF-8），按字节捕获后再安全解码
    # 避免弹出黑框
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creation_flags)
    if result.returncode != 0:
        stderr_text = None
        for enc in ("utf-8", "gbk", sys.getdefaultencoding() or "utf-8"):
            try:
                stderr_text = result.stderr.decode(enc, errors="replace")
                break
            except Exception:
                continue
        raise RuntimeError(f"ffmpeg 执行失败:\n{stderr_text}")


if __name__ == "__main__":
    # 批量处理 resources/src/videos/ 目录下的所有视频文件
    project_root = Path(__file__).parent.parent
    input_dir = project_root / "resources" / "src" / "videos" / "processing"
    output_dir = project_root / "resources" / "src" / "audios" / "processing"
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 支持的视频格式
    video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".m4v"]
    
    # 获取所有视频文件
    video_files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() in video_extensions]
    
    if not video_files:
        logger.warning(f"在 {input_dir} 目录下没有找到视频文件")
        sys.exit(1)
    
    logger.info(f"找到 {len(video_files)} 个视频文件，开始转换...")
    
    success_count = 0
    failed_count = 0
    
    for video_file in video_files:
        output_file = output_dir / f"{video_file.stem}.mp3"
        try:
            logger.info(f"正在转换: {video_file.name} -> {output_file.name}")
            convert_video_to_audio(video_file, output_file)
            logger.info(f"✓ 转换成功: {output_file.name}")
            success_count += 1
        except Exception as e:
            logger.error(f"✗ 转换失败 {video_file.name}: {e}")
            failed_count += 1
    
    logger.info(f"转换完成！成功: {success_count}, 失败: {failed_count}")


