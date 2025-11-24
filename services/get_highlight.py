import numpy as np
import subprocess

def get_high_volume_intervals(audio_path, interval_sec=6, chunk_length_ms=100):
    """
    分析音频文件，找到在指定时间区间内音量大于平均值的区间
    
    参数:
        audio_path: 音频文件路径
        interval_sec: 分析区间长度（秒），默认6秒
        chunk_length_ms: 分析的时间块长度（毫秒），默认100ms
    
    返回:
        list: [(开始时间(秒), 结束时间(秒), 平均音量(dBFS)), ...]
    """
    print(f"正在分析音频文件: {audio_path}\n")
    
    # 使用ffmpeg转换音频为原始PCM格式
    import os
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    ffmpeg_path = str(project_root / "resources" / "src" / "ffmpeg" / "ffmpeg.exe")
    
    cmd = [
        ffmpeg_path,
        "-i", audio_path,
        "-f", "s16le",   # 16位小端格式
        "-ac", "1",      # 单声道
        "-ar", "44100",  # 采样率44100Hz
        "-"
    ]
    
    # 执行ffmpeg并获取音频数据
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    samples = np.frombuffer(result.stdout, dtype=np.int16)
    
    # 计算分块参数
    sample_rate = 44100
    chunk_size = int(sample_rate * chunk_length_ms / 1000)
    num_chunks = len(samples) // chunk_size
    
    print(f"音频时长: {len(samples) / sample_rate:.2f} 秒")
    print(f"开始分析 {num_chunks} 个片段...\n")
    
    # 分析每个音频块，计算音量
    volumes = []
    for i in range(num_chunks):
        chunk = samples[i * chunk_size:(i + 1) * chunk_size]
        rms = np.sqrt(np.mean(chunk.astype(np.float64)**2))
        volume_db = 20 * np.log10(rms / 32768) if rms > 0 else -96  # 静音设为-96dB
        volumes.append(volume_db)
    
    volumes = np.array(volumes)
    
    # 计算平均音量
    avg_volume = np.mean(volumes)
    print(f"音频平均音量: {avg_volume:.2f} dBFS\n")
    
    # 计算每个区间包含的块数
    chunks_per_interval = int(interval_sec * 1000 / chunk_length_ms)
    
    # 寻找音量大于平均值的区间
    high_intervals = []
    
    for i in range(0, len(volumes), chunks_per_interval):
        # 获取当前区间的音量数据
        interval_volumes = volumes[i:i + chunks_per_interval]
        
        # 如果区间不完整，跳过
        if len(interval_volumes) < chunks_per_interval:
            break
        
        # 计算区间平均音量
        interval_avg = np.mean(interval_volumes)
        
        # 如果区间平均音量大于整体平均音量，记录此区间
        if interval_avg > avg_volume:
            start_time = i * chunk_length_ms / 1000
            end_time = (i + chunks_per_interval) * chunk_length_ms / 1000
            high_intervals.append((start_time, end_time, interval_avg))
    
    # 按音量从高到低排序
    high_intervals_sorted = sorted(high_intervals, key=lambda x: x[2], reverse=True)
    
    # 打印结果
    print("=" * 70)
    print(f"音量大于平均值的 {interval_sec} 秒区间（共 {len(high_intervals)} 个）")
    print("=" * 70)
    print(f"\n音量最高的前 5 个区间：\n")
    
    for idx, (start, end, vol) in enumerate(high_intervals_sorted[:10], 1):
        start_min = int(start // 60)
        start_sec = start % 60
        end_min = int(end // 60)
        end_sec = end % 60
        print(f"{idx}. [{start_min:02d}:{start_sec:05.2f} - {end_min:02d}:{end_sec:05.2f}]  "
              f"区间音量: {vol:.2f} dBFS (高出平均值 {vol - avg_volume:+.2f} dB)")
    
    print("\n" + "=" * 70)
    
    return high_intervals_sorted, avg_volume


if __name__ == "__main__":
    # 音频文件路径
    audio_file = "../resources/src/audios/邻居也疯狂第4集.mp3"
    
    # 分析音频，找到6秒区间内音量大于平均值的区间
    high_intervals, avg_volume = get_high_volume_intervals(audio_file, interval_sec=5, chunk_length_ms=100)

