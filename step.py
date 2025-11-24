"""
视频处理主流程
整合 AI 剪辑、视频编辑、AI 解说、音频生成和剪映项目生成
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dify.workflows import run_editing_workflow, run_commentary_workflow
from utils.text_to_srt import text_to_srt
from core.video_editing import edit_video
from core.gen_json import generate_capcut_project, generate_audio_from_srt
from utils.config_loader import get_config
from services.video_to_audio import convert_video_to_audio
from services.audio_to_subtitles import transcribe_audio, create_srt
from utils.fresh_timeline import fresh_timeline
from utils.loggers import get_logger
from utils.jianying_drafts import copy_project_to_directory

# 加载配置
config = get_config()

# 默认解说参数
DEFAULT_COMMENTARY_PLOT = """
未指定剧情，请根据字幕文件分析。
""".strip()
DEFAULT_VIDEO_TYPE = "都市爱情"

# 获取日志记录器（静默模式，避免重复打印初始化信息）
logger = get_logger('main', silent=True)


# ========== 步骤 1：视频转音频 ==========
def step1_video_to_audio() -> Dict[str, Any]:
    """
    步骤 1：将视频转换为音频
    
    Returns:
        包含 video_src_path 和 audio_output_path 的字典
    """
    logger.info("=" * 80)
    logger.info("【步骤 1/9】将视频转换为音频...")
    logger.info("=" * 80)
    
    # 获取原始视频路径
    video_src = config.get("video.src")
    video_src_path = Path(config.get_absolute_path(video_src))
    
    if not video_src_path.exists():
        logger.error(f"视频文件不存在: {video_src_path}")
        raise FileNotFoundError(f"视频文件不存在: {video_src_path}")
    
    # 设置音频输出路径（与 videos 目录同级的 audios 目录）
    audio_output_path = video_src_path.parent.parent / "audios" / f"{video_src_path.stem}.mp3"
    audio_output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 检查音频文件是否已存在
    if audio_output_path.exists():
        logger.info(f"⏭️  音频文件已存在，跳过转换: {audio_output_path}")
    else:
        # 转换视频为音频
        convert_video_to_audio(video_src_path, audio_output_path)
        logger.info(f"✅ 视频转音频完成: {audio_output_path}")
    
    return {
        "video_src_path": video_src_path,
        "audio_output_path": audio_output_path
    }


# ========== 步骤 2：音频转字幕 ==========
def step2_audio_to_subtitles(audio_output_path: Path, video_src_path: Path) -> Dict[str, Any]:
    """
    步骤 2：将音频转换为字幕
    
    Args:
        audio_output_path: 音频文件路径
        video_src_path: 原始视频路径（用于命名）
    
    Returns:
        包含 srt_output_path, txt_output_path, original_text 的字典
    """
    logger.info("=" * 80)
    logger.info("【步骤 2/9】将音频转换为字幕...")
    logger.info("=" * 80)
    
    # 设置字幕输出路径
    srt_output_path = video_src_path.parent.parent / "srt_files" / f"{video_src_path.stem}.txt"
    srt_output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 检查字幕文件和文本文件是否已存在
    if srt_output_path.exists():
        logger.info(f"⏭️  字幕文件已存在，跳过转换:")
        logger.info(f"   - SRT: {srt_output_path}")
    else:
        # 调用语音识别API转录音频
        api_url = "http://116.211.238.68:8881/api/v1/transcribe"
        transcription_result = transcribe_audio(str(audio_output_path), api_url)
        
        # 生成SRT字幕文件
        create_srt(transcription_result, str(srt_output_path))

        logger.info(f"✅ 音频转字幕完成:")
        logger.info(f"   - SRT: {srt_output_path}")

    # 读取生成的文本内容，作为AI工作流的输入
    with open(srt_output_path, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    return {
        "srt_output_path": srt_output_path,
        "original_text": original_text
    }


# ========== 步骤 3：AI 剪辑工作流 ==========
def step3_ai_editing_workflow(original_text: str) -> str:
    """
    步骤 3：运行 AI 剪辑工作流
    
    Args:
        original_text: 识别出的原始文本内容
    
    Returns:
        AI 生成的剪辑文本
    """
    logger.info("=" * 80)
    logger.info("【步骤 3/9】运行 AI 剪辑工作流...")
    logger.info("=" * 80)

    # 准备剪辑工作流的输入参数
    editing_inputs = {
        "long_lines": original_text
    }
    
    # 调用剪辑工作流
    editing_text = run_editing_workflow(editing_inputs)
    logger.info("✅ AI 剪辑工作流执行完成")
    return editing_text


# ========== 步骤 4：剪辑文本转 SRT ==========
def step4_editing_text_to_srt(editing_text: str) -> str:
    """
    步骤 4：将剪辑文本转换为 SRT 字幕文件
    
    Args:
        editing_text: AI 生成的剪辑文本
    
    Returns:
        剪辑 SRT 文件路径
    """
    logger.info("=" * 80)
    logger.info("【步骤 4/9】将剪辑文本转换为 SRT 字幕文件...")
    logger.info("=" * 80)
    
    clip_srt_file = text_to_srt(
        srt_string=editing_text,
        output_dir="resources/dst/srt_files/clip"
    )
    logger.info(f"✅ 剪辑文本转SRT完成: {clip_srt_file}")
    return clip_srt_file


# ========== 步骤 5：根据 SRT 剪辑视频 ==========
def step5_edit_video(clip_srt_file: str) -> str:
    """
    步骤 5：根据 SRT 字幕剪辑视频
    
    Args:
        clip_srt_file: 剪辑 SRT 文件路径
    
    Returns:
        剪辑后的视频文件路径
    """
    logger.info("=" * 80)
    logger.info("【步骤 5/9】根据 SRT 字幕剪辑视频...")
    logger.info("=" * 80)
    
    # 转换为绝对路径
    video_src = config.get("video.src")
    video_src_path = config.get_absolute_path(video_src)
    
    edited_video = edit_video(clip_srt_file, video_src_path)
    if not edited_video:
        logger.error("视频剪辑失败，请查看上面的详细错误信息")
        raise RuntimeError("视频剪辑失败，请查看上面的详细错误信息")
    
    logger.info(f"✅ 视频剪辑完成: {edited_video}")
    return edited_video


# ========== 步骤 6：刷新时间戳 ==========
def step6_refresh_timeline(clip_srt_file: str) -> str:
    """
    步骤 6：刷新剪辑 SRT 时间戳
    
    Args:
        clip_srt_file: 原始剪辑 SRT 文件路径
    
    Returns:
        刷新后的 SRT 文件路径
    """
    logger.info("=" * 80)
    logger.info("【步骤 6/9】刷新剪辑 SRT 时间戳...")
    logger.info("=" * 80)
    
    # 生成新的 SRT 文件路径
    clip_srt_path = Path(clip_srt_file)
    refreshed_clip_srt = str(clip_srt_path.parent / f"{clip_srt_path.stem}_fresh.txt")
    
    # 刷新时间戳，从 00:00:00,000 开始
    fresh_timeline(clip_srt_file, refreshed_clip_srt)
    logger.info(f"✅ 时间戳刷新完成: {refreshed_clip_srt}")
    return refreshed_clip_srt


# ========== 步骤 7：AI 解说工作流 ==========
def step7_ai_commentary_workflow(
    clip_srt_file: str,
    plot: Optional[str] = None,
    video_type: Optional[str] = None,
    long_commentary_path: Optional[str] = None
) -> str:
    """
    步骤 7：运行 AI 解说工作流
    
    Args:
        clip_srt_file: 剪辑 SRT 文件路径

    Returns:
        AI 生成的解说文本
    """
    logger.info("=" * 80)
    logger.info("【步骤 7/9】运行 AI 解说工作流...")
    logger.info("=" * 80)
    
    # 读取剪辑 SRT 文件内容
    with open(clip_srt_file, 'r', encoding='utf-8') as f:
        clip_srt_content = f.read()
    
    # 读取 long_commentary 示例文件内容（支持自定义文件覆盖）
    default_long_commentary_path = config.get("srt_file.jieShuo_example")
    long_commentary_abs_path = Path(config.get_absolute_path(default_long_commentary_path))
    
    def _read_long_commentary(target_path: Path) -> Optional[str]:
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"长解说示例文件不存在: {target_path}")
        except Exception as exc:
            logger.error(f"读取长解说示例文件失败 ({target_path}): {exc}")
        return None
    
    long_commentary_content = _read_long_commentary(long_commentary_abs_path) or ""
    
    if long_commentary_path:
        custom_path = Path(config.get_absolute_path(long_commentary_path))
        custom_content = _read_long_commentary(custom_path)
        if custom_content:
            long_commentary_content = custom_content
        else:
            logger.warning("自定义长解说文件读取失败，继续使用默认示例内容")
    
    # 准备解说工作流的输入参数
    commentary_inputs = {
        "plot": plot or DEFAULT_COMMENTARY_PLOT,
        "short_copy": clip_srt_content,
        "video_type": video_type or DEFAULT_VIDEO_TYPE,
        "long_commentary": long_commentary_content
    }
    
    # 调用解说工作流
    commentary_text = run_commentary_workflow(commentary_inputs)
    logger.info("✅ AI 解说工作流执行完成")
    return commentary_text


# ========== 步骤 8：解说文本转 SRT ==========
def step8_commentary_text_to_srt(commentary_text: str) -> str:
    """
    步骤 8：将解说文本转换为 SRT 字幕文件
    
    Args:
        commentary_text: AI 生成的解说文本
    
    Returns:
        解说 SRT 文件路径
    """
    logger.info("=" * 80)
    logger.info("【步骤 8/9】将解说文本转换为 SRT 字幕文件...")
    logger.info("=" * 80)
    
    commentary_srt_file = text_to_srt(
        srt_string=commentary_text,
        output_dir="resources/dst/srt_files/jieShuo"
    )
    logger.info(f"✅ 解说文本转SRT完成: {commentary_srt_file}")
    return commentary_srt_file


# ========== 步骤 9：生成剪映项目 ==========
def step9_generate_capcut_project(edited_video: str, commentary_srt_file: str) -> str:
    """
    步骤 9：生成剪映项目 JSON 文件
    
    Args:
        edited_video: 剪辑后的视频路径
        commentary_srt_file: 解说 SRT 文件路径
    """
    logger.info("=" * 80)
    logger.info("【步骤 9/10】生成剪映项目 JSON 文件...")
    logger.info("=" * 80)
    
    # 获取音频配置
    audio_pattern = config.get('audio.pattern')
    audio_output_dir = config.get('audio.output_dir')
    output_json_dir = config.get('output.json_dir')
    reference_audio = config.get('tts.reference_audio')
    tts_model = config.get('tts.model')
    tts_speed = config.get('tts.speed')

    # 为音频和 JSON 生成统一的时间戳目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_run_dir = Path(audio_output_dir) / timestamp
    audio_run_dir_str = str(audio_run_dir)
    json_run_dir = str(Path(output_json_dir) / timestamp)

    # 更新音频命名模式，使其指向当前时间目录
    audio_pattern_name = Path(audio_pattern).name
    audio_pattern_for_run = str(audio_run_dir / audio_pattern_name)

    audio_abs_dir = config.get_absolute_path(audio_run_dir_str)
    
    # 根据解说 SRT 生成音频文件
    generate_audio_from_srt(
        srt_file=commentary_srt_file,
        reference_audio=reference_audio,
        output_dir=audio_run_dir_str,
        model=tts_model,
        speed=tts_speed
    )
    logger.info(f"✅ 音频生成完成: {audio_abs_dir}")
    
    # 生成剪映项目文件
    generate_capcut_project(
        video_file=edited_video,
        audio_pattern=audio_pattern_for_run,
        srt_file=commentary_srt_file,
        output_dir=json_run_dir
    )
    logger.info(f"✅ 剪映项目生成完成: {config.get_absolute_path(json_run_dir)}")
    
    return json_run_dir


# ========== 步骤 10：复制项目到桌面 ==========
def step10_copy_project_to_destination(project_json_dir: str, destination_dir: str) -> str:
    """
    步骤 10：将生成的剪映项目复制到桌面 JianyingPro Drafts 目录
    
    Args:
        project_json_dir: 剪映项目 JSON 输出目录
    
    Returns:
        桌面目标目录绝对路径
    """
    logger.info("=" * 80)
    logger.info("【步骤 10/10】复制剪映项目到指定导出目录...")
    logger.info("=" * 80)
    
    if not destination_dir:
        raise ValueError("未设置导出目录，请先在 UI 中选择一个目标文件夹")
    
    exported_path = copy_project_to_directory(project_json_dir, destination_dir)
    logger.info(f"✅ 剪映项目已复制到目标目录: {exported_path}")
    return exported_path


# ========== 主控制函数 ==========
def run_pipeline(
    start_step: int = 1,
    end_step: int = 10,
    step_data: Optional[Dict[str, Any]] = None,
    export_destination_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    运行视频处理流水线
    
    Args:
        start_step: 起始步骤（1-10）
        end_step: 结束步骤（1-10）
        step_data: 如果从中间步骤开始，需要提供前置步骤的数据
                  例如从步骤3开始: {"original_text": "..."}
                  例如从步骤5开始: {"clip_srt_file": "path/to/file.srt"}
    
    Returns:
        所有步骤生成的数据字典
    """
    if step_data is None:
        step_data = {}
    
    if export_destination_dir:
        step_data["export_destination_dir"] = export_destination_dir
    elif "export_destination_dir" not in step_data:
        # 默认使用桌面目录
        step_data["export_destination_dir"] = str((Path.home() / "Desktop").resolve())
    
    # 步骤 1：视频转音频
    if start_step <= 1 <= end_step:
        result = step1_video_to_audio()
        step_data.update(result)
    
    # 步骤 2：音频转字幕
    if start_step <= 2 <= end_step:
        if "audio_output_path" not in step_data or "video_src_path" not in step_data:
            raise ValueError("步骤2需要: audio_output_path, video_src_path")
        result = step2_audio_to_subtitles(
            step_data["audio_output_path"],
            step_data["video_src_path"]
        )
        step_data.update(result)
    
    # 步骤 3：AI 剪辑工作流
    if start_step <= 3 <= end_step:
        if "original_text" not in step_data:
            raise ValueError("步骤3需要: original_text")
        editing_text = step3_ai_editing_workflow(step_data["original_text"])
        step_data["editing_text"] = editing_text
    
    # 步骤 4：剪辑文本转 SRT
    if start_step <= 4 <= end_step:
        if "editing_text" not in step_data:
            raise ValueError("步骤4需要: editing_text")
        clip_srt_file = step4_editing_text_to_srt(step_data["editing_text"])
        step_data["original_clip_srt"] = clip_srt_file
        step_data["clip_srt_file"] = clip_srt_file
    
    # 步骤 5：根据 SRT 剪辑视频
    if start_step <= 5 <= end_step:
        if "clip_srt_file" not in step_data:
            raise ValueError("步骤5需要: clip_srt_file")
        edited_video = step5_edit_video(step_data["clip_srt_file"])
        step_data["edited_video"] = edited_video
    
    # 步骤 6：刷新时间戳
    if start_step <= 6 <= end_step:
        if "clip_srt_file" not in step_data:
            raise ValueError("步骤6需要: clip_srt_file")
        refreshed_clip_srt = step6_refresh_timeline(step_data["clip_srt_file"])
        step_data["refreshed_clip_srt"] = refreshed_clip_srt
        step_data["clip_srt_file"] = refreshed_clip_srt  # 更新为刷新后的文件
    
    # 步骤 7：AI 解说工作流
    if start_step <= 7 <= end_step:
        if "clip_srt_file" not in step_data:
            raise ValueError("步骤7需要: clip_srt_file")
        commentary_text = step7_ai_commentary_workflow(
            step_data["clip_srt_file"]
        )
        step_data["commentary_text"] = commentary_text
    
    # 步骤 8：解说文本转 SRT
    if start_step <= 8 <= end_step:
        if "commentary_text" not in step_data:
            raise ValueError("步骤8需要: commentary_text")
        commentary_srt_file = step8_commentary_text_to_srt(step_data["commentary_text"])
        step_data["commentary_srt_file"] = commentary_srt_file
    
    # 步骤 9：生成剪映项目
    if start_step <= 9 <= end_step:
        if "edited_video" not in step_data or "commentary_srt_file" not in step_data:
            raise ValueError("步骤9需要: edited_video, commentary_srt_file")
        project_json_dir = step9_generate_capcut_project(
            step_data["edited_video"],
            step_data["commentary_srt_file"]
        )
        step_data["project_json_dir"] = project_json_dir
    
    # 步骤 10：复制剪映项目到桌面
    if start_step <= 10 <= end_step:
        if "project_json_dir" not in step_data:
            raise ValueError("步骤10需要: project_json_dir")
        if "export_destination_dir" not in step_data:
            raise ValueError("步骤10需要: export_destination_dir")
        desktop_project_path = step10_copy_project_to_destination(
            step_data["project_json_dir"],
            step_data["export_destination_dir"]
        )
        step_data["desktop_project_path"] = desktop_project_path
    
    return step_data


if __name__ == "__main__":
    # 初始化日志系统
    from utils.loggers import get_app_logger
    get_app_logger()
    
    # 选项 1：运行完整流程（步骤 1-10）
    result = run_pipeline(start_step=1, end_step=10)
    
    # 选项 2：从步骤 7 开始运行（AI 解说工作流 → 生成剪映项目）
    # result = run_pipeline(
    #     start_step=7,
    #     end_step=9,
    #     step_data={
    #         "clip_srt_file": "resources/dst/srt_files/clip/20251118_173118_fresh.txt",  # 剪辑字幕文件
    #         "edited_video": "resources/dst/videos/final_clip.mp4"  # 剪辑后的视频文件
    #     }
    # )
