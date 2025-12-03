import numpy as np
import subprocess
import re
import os


def parse_srt_time(time_str):
    """
    解析SRT时间格式 (HH:MM:SS,mmm) 为秒数
    
    参数:
        time_str: 时间字符串，如 "00:05:11,320"
    
    返回:
        float: 时间（秒）
    """
    # 格式: HH:MM:SS,mmm
    time_str = time_str.strip()
    time_part, ms_part = time_str.split(',')
    h, m, s = map(int, time_part.split(':'))
    ms = int(ms_part)
    
    return h * 3600 + m * 60 + s + ms / 1000


def format_srt_time(seconds):
    """
    将秒数转换为SRT时间格式
    
    参数:
        seconds: 时间（秒）
    
    返回:
        str: SRT格式时间字符串
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt_file(srt_path):
    """
    解析SRT文件
    
    返回:
        list: [(序号, 开始时间, 结束时间, 字幕文本), ...]
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 分割各个字幕块
    blocks = re.split(r'\n\s*\n', content.strip())
    
    subtitles = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2:
            # 序号
            index = lines[0].strip()
            # 时间戳
            time_line = lines[1].strip()
            match = re.match(r'(\S+)\s*-->\s*(\S+)', time_line)
            if match:
                start_time_str = match.group(1)
                end_time_str = match.group(2)
                start_time = parse_srt_time(start_time_str)
                end_time = parse_srt_time(end_time_str)
                # 字幕文本（如果有的话）
                text = '\n'.join(lines[2:]) if len(lines) > 2 else ""
                subtitles.append((index, start_time, end_time, text))
    
    return subtitles


def analyze_audio_segment(audio_path, start_time, end_time, chunk_length_ms=100):
    """
    分析音频片段，返回每个小块的音量
    
    参数:
        audio_path: 音频文件路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        chunk_length_ms: 分析的时间块长度（毫秒）
    
    返回:
        tuple: (时间点列表, 音量列表)
    """
    # 使用ffmpeg提取音频片段
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    ffmpeg_path = str(project_root / "resources" / "src" / "ffmpeg" / "ffmpeg.exe")
    
    duration = end_time - start_time
    
    cmd = [
        ffmpeg_path,
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", audio_path,
        "-f", "s16le",   # 16位小端格式
        "-ac", "1",      # 单声道
        "-ar", "44100",  # 采样率44100Hz
        "-"
    ]
    
    # 执行ffmpeg并获取音频数据（Windows 下隐藏命令行窗口）
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=creation_flags)
    samples = np.frombuffer(result.stdout, dtype=np.int16)
    
    if len(samples) == 0:
        return [], []
    
    # 计算分块参数
    sample_rate = 44100
    chunk_size = int(sample_rate * chunk_length_ms / 1000)
    num_chunks = len(samples) // chunk_size
    
    # 分析每个音频块，计算音量
    volumes = []
    times = []
    for i in range(num_chunks):
        chunk = samples[i * chunk_size:(i + 1) * chunk_size]
        rms = np.sqrt(np.mean(chunk.astype(np.float64)**2))
        volume_db = 20 * np.log10(rms / 32768) if rms > 0 else -96  # 静音设为-96dB
        volumes.append(volume_db)
        times.append(start_time + i * chunk_length_ms / 1000)
    
    return times, volumes


def find_low_volume_segments(times, volumes, threshold_db=-50, min_duration_sec=0.3):
    """
    找到低音量片段
    
    参数:
        times: 时间点列表
        volumes: 音量列表
        threshold_db: 音量阈值（dBFS），低于此值视为低音量
        min_duration_sec: 最小持续时间（秒），只保留持续时间超过此值的低音量片段
    
    返回:
        list: [(开始时间, 结束时间), ...] 低音量片段列表
    """
    if len(times) == 0:
        return []
    
    low_segments = []
    in_low_segment = False
    segment_start = None
    
    chunk_duration = times[1] - times[0] if len(times) > 1 else 0.1
    
    for i, (t, v) in enumerate(zip(times, volumes)):
        if v < threshold_db:
            if not in_low_segment:
                in_low_segment = True
                segment_start = t
        else:
            if in_low_segment:
                segment_end = t
                # 检查持续时间
                if segment_end - segment_start >= min_duration_sec:
                    low_segments.append((segment_start, segment_end))
                in_low_segment = False
                segment_start = None
    
    # 处理最后一个片段
    if in_low_segment and segment_start is not None:
        segment_end = times[-1] + chunk_duration
        if segment_end - segment_start >= min_duration_sec:
            low_segments.append((segment_start, segment_end))
    
    return low_segments


