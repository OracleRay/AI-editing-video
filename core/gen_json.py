from datetime import datetime
import json
import re
import os
import uuid
import subprocess
import sys
import random
from pathlib import Path

# 添加utils目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from services.tts_client import parse_srt as tts_parse_srt, process_subtitle, ensure_output_dir
from utils.config_loader import get_config, get_workspace_path
from utils.meta_json import *
from utils.loggers import get_logger
from utils.subtitle_detector import detect_subtitle_position
from utils.gen_jieShuo_srt import batch_convert_mp3_to_srt

# === 加载配置 ===
config = get_config()
FFPROBE_PATH = config.get('ffmpeg.ffprobe_path')
logger = get_logger('gen_json', silent=True)

# === 转场配置 ===
TRANSITION_CONFIGS = [
    {
        "name": "横移模糊",
        "resource_id": "7316901787762430491",
        "effect_id": "36950128",
        "duration": 500000
    },
    {
        "name": "推近 II",
        "resource_id": "7290852476259930685",
        "effect_id": "26135688",
        "duration": 500000
    },
    {
        "name": "回忆拉屏 II",
        "resource_id": "7306440470119322139",
        "effect_id": "31456359",
        "duration": 300000
    }
]


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
        # Windows 下隐藏命令行窗口
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(
            [ffprobe_abs_path, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags
        )
        duration_seconds = float(result.stdout.strip())
        return int(duration_seconds * 1000000)  # 转换为微秒
    except Exception as e:
        return None

def get_video_dimensions(video_path):
    """获取视频文件的真实宽度和高度，返回 (width, height, aspect_ratio_name)"""
    try:
        ffprobe_abs_path = config.get_absolute_path(FFPROBE_PATH)
        # Windows 下隐藏命令行窗口
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(
            [ffprobe_abs_path, '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height', '-of', 'csv=p=0', video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags
        )
        
        if result.returncode == 0:
            dimensions = result.stdout.strip().split(',')
            if len(dimensions) == 2:
                width = int(dimensions[0])
                height = int(dimensions[1])
                
                # 计算宽高比并判断类型（用于显示）
                ratio = width / height
                aspect_ratio_name = get_aspect_ratio_name(ratio)
                
                return width, height, aspect_ratio_name
        
        return None, None, None
    except Exception as e:
        logger.error(f"获取视频尺寸失败: {e}")
        return None, None, None

def get_aspect_ratio_name(ratio):
    """根据宽高比数值判断比例名称"""
    if 1.3 <= ratio <= 1.4:  # 4:3 ≈ 1.333
        return "4:3"
    elif 1.7 <= ratio <= 1.8:  # 16:9 ≈ 1.777
        return "16:9"
    elif 2.3 <= ratio <= 2.4:  # 21:9 ≈ 2.333 (电影超宽屏)
        return "21:9"
    elif 1.2 <= ratio <= 1.3:  # 5:4 ≈ 1.25
        return "5:4"
    elif 0.55 <= ratio <= 0.65:  # 9:16 ≈ 0.5625 (竖屏)
        return "9:16"
    elif 0.42 <= ratio <= 0.48:  # 9:21 ≈ 0.428 (竖屏电影)
        return "9:21"
    else:
        # 对于其他比例，返回最接近的标准比例
        ratios = {
            "4:3": abs(ratio - 1.333),
            "16:9": abs(ratio - 1.777),
            "21:9": abs(ratio - 2.333),
            "9:16": abs(ratio - 0.5625),
            "9:21": abs(ratio - 0.428)
        }
        return min(ratios, key=ratios.get)

# === 生成项目文件 ===
def generate_capcut_project(video_file, audio_pattern, srt_file, output_dir,
                            ocr_confidence=0.4, audio_dir=None, subtitle_dir=None):
    """
    生成剪映项目文件
    
    Args:
        video_file: 视频文件路径
        audio_pattern: 音频文件模式
        srt_file: 字幕文件路径
        output_dir: 输出目录
        enable_subtitle_mask: 是否启用字幕蒙版（模糊效果）
        ocr_confidence: OCR置信度阈值（0.0-1.0），默认0.5
        audio_dir: 包含多个音频文件的目录（可选），会自动转换为字幕并添加到项目中
        subtitle_dir: 字幕输出基础目录（可选），传递给 batch_convert_mp3_to_srt 作为 output_base_dir
    """
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
    audio_segments = []  # 音频片段列表（单轨道连续排列）
    audio_video_mapping = []  # 记录音频和原视频的时间映射 [(target_start, target_end, source_start, source_end), ...]
    
    audio_target_time = 0  # 音频在目标时间轴上的当前位置
    
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
        
        # 音频片段（连续排列在目标时间轴上）
        segment = create_base_segment()
        segment.update({
            "id": gen_id(),
            "material_id": audio_mat_id,
            "target_timerange": {"start": audio_target_time, "duration": real_audio_duration},  # 连续排列
            "source_timerange": {"start": 0, "duration": real_audio_duration},  # 从音频文件开头播放
            "volume": 1.0,
            "extra_material_refs": [],
            "track_render_index": 0  # 单轨道
        })
        audio_segments.append(segment)
        
        # 记录音频和原视频的时间映射关系
        audio_video_mapping.append((
            audio_target_time,  # 目标开始时间
            audio_target_time + real_audio_duration,  # 目标结束时间
            start_us,  # 原视频开始时间
            start_us + real_audio_duration  # 原视频结束时间（实际可能超出，但我们只取音频时长）
        ))
        
        # 更新音频目标时间
        audio_target_time += real_audio_duration
    
    # === 创建视频片段（音频时静音，音频结束后剪掉剩余部分）===
    video_segments = []
    transition_materials = []  # 存储所有转场材料
    transition_ids = []  # 存储每个片段对应的转场ID（最后一个片段无转场）
    
    logger.info("=" * 60)
    logger.info("🎬 开始添加转场效果")
    logger.info("=" * 60)
    
    total_segments = len(audio_video_mapping)
    
    for idx, (target_start, target_end, source_start, source_end) in enumerate(audio_video_mapping):
        # 隔一个片段添加转场（idx为偶数时添加：0, 2, 4, 6...，且不是最后一个片段）
        if idx < total_segments - 1 and idx % 2 == 0:
            # 随机选择一个转场
            transition_config = random.choice(TRANSITION_CONFIGS)
            transition_id = gen_id()
            
            # 创建转场材料
            transition_material = create_transition(
                transition_id=transition_id,
                name=transition_config["name"],
                resource_id=transition_config["resource_id"],
                effect_id=transition_config["effect_id"],
                duration=transition_config["duration"]
            )
            transition_materials.append(transition_material)
            transition_ids.append(transition_id)
            
            logger.info(f"✅ 片段 {idx+1} → {idx+2}: {transition_config['name']} ({transition_config['duration']/1000000:.2f}秒)")
        else:
            transition_ids.append(None)  # 奇数片段或最后一个片段无转场
        
        # 音频播放时段，视频静音
        duration = target_end - target_start
        mute_segment = create_base_segment()
        
        # 构建 extra_material_refs（如果有转场，转场ID在最前面）
        extra_refs = []
        if transition_ids[idx]:
            extra_refs.append(transition_ids[idx])
        extra_refs.append(speed_id)
        
        mute_segment.update({
            "id": gen_id(),
            "material_id": video_mat_id,
            "target_timerange": {"start": target_start, "duration": duration},
            "source_timerange": {"start": source_start, "duration": duration},  # 从原视频对应位置取素材
            "volume": 0.0,  # 音频播放时视频静音
            "extra_material_refs": extra_refs,
            "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
            "track_render_index": 0  # 主视频轨道（在底层）
        })
        video_segments.append(mute_segment)
    
    if transition_materials:
        logger.info("")
        logger.info(f"✅ 转场效果添加完成（隔一个片段添加）")
        logger.info(f"   总片段: {total_segments} 个 | 转场数: {len(transition_materials)} 个")
    
    # 重新计算总时长为所有音频的总时长
    total_duration = audio_target_time
    
    video_track = {
        "attribute": 0,
        "flag": 0,
        "id": gen_id(),
        "is_default_name": False,
        "name": "主视频轨道",
        "segments": video_segments,
        "type": "video"
    }
    
    # === 创建音频轨道（单轨道连续排列）===
    audio_tracks = []
    
    audio_track = {
        "attribute": 0,
        "flag": 0,
        "id": gen_id(),
        "is_default_name": True,
        "name": "",
        "segments": audio_segments,
        "type": "audio"
    }
    audio_tracks.append(audio_track)
    
    # === 获取视频真实尺寸 ===
    canvas_width, canvas_height, aspect_ratio = get_video_dimensions(video_abs_path)
    if canvas_width is None or canvas_height is None:
        # 无法获取，使用默认值
        canvas_width, canvas_height = 1920, 1080
        aspect_ratio = "16:9"
        logger.warning(f"无法获取视频尺寸，使用默认值: {canvas_width}x{canvas_height} ({aspect_ratio})")
    else:
        logger.info(f"检测到视频尺寸: {canvas_width}x{canvas_height} ({aspect_ratio})")
    
    # === 检测字幕位置（用于字幕定位和蒙版）===
    subtitle_position_y = -0.75  # 默认位置（底部）
    subtitle_position = None
    
    logger.info("=" * 60)
    logger.info("🔍 开始字幕位置检测")
    logger.info("=" * 60)
    try:
        # 使用新的字幕检测逻辑
        subtitle_position = detect_subtitle_position(
            video_path=video_abs_path,
            num_frames=30  # 检测30帧
        )

        if subtitle_position:
            logger.info("=" * 60)
            logger.info("✅ 字幕位置检测成功")
            
            # 将像素坐标转换为剪映坐标系统（用于字幕位置）
            normalized_y = subtitle_position['center_y'] / canvas_height
            subtitle_position_y = 1 - (normalized_y * 2)
            logger.info(f"   剪映坐标 Y: {subtitle_position_y:.3f}")
        else:
            logger.warning("❌ 字幕检测失败，使用默认位置")
    except Exception as e:
        logger.error(f"字幕位置检测失败: {e}")
        logger.warning("将使用默认字幕位置")
        import traceback
        logger.error(traceback.format_exc())
    
    # === 创建字幕材料和轨道 ===
    text_materials = []
    text_tracks = []
    
    if audio_dir:
        try:
            subtitle_output_dir = batch_convert_mp3_to_srt(audio_dir, subtitle_dir)

            subtitle_path = Path(subtitle_output_dir)
            srt_files = sorted([str(f) for f in subtitle_path.glob("*.srt")])
            
            # 解析字幕文件并创建字幕片段
            text_segments = []
            logger.info("")

            for idx, (target_start, target_end, source_start, source_end) in enumerate(audio_video_mapping):
                # 每个音频片段对应一个字幕文件
                if idx >= len(srt_files):
                    logger.warning(f"⚠️  音频片段 [{idx+1}] 没有对应的字幕文件")
                    break

                srt_file_path = srt_files[idx]
                logger.info(f"📄 [{idx+1}/{len(audio_video_mapping)}] {Path(srt_file_path).name}")

                # 解析字幕文件
                srt_clips = parse_srt(srt_file_path)

                if not srt_clips:
                    logger.warning(f"   ⚠️  字幕文件为空，跳过")
                    continue

                # 为每个字幕行创建材料和片段
                for sub_start, sub_end, sub_text in srt_clips:
                    text_id = gen_id()

                    # 计算字幕在时间轴上的位置（相对于当前音频片段）
                    subtitle_start = target_start + sub_start
                    subtitle_duration = sub_end - sub_start

                    # 确保字幕不超出音频片段范围
                    if subtitle_start + subtitle_duration > target_end:
                        subtitle_duration = target_end - subtitle_start

                    if subtitle_duration <= 0:
                        continue

                    # 创建字幕材料
                    text_material = create_text_material(
                        text_id=text_id,
                        text_content=sub_text.strip()
                    )
                    text_materials.append(text_material)

                    # 创建字幕片段（使用检测到的位置）
                    text_segment = create_text_segment(
                        text_id=text_id,
                        start_time=subtitle_start,
                        duration=subtitle_duration,
                        position_y=subtitle_position_y
                    )
                    text_segments.append(text_segment)

                logger.info(f"   ✅ 添加了 {len(srt_clips)} 个字幕")
            
            # 在循环外创建字幕轨道（只创建一个轨道，包含所有字幕片段）
            if text_segments:
                text_track = {
                    "attribute": 0,
                    "flag": 0,
                    "id": gen_id(),
                    "is_default_name": True,
                    "name": "",
                    "segments": text_segments,
                    "type": "text"
                }
                text_tracks.append(text_track)
                logger.info("")
                logger.info(f"✅ 字幕轨道创建成功")
                logger.info(f"   总字幕数: {len(text_segments)}")
                logger.info(f"   字幕材料数: {len(text_materials)}")
                
        except Exception as e:
            logger.error(f"字幕处理失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # === 创建字幕蒙版和模糊效果 ===
    mask_material = None
    blur_effect_material = None
    background_video_segments = []  # 背景视频轨道（带模糊和蒙版）

    if subtitle_position:
        try:
            # 创建蒙版材料
            mask_id = gen_id()
            mask_material = create_rectangle_mask(
                mask_id=mask_id,
                subtitle_center_y=subtitle_position_y,
                subtitle_height=subtitle_position['height'],
                canvas_height=canvas_height
            )

            # 创建模糊特效材料
            blur_effect_id = gen_id()
            blur_effect_material = create_blur_effect(blur_effect_id, intensity=80.0)

            # === 创建背景视频轨道（复制主轨道的片段，并添加模糊和蒙版）===
            for idx, (target_start, target_end, source_start, source_end) in enumerate(audio_video_mapping):
                duration = target_end - target_start
                bg_segment = create_base_segment()
                
                # 构建 extra_material_refs（如果有转场，转场ID在最前面）
                bg_extra_refs = []
                if transition_ids[idx]:
                    bg_extra_refs.append(transition_ids[idx])
                bg_extra_refs.extend([speed_id, blur_effect_id, mask_id])
                
                bg_segment.update({
                    "id": gen_id(),
                    "material_id": video_mat_id,
                    "target_timerange": {"start": target_start, "duration": duration},
                    "source_timerange": {"start": source_start, "duration": duration},
                    "volume": 0.0,  # 背景视频静音
                    "extra_material_refs": bg_extra_refs,  # 引用转场、特效和蒙版
                    "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
                    "track_render_index": 0  # 背景轨道（在上层）
                })
                background_video_segments.append(bg_segment)

        except Exception as e:
            logger.error(f"创建字幕蒙版失败: {e}")
            logger.warning("将不使用字幕蒙版功能")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.info("⚠️  跳过字幕蒙版创建（字幕检测未成功）")

    # === 创建视频轨道 ===
    all_video_tracks = []
    
    # 主视频轨道（在底层，干净的视频）
    all_video_tracks.append(video_track)
    
    # 背景视频轨道（在上层，带模糊和蒙版）
    background_track = {
        "attribute": 0,
        "flag": 0,
        "id": gen_id(),
        "is_default_name": False,
        "name": "背景视频轨道（模糊蒙版）",
        "segments": background_video_segments,
        "type": "video"
    }
    all_video_tracks.append(background_track)

    # === 组装项目 ===
    project = generate_project_data(
        video_mat_id=video_mat_id,
        speed_id=speed_id,
        total_duration=total_duration,
        project_id=project_id,
        audio_materials=audio_materials,
        video_tracks=all_video_tracks,  # 传入所有视频轨道
        audio_tracks=audio_tracks,
        video_filename=video_filename,
        video_abs_path=video_abs_path,
        aspect_ratio=aspect_ratio,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        mask_material=mask_material,
        blur_effect_material=blur_effect_material,
        text_materials=text_materials,
        text_tracks=text_tracks,
        transition_materials=transition_materials  # 传入转场材料
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
    logger.info(f"视频片段: {len(video_segments)} 个 | 音频片段: {len(audio_segments)} 个 | 总时长: {total_duration / 1000000:.2f} 秒")
    logger.info(f"视频轨道数: {len(all_video_tracks)} | 音频轨道数: {len(audio_tracks)} | 字幕轨道数: {len(text_tracks)}")
    if text_tracks and text_tracks[0]['segments']:
        logger.info(f"字幕片段: {len(text_tracks[0]['segments'])} 个")
    logger.info(f"转场效果: {len(transition_materials)} 个")

if __name__ == "__main__":
    # generate_audio_from_srt(
    #     srt_file="C:/Users/leidc/Desktop/workspace/srt_files/jieShuo/20251201_131444.txt",
    #     reference_audio="resources/src/audios/xiao_shuai/爆款小帅男声.MP3",
    #     output_dir="C:/Users/leidc/Desktop/workspace/audios/test/",
    #     model=config.get('tts.model'),
    #     speed=config.get('tts.speed')
    # )
    # logger.info(f"✅ 音频生成完成!")

    # 生成剪映项目文件（自动转换音频为字幕）
    generate_capcut_project(
        video_file="C:/Users/leidc/Desktop/workspace/videos/20251201_131444.mp4",
        audio_pattern=str("C:/Users/leidc/Desktop/workspace/audios/20251201_132114/" + Path(config.get('audio.pattern')).name),
        srt_file="C:/Users/leidc/Desktop/workspace/srt_files/jieShuo/20251201_132114.txt",
        output_dir="C:/Users/leidc/Desktop/workspace/json/test/",
        audio_dir="C:/Users/leidc/Desktop/workspace/audios/20251201_132114/",  # 音频目录
        subtitle_dir="C:/Users/leidc/Desktop/workspace/srt_files/subtitles"  # 字幕基础目录
    )
    
    logger.info(f"✅ 剪映项目生成完成!")