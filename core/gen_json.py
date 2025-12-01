from datetime import datetime
import json
import re
import os
import uuid
import subprocess
import sys
from pathlib import Path

# 添加utils目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from services.tts_client import parse_srt as tts_parse_srt, process_subtitle, ensure_output_dir
from utils.config_loader import get_config, get_workspace_path
from utils.meta_json import *
from utils.loggers import get_logger

# === 加载配置 ===
config = get_config()
FFPROBE_PATH = config.get('ffmpeg.ffprobe_path')
logger = get_logger('gen_json', silent=True)


def generate_audio_from_srt(srt_file, reference_audio, output_dir, model, speed):
    """根据SRT文件生成音频文件"""
    
    # 使用 config_loader 转换为绝对路径
    srt_path = config.get_absolute_path(srt_file)
    if not os.path.exists(srt_path):
        raise FileNotFoundError(f"SRT文件不存在: {srt_path}")
    
    subtitles = tts_parse_srt(srt_path)

    # 检查参考音频
    reference_audio_path = config.get_absolute_path(reference_audio)
    if not os.path.exists(reference_audio_path):
        raise FileNotFoundError(f"参考音频不存在: {reference_audio_path}")

    # 创建输出目录
    out_dir = config.get_absolute_path(output_dir)
    ensure_output_dir(out_dir)
    
    # 处理每条字幕
    success_count = 0
    failed_count = 0
    for file_index, subtitle in enumerate(subtitles, start=1):
        try:
            process_subtitle(subtitle, model, reference_audio_path, out_dir, speed, file_index)
            success_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"字幕 {subtitle['index']} 处理失败: {e}")
    
    # 总结
    logger.info(f"音频生成完成: 成功 {success_count}/{len(subtitles)} 个")
    
    if failed_count == len(subtitles):
        raise RuntimeError("所有音频生成失败，无法继续")

def parse_srt(srt_path):
    """解析SRT文件，返回 [(开始时间微秒, 结束时间微秒, 字幕文本)]"""
    clips = []
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        # 支持两种格式：HH:MM:SS,mmm 或 MM:SS,mmm
        match = re.search(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})', lines[1])
        if match:
            h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, match.groups())
        else:
            # 尝试匹配不带小时的格式 MM:SS,mmm
            match = re.search(r'(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})', lines[1])
            if match:
                m1, s1, ms1, h2, m2, s2, ms2 = map(int, match.groups())
                h1 = 0
            else:
                continue
        
        start_us = ((h1 * 3600 + m1 * 60 + s1) * 1000 + ms1) * 1000
        end_us = ((h2 * 3600 + m2 * 60 + s2) * 1000 + ms2) * 1000
        text = '\n'.join(lines[2:])
        clips.append((start_us, end_us, text))
    
    return clips

def gen_id():
    return uuid.uuid4().hex

