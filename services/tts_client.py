import os
import time
import base64
import mimetypes
import sys
from pathlib import Path
from urllib.parse import urlparse
import requests
import subprocess

# 添加utils目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.config_loader import get_config
from utils.loggers import get_logger

# ==================== 加载配置 ====================
config = get_config()
logger = get_logger('tts_client', silent=True)

# API 配置
API_BASE = config.get('tts.api.base_url')
SUBMIT_URL = f"{API_BASE}{config.get('tts.api.submit_endpoint')}"
STATUS_URL_TMPL = f"{API_BASE}{config.get('tts.api.status_endpoint')}"
API_KEY = config.get('tts.api.api_key')
DEFAULT_MODEL = config.get('tts.model')

# 用户配置
SRT_FILE = config.get('subtitle.srt_file')
REFERENCE_AUDIO = config.get('tts.reference_audio')
SPEED = config.get('tts.speed')
FFMPEG_PATH = config.get('ffmpeg.ffmpeg_path')

# 轮询配置
POLL_INTERVAL_SEC = config.get('tts.polling.interval_sec', 2.0)
POLL_TIMEOUT_SEC = config.get('tts.polling.timeout_sec', 300)


def ensure_output_dir(dir_path: str) -> None:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)


def parse_srt(srt_file_path: str) -> list[dict]:
    """解析SRT字幕文件，返回字幕列表"""
    if not os.path.exists(srt_file_path):
        raise FileNotFoundError(f"SRT 文件不存在：{srt_file_path}")
    
    subtitles = []
    with open(srt_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue
        
        text = "\n".join(lines[2:]).strip()
        if text:
            subtitles.append({"index": index, "text": text})
    
    return subtitles


def submit_tts(text: str, model: str, reference_file_path: str | None = None) -> str:
    """提交TTS任务，返回task_id"""
    headers = {"X-API-KEY": API_KEY}
    files: dict[str, tuple | None] = {
        "text": (None, text),
        "model": (None, model),
    }
    
    file_handle = None
    try:
        if reference_file_path:
            mime_type = mimetypes.guess_type(reference_file_path)[0] or "application/octet-stream"
            file_handle = open(reference_file_path, "rb")
            files["files"] = (os.path.basename(reference_file_path), file_handle, mime_type)
        
        resp = requests.post(SUBMIT_URL, headers=headers, files=files)
    finally:
        if file_handle:
            file_handle.close()
    
    resp.raise_for_status()
    data = resp.json()
    
    task_id = (
        data.get("task_id") or 
        (data.get("data", {}) or {}).get("task_id") or 
        (data.get("result", {}) or {}).get("task_id")
    )
    if not task_id:
        raise RuntimeError(f"提交失败，未获得 task_id，返回：{data}")
    return task_id


def poll_status(task_id: str, poll_interval_sec: float = None, timeout_sec: int = None) -> dict:
    """轮询任务状态直到完成或超时"""
    if poll_interval_sec is None:
        poll_interval_sec = POLL_INTERVAL_SEC
    if timeout_sec is None:
        timeout_sec = POLL_TIMEOUT_SEC
    
    headers = {"X-API-KEY": API_KEY}
    status_url = STATUS_URL_TMPL.format(task_id=task_id)
    deadline = time.time() + timeout_sec

    while True:
        resp = requests.get(status_url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status") or (data.get("data", {}) or {}).get("status")
        result = data.get("result") or (data.get("data", {}) or {}).get("result") or data

        if status in {"success", "finished", "done", "completed"}:
            return result if isinstance(result, dict) else {"result": result}
        if status in {"failed", "error"}:
            raise RuntimeError(f"任务失败：{data}")

        if time.time() > deadline:
            raise TimeoutError(f"查询超时（{timeout_sec}s）")

        time.sleep(poll_interval_sec)


def save_audio_from_url(url: str, out_dir: str, subtitle_index: int) -> str:
    """从URL下载音频并保存"""
    resp = requests.get(url)
    resp.raise_for_status()
    
    # 获取扩展名
    ext = os.path.splitext(urlparse(url).path)[1] or ".wav"
    if "Content-Type" in resp.headers:
        ext = mimetypes.guess_extension(resp.headers.get("Content-Type")) or ext
    
    out_path = os.path.join(out_dir, f"{subtitle_index:04d}{ext}")
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def save_audio_from_base64(b64_str: str, out_dir: str, subtitle_index: int, fmt: str | None = None) -> str:
    """从Base64字符串保存音频"""
    ext = f".{fmt}" if fmt else ".wav"
    out_path = os.path.join(out_dir, f"{subtitle_index:04d}{ext}")
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64_str))
    return out_path


