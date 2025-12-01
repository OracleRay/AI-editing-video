import os
import subprocess
from datetime import datetime
from pathlib import Path

from core.gen_json import generate_capcut_project, generate_audio_from_srt, parse_srt
from core.video_editing import get_video_info
from utils.config_loader import get_config
from utils.loggers import get_logger

config = get_config()
logger = get_logger("zhong_cao", silent=True)

TEXT_SOURCE = "resources/dst/srt_files/zhongCao/test.srt"
VIDEO_SOURCE = "resources/dst/videos/final_clip.mp4"
JSON_OUTPUT_DIR = "resources/dst/json/zhongCao"
AUDIO_BASE_DIR = config.get("audio.output_dir")
FFMPEG_PATH = config.get_absolute_path(config.get("ffmpeg.ffmpeg_path"))


def trim_video_to_duration(video_path: str, duration_sec: float) -> str:
    tolerance = 0.05  # 50ms 容差
    video_duration_us, _, _ = get_video_info(video_path)
    if video_duration_us is None:
        logger.warning("无法获取视频时长，跳过裁剪")
        return video_path

    video_duration_sec = video_duration_us / 1_000_000
    if video_duration_sec <= duration_sec + tolerance:
        return video_path

    target = Path(video_path)
    cropped_path = target.with_name(f"{target.stem}_cropped{target.suffix}")

    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i",
        video_path,
        "-t",
        f"{duration_sec:.3f}",
        "-c",
        "copy",
        str(cropped_path),
    ]
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
        creationflags=creation_flags,
    )
    if result.returncode != 0:
        raise RuntimeError(f"裁剪视频失败: {result.stderr.strip()}")

    logger.info(f"视频已裁剪: {cropped_path}")
    return str(cropped_path)


def run_zhong_cao_pipeline():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_dir_rel = str(Path(AUDIO_BASE_DIR) / timestamp)
    
    # 使用与 gen_json.py 完全相同的逻辑生成音频
    reference_audio = config.get("tts.reference_audio")
    model = config.get("tts.model")
    speed = config.get("tts.speed", 1.0)
    
    logger.info(f"开始生成音频...")
    generate_audio_from_srt(
        srt_file=TEXT_SOURCE,
        reference_audio=reference_audio,
        output_dir=audio_dir_rel,
        model=model,
        speed=speed
    )
    
    # 从原始SRT文件中获取总时长（使用 gen_json.py 的 parse_srt 方法）
    srt_path = config.get_absolute_path(TEXT_SOURCE)
    clips = parse_srt(srt_path)
    if not clips:
        raise RuntimeError("SRT文件解析失败，未找到有效的字幕片段")
    
    # 获取SRT中的最大结束时间作为总时长
    total_duration_us = max(end_us for _, end_us, _ in clips)
    total_duration_sec = total_duration_us / 1_000_000
    
    # 裁剪视频（如果视频时长大于音频总时长）
    video_path = config.get_absolute_path(VIDEO_SOURCE)
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    normalized_video_path = trim_video_to_duration(video_path, total_duration_sec)
    
    # 准备音频文件模式（使用 gen_json.py 相同的格式）
    audio_pattern_for_run = str(Path(audio_dir_rel) / "{:04d}.mp3")
    json_dir_rel = str(Path(JSON_OUTPUT_DIR) / timestamp)
    
    # 直接调用 gen_json.py 的方法生成剪映项目（使用原始SRT文件）
    generate_capcut_project(
        video_file=normalized_video_path,
        audio_pattern=audio_pattern_for_run,
        srt_file=TEXT_SOURCE,
        output_dir=json_dir_rel,
    )
    
    logger.info("剪映草稿生成完成")
    logger.info(f"音频目录: {config.get_absolute_path(audio_dir_rel)}")
    logger.info(f"剪映草稿: {config.get_absolute_path(json_dir_rel)}")


if __name__ == "__main__":
    run_zhong_cao_pipeline()

