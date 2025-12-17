import re
import os
import uuid
import subprocess
from datetime import datetime
from utils.config_loader import get_config
from utils.loggers import get_logger

# === 加载配置 ===
config = get_config()
logger = get_logger('video_editing', silent=True)

# # 获取视频剪辑配置（转换为绝对路径）
TEMP_DIR = config.get_workspace_path("videos/temp")  # 临时文件目录
OUTPUT_DIR = config.get_workspace_path("videos")  # 输出目录

# 获取FFmpeg配置（转换为绝对路径）
FFMPEG_PATH = config.get_absolute_path(config.get("ffmpeg.ffmpeg_path"))  # ffmpeg路径
FFPROBE_PATH = config.get_absolute_path(config.get("ffmpeg.ffprobe_path"))  # ffprobe路径

# === 工具函数 ===
def parse_srt(srt_path):
    """解析SRT文件,返回 [(开始时间秒, 结束时间秒, 字幕文本)]"""
    clips = []
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        # 支持格式: HH:MM:SS,mmm 或 MM:SS,mmm
        match = re.search(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})', lines[1])
        if match:
            h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, match.groups())
        else:
            # 尝试匹配格式 MM:SS,mmm
            match = re.search(r'(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}),(\d{3})', lines[1])
            if match:
                m1, s1, ms1, m2, s2, ms2 = map(int, match.groups())
                h1, h2 = 0, 0
            else:
                continue
        
        start_sec = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
        end_sec = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0
        text = '\n'.join(lines[2:])
        clips.append((start_sec, end_sec, text))
    
    return clips

def cut_video_clips(video_file, clips, temp_dir):
    """根据时间戳剪切视频片段"""
    os.makedirs(temp_dir, exist_ok=True)
    
    # Windows 下隐藏命令行窗口
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    clip_files = []
    for i, (start_sec, end_sec, text) in enumerate(clips):
        duration = end_sec - start_sec
        output_file = os.path.join(temp_dir, f"clip_{i:04d}.mp4")
        
        # 使用ffmpeg剪切视频片段（精确剪切，需要重新编码）
        cmd = [
            FFMPEG_PATH,
            "-y",  # 覆盖已存在的文件
            "-ss", str(start_sec),  # 开始时间
            "-i", video_file,  # 输入文件
            "-t", str(duration),  # 持续时间
            "-c:v", "libx264",  # 视频编码：H.264（精确剪切）
            "-c:a", "aac",  # 音频编码：AAC
            "-preset", "fast",  # 编码速度：fast（平衡速度和质量）
            "-crf", "18",  # 质量：18（高质量，接近无损）
            "-avoid_negative_ts", "make_zero",  # 避免负时间戳
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=creation_flags)
        if result.returncode != 0:
            continue
        
        clip_files.append(output_file)
    
    return clip_files

def concat_video_clips(clip_files, output_file):
    """拼接视频片段"""
    # 创建拼接列表文件
    concat_list = os.path.join(TEMP_DIR, "concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for clip_file in clip_files:
            # 使用绝对路径,避免路径问题
            abs_path = os.path.abspath(clip_file).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")
    
    # Windows 下隐藏命令行窗口
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    # 使用ffmpeg拼接视频
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=creation_flags)
    if result.returncode != 0:
        return False
    
    return True

def get_video_info(video_file):
    """获取视频信息(时长、宽高)"""
    try:
        # Windows 下隐藏命令行窗口
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        
        # 获取时长
        result = subprocess.run(
            [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', video_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=creation_flags
        )
        duration_seconds = float(result.stdout.strip())
        duration_us = int(duration_seconds * 1000000)
        
        # 获取宽高
        result = subprocess.run(
            [FFPROBE_PATH, '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height',
             '-of', 'csv=s=x:p=0', video_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=creation_flags
        )
        width, height = map(int, result.stdout.strip().split('x'))
        
        return duration_us, width, height
    except Exception as e:
        return None, None, None

def gen_id():
    return uuid.uuid4().hex


def get_video_duration(video_file):
    """
    获取视频时长（秒）
    
    Args:
        video_file: 视频文件路径
    
    Returns:
        视频时长（秒），失败返回None
    """
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(
            [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', video_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=creation_flags
        )
        duration_seconds = float(result.stdout.strip())
        return duration_seconds
    except Exception as e:
        logger.error(f"获取视频时长失败: {e}")
        return None


# === 主程序 ===
def edit_video(srt_file, video_file):
    """
    根据SRT字幕文件剪切并拼接视频
    
    Args:
        srt_file: 字幕文件路径（外部传入）
    
    Returns:
        生成的视频文件路径，失败返回None
    """
    
    logger.info(f"  📄 SRT文件: {srt_file}")
    logger.info(f"  🎬 视频文件: {video_file}")
    
    # 检查文件是否存在
    if not os.path.exists(srt_file):
        logger.error(f"  ❌ SRT文件不存在: {srt_file}")
        return None
    
    if not os.path.exists(video_file):
        logger.error(f"  ❌ 视频文件不存在: {video_file}")
        return None
    
    # 生成输出视频文件名（使用时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_video = os.path.join(OUTPUT_DIR, f"{timestamp}.mp4")
    
    # 1. 解析SRT文件
    logger.info(f"  📝 解析SRT文件...")
    clips = parse_srt(srt_file)
    if not clips:
        logger.error(f"  ❌ SRT文件解析失败，未找到有效的字幕片段")
        return None
    logger.info(f"  ✅ 解析成功，找到 {len(clips)} 个片段")
    
    # 2. 剪切视频片段
    logger.info(f"  ✂️  剪切视频片段...")
    clip_files = cut_video_clips(video_file, clips, TEMP_DIR)
    if not clip_files:
        logger.error(f"  ❌ 视频剪切失败，未生成任何片段")
        return None
    logger.info(f"  ✅ 剪切成功，生成 {len(clip_files)} 个片段")
    
    # 3. 拼接视频片段
    logger.info(f"  🔗 拼接视频片段...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not concat_video_clips(clip_files, final_video):
        logger.error(f"  ❌ 视频拼接失败")
        return None

    return final_video

if __name__ == "__main__":

    # 测试用的默认SRT文件路径
    srt_file_path = "C:/Users/leidc/Desktop/test/clip.txt"

    video_src_path = "C:/Users/leidc/Desktop/待处理视频/捕风追影1.mp4"
    
    result = edit_video(srt_file_path, video_src_path)
    if result:
        logger.info(f"✅ 视频生成成功: {result}")
    else:
        logger.error("❌ 视频生成失败")