def _build_atempo_chain(speed: float) -> str:
    """将任意倍速拆分为ffmpeg atempo允许的0.5~2.0段"""
    if speed <= 0:
        raise ValueError("倍速需为正数")
    
    filters = []
    remaining = speed
    
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    
    while 0 < remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    
    if abs(remaining - 1.0) > 1e-6:
        filters.append(f"atempo={remaining:.6f}")
    
    return ",".join(filters) or "atempo=1.0"


def apply_speed_with_ffmpeg(input_path: str, speed: float) -> str:
    """使用ffmpeg对音频进行倍速处理并覆盖原文件"""
    if abs(speed - 1.0) <= 1e-6:
        return input_path

    base_dir = os.path.dirname(input_path)
    base_name, ext = os.path.splitext(os.path.basename(input_path))
    temp_out_path = os.path.join(base_dir, f"{base_name}.__tmp_speed{ext}")

    filter_chain = _build_atempo_chain(speed)
    cmd = [
        FFMPEG_PATH,
        "-v", "error",
        "-y",
        "-i", input_path,
        "-filter:a", filter_chain,
        "-vn",
        temp_out_path,
    ]
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creation_flags,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except FileNotFoundError:
        return input_path

    if proc.returncode != 0:
        return input_path

    try:
        os.replace(temp_out_path, input_path)
    except Exception as e:
        return input_path

    return input_path


def extract_and_save_audio(result_json: dict, out_dir: str, subtitle_index: int) -> str:
    """从API返回结果中提取并保存音频"""
    candidates = []
    
    # 检查URL类字段
    for key in ["audio_url", "url", "file", "result_url"]:
        if key in result_json and isinstance(result_json[key], str):
            candidates.append(("url", result_json[key]))
    
    # 检查文件列表
    if isinstance(result_json.get("files"), list):
        for item in result_json["files"]:
            if isinstance(item, str):
                candidates.append(("url", item))
            elif isinstance(item, dict) and "url" in item:
                candidates.append(("url", item["url"]))
    
    # 检查Base64类字段
    for key in ["audio_base64", "audios"]:
        if key in result_json and isinstance(result_json[key], str):
            fmt = result_json.get("format") or result_json.get("ext")
            candidates.append(("b64", result_json[key], fmt))

    if not candidates:
        nested = result_json.get("data") or result_json.get("result")
        if isinstance(nested, dict):
            return extract_and_save_audio(nested, out_dir, subtitle_index)
        raise RuntimeError(f"未找到音频字段：{result_json}")

    kind = candidates[0][0]
    if kind == "url":
        return save_audio_from_url(candidates[0][1], out_dir, subtitle_index)
    else:  # b64
        b64_str = candidates[0][1]
        fmt = candidates[0][2] if len(candidates[0]) > 2 else None
        return save_audio_from_base64(b64_str, out_dir, subtitle_index, fmt)


def process_subtitle(subtitle: dict, model: str, reference_file: str, out_dir: str, speed: float, file_index: int) -> str:
    """处理单条字幕的TTS任务"""
    index = subtitle["index"]
    text = subtitle["text"]
    
    # 提交任务
    task_id = submit_tts(text, model, reference_file_path=reference_file)
    
    # 轮询状态
    result_json = poll_status(task_id)
    
    # 保存音频（使用递增的 file_index 而不是字幕原始序号）
    out_path = extract_and_save_audio(result_json, out_dir, file_index)
    
    # 倍速处理
    if abs(speed - 1.0) > 1e-6:
        out_path = apply_speed_with_ffmpeg(out_path, speed)
    
    return out_path


def main():
    script_dir = Path(__file__).parent.parent
    
    # 解析SRT文件
    srt_path = config.get_absolute_path(SRT_FILE)
    subtitles = parse_srt(srt_path)
    logger.info(f"找到 {len(subtitles)} 条字幕")
    
    # 检查参考音频
    reference_audio_path = config.get_absolute_path(REFERENCE_AUDIO)
    if not os.path.exists(reference_audio_path):
        logger.error(f"参考音频不存在：{reference_audio_path}")
        return
    
    # 创建输出目录
    out_dir = config.get_absolute_path(config.get('audio.output_dir'))
    ensure_output_dir(out_dir)
    
    # 处理每条字幕
    success_count = 0
    for file_index, subtitle in enumerate(subtitles, start=1):
        try:
            process_subtitle(subtitle, DEFAULT_MODEL, reference_audio_path, out_dir, SPEED, file_index)
            success_count += 1
        except Exception as e:
            logger.error(f"字幕 {subtitle['index']} 处理失败：{e}")
    
    # 总结
    logger.info(f"完成：{success_count}/{len(subtitles)} 个音频文件")


if __name__ == "__main__":
    main()


