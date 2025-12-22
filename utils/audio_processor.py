"""
音频处理工具
使用 FFmpeg 处理音频文件，包括音量调整、循环、裁剪等
"""

import os
import subprocess
from utils.config_loader import get_config
from utils.loggers import get_logger

config = get_config()
logger = get_logger('audio_processor', silent=True)


def get_audio_duration(audio_path: str) -> float:
    """
    获取音频文件的时长（秒）
    
    Args:
        audio_path: 音频文件路径
    
    Returns:
        音频时长（秒）
    """
    # 使用配置中的路径（已支持打包环境）
    ffprobe_path = config.get_absolute_path(config.get('ffmpeg.ffprobe_path'))
    
    # Windows 下隐藏命令行窗口
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    cmd = [
        ffprobe_path,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_path
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            creationflags=creation_flags
        )
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        logger.error(f"获取音频时长失败: {e}")
        raise


def adjust_bgm_for_video(
    bgm_path: str,
    output_path: str,
    target_duration: float,
    volume: float = 0.5
) -> str:
    """
    调整BGM以匹配视频时长
    - 如果BGM太长，裁剪到目标时长
    - 如果BGM太短，循环播放到目标时长
    - 同时调整音量
    
    Args:
        bgm_path: BGM源文件路径
        output_path: 输出文件路径
        target_duration: 目标时长（秒）
        volume: 音量（0.0-2.0，1.0为原音量）
    
    Returns:
        处理后的音频文件路径
    """
    # 使用配置中的路径（已支持打包环境）
    ffmpeg_path = config.get_absolute_path(config.get('ffmpeg.ffmpeg_path'))
    
    # 获取BGM时长
    bgm_duration = get_audio_duration(bgm_path)
    logger.info(f"BGM原始时长: {bgm_duration:.2f}秒, 目标时长: {target_duration:.2f}秒")
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Windows 下隐藏命令行窗口
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    if bgm_duration >= target_duration:
        # BGM较长，裁剪并调整音量
        cmd = [
            ffmpeg_path,
            '-i', bgm_path,
            '-t', str(target_duration),
            '-af', f'volume={volume}',
            '-y',
            output_path
        ]
        logger.info(f"BGM较长，裁剪到 {target_duration:.2f}秒")
    else:
        # BGM较短，需要循环播放
        # 计算需要循环的次数
        loop_count = int(target_duration / bgm_duration) + 1
        
        # 使用 concat 滤镜循环，然后裁剪到目标时长
        cmd = [
            ffmpeg_path,
            '-stream_loop', str(loop_count),
            '-i', bgm_path,
            '-t', str(target_duration),
            '-af', f'volume={volume}',
            '-y',
            output_path
        ]
        logger.info(f"BGM较短，循环播放 {loop_count} 次后裁剪到 {target_duration:.2f}秒")
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, creationflags=creation_flags)
        logger.info(f"BGM处理完成: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"BGM处理失败: {e.stderr.decode('utf-8', errors='ignore')}")
        raise


def adjust_audio_volume(
    audio_path: str,
    output_path: str,
    volume: float = 1.0
) -> str:
    """
    调整音频音量
    
    Args:
        audio_path: 源音频文件路径
        output_path: 输出文件路径
        volume: 音量（0.0-2.0，1.0为原音量）
    
    Returns:
        处理后的音频文件路径
    """
    # 使用配置中的路径（已支持打包环境）
    ffmpeg_path = config.get_absolute_path(config.get('ffmpeg.ffmpeg_path'))
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Windows 下隐藏命令行窗口
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    cmd = [
        ffmpeg_path,
        '-i', audio_path,
        '-af', f'volume={volume}',
        '-y',
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, creationflags=creation_flags)
        logger.info(f"音量调整完成: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"音量调整失败: {e.stderr.decode('utf-8', errors='ignore')}")
        raise


if __name__ == "__main__":
    # 测试代码
    test_bgm = "path/to/test.mp3"
    test_output = "path/to/output.mp3"
    
    # 测试调整BGM
    # adjust_bgm_for_video(test_bgm, test_output, 60.0, 0.5)
    pass