def get_audio_duration(audio_path):
    """获取音频文件的实际时长（微秒）"""
    try:
        ffprobe_abs_path = config.get_absolute_path(FFPROBE_PATH)
        result = subprocess.run(
            [ffprobe_abs_path, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        duration_seconds = float(result.stdout.strip())
        return int(duration_seconds * 1000000)  # 转换为微秒
    except Exception as e:
        return None

def get_video_aspect_ratio(video_path):
    """获取视频文件的宽高比，返回'16:9'或'4:3'，如果无法获取则返回None"""
    try:
        ffprobe_abs_path = config.get_absolute_path(FFPROBE_PATH)
        result = subprocess.run(
            [ffprobe_abs_path, '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height', '-of', 'csv=p=0', video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            dimensions = result.stdout.strip().split(',')
            if len(dimensions) == 2:
                width = int(dimensions[0])
                height = int(dimensions[1])
                
                # 计算宽高比
                ratio = width / height
                
                # 判断比例（允许一定的误差范围）
                if 1.3 <= ratio <= 1.4:  # 4:3 ≈ 1.333
                    return "4:3"
                elif 1.7 <= ratio <= 1.8:  # 16:9 ≈ 1.777
                    return "16:9"
                elif 1.2 <= ratio <= 1.3:  # 5:4 ≈ 1.25
                    return "5:4"
                elif 0.7 <= ratio <= 0.8:  # 9:16 ≈ 0.5625 (竖屏)
                    return "9:16"
                else:
                    # 对于其他比例，返回最接近的标准比例
                    if abs(ratio - 1.333) < abs(ratio - 1.777):
                        return "4:3"
                    else:
                        return "16:9"
        
        return None
    except Exception as e:
        logger.error(f"获取视频宽高比失败: {e}")
        return None

def get_canvas_dimensions(aspect_ratio):
    """根据宽高比返回画布尺寸"""
    if aspect_ratio == "4:3":
        return 1440, 1080  # 4:3 标准分辨率
    elif aspect_ratio == "5:4":
        return 1280, 1024  # 5:4 标准分辨率
    elif aspect_ratio == "9:16":
        return 1080, 1920  # 竖屏9:16
    else:  # 默认16:9
        return 1920, 1080  # 16:9 标准分辨率

# === 生成项目文件 ===
def generate_capcut_project(video_file, audio_pattern, srt_file, output_dir):
    # 将相对路径转换为绝对路径
    srt_abs_path = config.get_absolute_path(srt_file)
    clips = parse_srt(srt_abs_path)
    if not clips:
        return
    
    output_abs_dir = config.get_absolute_path(output_dir)
    os.makedirs(output_abs_dir, exist_ok=True)
    
    # 基本信息
    video_abs_path = config.get_absolute_path(video_file)
    video_filename = os.path.basename(video_file)
    total_duration = max(end for _, end, _ in clips)
    project_id = str(uuid.uuid4()).upper()
    
    video_mat_id = gen_id()
    speed_id = gen_id()
    
    # === 创建音频素材和片段 ===
    audio_materials = []
    audio_segments_with_track = []  # [(segment, track_index, start, end), ...]
    audio_timings = []  # 记录音频的实际播放时段 [(start, end), ...]
    
    # 用于追踪每个轨道的最后结束时间
    track_end_times = []  # [end_time_of_track_0, end_time_of_track_1, ...]
    
    for i, (start_us, end_us, text) in enumerate(clips):
        audio_file = audio_pattern.format(i + 1)
        audio_abs_path = config.get_absolute_path(audio_file)
        
        if not os.path.exists(audio_abs_path):
            continue
        
        # 获取音频文件的实际时长
        real_audio_duration = get_audio_duration(audio_abs_path)
        if real_audio_duration is None:
            continue
        
        audio_mat_id = gen_id()
        
        # 音频素材（使用音频文件的真实时长）
        audio_materials.append({
            "app_id": 0,
            "category_id": "",
            "category_name": "local",
            "check_flag": 1,
            "duration": real_audio_duration,  # 使用真实时长
            "effect_id": "",
            "formula_id": "",
            "id": audio_mat_id,
            "intensifies_path": "",
            "local_material_id": "",
            "material_id": audio_mat_id,
            "material_name": os.path.basename(audio_file),
            "material_url": "",
            "name": os.path.basename(audio_file),
            "path": audio_abs_path,
            "query": "",
            "request_id": "",
            "resource_id": "",
            "source_platform": 0,
            "team_id": "",
            "text_id": "",
            "type": "extract_music",
            "video_id": "",
            "wave_points": []
        })
        
        # 计算当前音频的时间范围
        audio_start = start_us
        audio_end = start_us + real_audio_duration
        
        # 查找可以放置当前音频的轨道（不重叠的轨道）
        track_index = -1
        for idx, track_end in enumerate(track_end_times):
            if audio_start >= track_end:  # 当前音频开始时间 >= 该轨道的结束时间，无重叠
                track_index = idx
                track_end_times[idx] = audio_end  # 更新该轨道的结束时间
                break
        
        # 如果没有找到合适的轨道，创建新轨道
        if track_index == -1:
            track_index = len(track_end_times)
            track_end_times.append(audio_end)
        
        # 音频片段（从字幕开始时间播放，使用真实时长）
        segment = create_base_segment()
        segment.update({
            "id": gen_id(),
            "material_id": audio_mat_id,
            "target_timerange": {"start": start_us, "duration": real_audio_duration},  # 真实时长
            "source_timerange": {"start": 0, "duration": real_audio_duration},  # 真实时长
            "volume": 1.0,
            "extra_material_refs": [],
            "track_render_index": track_index  # 设置轨道索引
        })
        audio_segments_with_track.append((segment, track_index, audio_start, audio_end))
        
        # 记录音频实际播放的时段
        audio_timings.append((start_us, start_us + real_audio_duration))
    
    # === 创建视频片段（音频时静音，间隙时原声）===
    video_segments = []
    current_time = 0
    
    for audio_start, audio_end in audio_timings:
        # 如果当前时间小于音频开始时间，说明有间隙，播放原声
        if current_time < audio_start:
            gap_segment = create_base_segment()
            gap_duration = audio_start - current_time
            gap_segment.update({
                "id": gen_id(),
                "material_id": video_mat_id,
                "target_timerange": {"start": current_time, "duration": gap_duration},
                "source_timerange": {"start": current_time, "duration": gap_duration},
                "volume": 1.0,  # 间隙播放原声
                "extra_material_refs": [speed_id],
                "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000}
            })
            video_segments.append(gap_segment)
        
        # 音频播放时段，视频静音（使用音频的实际时长）
        audio_duration = audio_end - audio_start
        mute_segment = create_base_segment()
        mute_segment.update({
            "id": gen_id(),
            "material_id": video_mat_id,
            "target_timerange": {"start": audio_start, "duration": audio_duration},
            "source_timerange": {"start": audio_start, "duration": audio_duration},
            "volume": 0.0,  # 音频播放时视频静音
            "extra_material_refs": [speed_id],
            "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000}
        })
        video_segments.append(mute_segment)
        
        current_time = audio_end
    
    # 如果最后还有剩余时间，播放原声
    if current_time < total_duration:
        final_segment = create_base_segment()
        final_duration = total_duration - current_time
        final_segment.update({
            "id": gen_id(),
            "material_id": video_mat_id,
            "target_timerange": {"start": current_time, "duration": final_duration},
            "source_timerange": {"start": current_time, "duration": final_duration},
            "volume": 1.0,  # 最后的间隙播放原声
            "extra_material_refs": [speed_id],
            "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000}
        })
        video_segments.append(final_segment)
    
    video_track = {
        "attribute": 0,
        "flag": 0,
        "id": gen_id(),
        "is_default_name": False,
        "name": "主视频轨道",
        "segments": video_segments,
        "type": "video"
    }
    
    # === 创建音频轨道（根据轨道数量创建多个轨道）===
    num_tracks = len(track_end_times)
    audio_tracks = []
    
    for track_idx in range(num_tracks):
        # 收集该轨道上的所有片段
        track_segments = [seg for seg, idx, _, _ in audio_segments_with_track if idx == track_idx]
        
        audio_track = {
            "attribute": 0,
            "flag": 0,
            "id": gen_id(),
            "is_default_name": True if track_idx == 0 else False,
            "name": "" if track_idx == 0 else f"音频轨道{track_idx + 1}",
            "segments": track_segments,
            "type": "audio"
        }
        audio_tracks.append(audio_track)
    
    # === 检测视频宽高比 ===
    aspect_ratio = get_video_aspect_ratio(video_abs_path)
    if aspect_ratio is None:
        aspect_ratio = "16:9"  # 默认使用16:9
        logger.warning(f"无法获取视频宽高比，使用默认值: {aspect_ratio}")
    else:
        logger.info(f"检测到视频宽高比: {aspect_ratio}")
    
    # 获取对应的画布尺寸
    canvas_width, canvas_height = get_canvas_dimensions(aspect_ratio)

    # === 组装项目 ===
    project = generate_project_data(
        video_mat_id=video_mat_id,
        speed_id=speed_id,
        total_duration=total_duration,
        project_id=project_id,
        audio_materials=audio_materials,
        video_track=video_track,
        audio_tracks=audio_tracks,
        video_filename=video_filename,
        video_abs_path=video_abs_path,
        aspect_ratio=aspect_ratio,
        canvas_width=canvas_width,
        canvas_height=canvas_height
    )
    
    # === 生成元数据 ===
    meta_info = generate_meta_info(
        project_id=project_id,
        total_duration=total_duration
    )
    
    # === 保存文件 ===
    with open(os.path.join(output_abs_dir, "draft_content.json"), "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=4)
    
    with open(os.path.join(output_abs_dir, "draft_meta_info.json"), "w", encoding="utf-8") as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=4)
    
    logger.info(f"剪映项目文件已生成: {output_abs_dir}")
    logger.info(f"视频片段: {len(video_segments)} 个 | 音频片段: {len(audio_segments_with_track)} 个 | 总时长: {total_duration / 1000000:.2f} 秒")

if __name__ == "__main__":
    generate_audio_from_srt(
        srt_file="C:/Users/leidc/Desktop/workspace/srt_files/jieShuo/test.txt",
        reference_audio="resources/src/audios/xiao_shuai/爆款小帅男声.MP3",
        output_dir="C:/Users/leidc/Desktop/workspace/audios/test/",
        model=config.get('tts.model'),
        speed=config.get('tts.speed')
    )
    logger.info(f"✅ 音频生成完成!")

    # 生成剪映项目文件
    generate_capcut_project(
        video_file="C:/Users/leidc/Desktop/workspace/videos/20251126_164351.mp4",
        audio_pattern=str("C:/Users/leidc/Desktop/workspace/audios/test/" + Path(config.get('audio.pattern')).name),
        srt_file="C:/Users/leidc/Desktop/workspace/srt_files/jieShuo/test.txt",
        output_dir="C:/Users/leidc/Desktop/workspace/json/test/"
    )
    logger.info(f"✅ 剪映项目生成完成!")