import re
from datetime import timedelta
from utils.loggers import get_logger

logger = get_logger('fresh_timeline', silent=True)


def parse_srt_time(time_str):
    """
    解析SRT时间格式: HH:MM:SS,mmm
    返回 timedelta 对象
    """
    match = re.match(r'(\d+):(\d+):(\d+),(\d+)', time_str)
    if match:
        hours, minutes, seconds, milliseconds = map(int, match.groups())
        return timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)
    return None


def format_srt_time(td):
    """
    将 timedelta 对象格式化为SRT时间格式: HH:MM:SS,mmm
    """
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = td.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def fresh_timeline(input_srt_path, output_srt_path):
    """
    重新计算字幕时间戳，从00:00:00,000开始
    保持每个字幕片段的持续时间不变
    """
    with open(input_srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 分割字幕块
    subtitle_blocks = re.split(r'\n\n+', content.strip())
    
    new_subtitles = []
    current_time = timedelta(0)  # 从0开始
    subtitle_index = 1  # 序号从1开始
    
    for block in subtitle_blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        # 解析时间戳
        time_match = re.match(r'(.+?)\s*-->\s*(.+)', lines[1])
        if not time_match:
            continue
        
        start_str, end_str = time_match.groups()
        original_start = parse_srt_time(start_str.strip())
        original_end = parse_srt_time(end_str.strip())
        
        if original_start is None or original_end is None:
            continue
        
        # 计算该字幕的持续时间
        duration = original_end - original_start
        
        # 新的开始时间是当前累计时间
        new_start = current_time
        # 新的结束时间是开始时间加上持续时间
        new_end = new_start + duration
        
        # 格式化新的时间戳
        new_time_line = f"{format_srt_time(new_start)} --> {format_srt_time(new_end)}"
        
        # 提取字幕文本（第3行及之后）
        subtitle_text = '\n'.join(lines[2:])
        
        # 构建新的字幕块
        new_block = f"{subtitle_index}\n{new_time_line}\n{subtitle_text}"
        new_subtitles.append(new_block)
        
        # 更新当前时间为这个字幕的结束时间
        current_time = new_end
        # 递增序号
        subtitle_index += 1
    
    # 写入新的字幕文件
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(new_subtitles))
    
    logger.info(f"[完成] 字幕时间轴已刷新")
    logger.info(f"[输入] {input_srt_path}")
    logger.info(f"[输出] {output_srt_path}")
    logger.info(f"[统计] 共处理 {len(new_subtitles)} 条字幕")
    logger.info(f"[时长] 新视频总时长: {format_srt_time(current_time)}")


if __name__ == "__main__":
    # 示例用法
    input_file = "../test/test.txt"
    output_file = "C:/Users/leidc/Desktop/workspace/srt_files/clip/test_fresh.txt"
    
    fresh_timeline(input_file, output_file)