def split_subtitle_by_low_volume(subtitle, audio_path, threshold_db=-50, min_duration_sec=0.3, chunk_length_ms=100):
    """
    根据低音量将字幕拆分成多个片段
    
    参数:
        subtitle: (序号, 开始时间, 结束时间, 字幕文本)
        audio_path: 音频文件路径
        threshold_db: 音量阈值
        min_duration_sec: 最小低音量持续时间
        chunk_length_ms: 分析块大小
    
    返回:
        list: [(开始时间, 结束时间), ...] 保留的高音量片段列表
    """
    index, start_time, end_time, text = subtitle
    
    # 分析音频片段
    times, volumes = analyze_audio_segment(audio_path, start_time, end_time, chunk_length_ms)
    
    if len(times) == 0:
        return [(start_time, end_time)]
    
    # 找到低音量片段
    low_segments = find_low_volume_segments(times, volumes, threshold_db, min_duration_sec)
    
    if len(low_segments) == 0:
        # 没有低音量片段，保留整个字幕
        return [(start_time, end_time)]
    
    # 计算保留的高音量片段
    high_segments = []
    current_start = start_time
    
    for low_start, low_end in low_segments:
        if current_start < low_start:
            high_segments.append((current_start, low_start))
        current_start = low_end
    
    # 最后一段
    if current_start < end_time:
        high_segments.append((current_start, end_time))
    
    return high_segments


def trim_srt_by_audio_volume(srt_path, audio_path, output_path=None, threshold_db=-50, min_duration_sec=0.3):
    """
    根据音频音量裁剪SRT字幕文件
    
    参数:
        srt_path: SRT文件路径
        audio_path: 对应的音频文件路径
        output_path: 输出文件路径，如果为None则自动生成
        threshold_db: 音量阈值（dBFS）
        min_duration_sec: 最小低音量持续时间（秒）
    """
    if output_path is None:
        base, ext = os.path.splitext(srt_path)
        output_path = f"{base}_trimmed{ext}"
    
    print(f"正在处理: {srt_path}")
    print(f"音频文件: {audio_path}")
    print(f"音量阈值: {threshold_db} dBFS")
    print(f"最小低音量持续时间: {min_duration_sec} 秒\n")
    
    # 解析SRT文件
    subtitles = parse_srt_file(srt_path)
    print(f"共找到 {len(subtitles)} 个字幕块\n")
    
    # 处理每个字幕块
    new_subtitles = []
    
    for idx, subtitle in enumerate(subtitles, 1):
        index, start_time, end_time, text = subtitle
        print(f"处理字幕 {idx}/{len(subtitles)}: {format_srt_time(start_time)} --> {format_srt_time(end_time)}")
        
        # 拆分字幕
        high_segments = split_subtitle_by_low_volume(
            subtitle, audio_path, threshold_db, min_duration_sec
        )
        
        print(f"  原始时长: {end_time - start_time:.2f}秒")
        print(f"  拆分成 {len(high_segments)} 个片段")
        
        # 保留原始时间戳，只删除低音量片段，并过滤掉太短的片段（小于1秒）
        for seg_idx, (seg_start, seg_end) in enumerate(high_segments):
            duration = seg_end - seg_start
            if duration >= 1.0:  # 只保留时长>=1秒的片段
                print(f"    片段 {seg_idx + 1}: {format_srt_time(seg_start)} --> {format_srt_time(seg_end)} (时长: {duration:.2f}秒) ✓ 保留")
                new_subtitles.append((seg_start, seg_end))
            else:
                print(f"    片段 {seg_idx + 1}: {format_srt_time(seg_start)} --> {format_srt_time(seg_end)} (时长: {duration:.2f}秒) ✗ 太短，跳过")
        
        print()
    
    # 写入新的SRT文件
    with open(output_path, 'w', encoding='utf-8') as f:
        for idx, (start, end) in enumerate(new_subtitles, 1):
            f.write(f"{idx}\n")
            f.write(f"{format_srt_time(start)} --> {format_srt_time(end)}\n")
            f.write(f"哈哈哈哈哈\n")  # 添加字幕文本
            f.write(f"\n")
    
    print(f"处理完成！")
    print(f"原始字幕块数: {len(subtitles)}")
    print(f"新字幕块数: {len(new_subtitles)}")
    print(f"输出文件: {output_path}")
    
    return output_path


if __name__ == "__main__":
    # 示例用法
    srt_file = "../resources/dst/srt_files/res9.srt"
    audio_file = "../resources/src/audios/邻居也疯狂第4集.mp3"
    
    # 裁剪字幕，删除低音量片段
    # threshold_db: 音量阈值，默认-50dB，可以根据实际情况调整（-60到-40之间）
    # min_duration_sec: 最小持续时间，只删除持续超过此时间的低音量片段，默认0.3秒
    output_file = trim_srt_by_audio_volume(
        srt_file, 
        audio_file, 
        threshold_db=-45,  # 可调整
        min_duration_sec=0.3  # 可调整
    )

