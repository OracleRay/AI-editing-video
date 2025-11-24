"""
文本转 SRT 字幕文件工具
将包含转义符的 SRT 字符串保存为 SRT 文件
"""

import os
from pathlib import Path
from datetime import datetime
from utils.loggers import get_logger
from utils.config_loader import get_config

logger = get_logger('text_to_srt', silent=True)
config = get_config()


def text_to_srt(srt_string: str, 
                output_dir: str = "resources/dst/srt_files") -> str:
    """
    将包含转义符的 SRT 字符串保存为 SRT 文件
    
    Args:
        srt_string: 包含 \n 转义符的 SRT 格式字符串
        output_dir: 输出目录，默认为 "resources/dst/srt_files"
    
    Returns:
        生成的 SRT 文件路径
    
    Examples:
        >>> from utils.text_to_srt import text_to_srt
        >>> srt_str = "1\\n00:00:00,000 --> 00:00:01,840\\n这是第一句\\n\\n2\\n00:00:01,840 --> 00:00:04,560\\n这是第二句"
        >>> file_path = text_to_srt(srt_str)
        >>> print(f"字幕文件已保存: {file_path}")
    """
    # 如果返回的是 Python 列表格式的字符串 ['...']，则提取内容
    if srt_string.startswith('[') and srt_string.endswith(']'):
        # 去掉首尾的方括号和引号
        srt_string = srt_string[1:-1]  # 去掉 [ 和 ]
        if srt_string.startswith("'") and srt_string.endswith("'"):
            srt_string = srt_string[1:-1]  # 去掉 ' 和 '
        elif srt_string.startswith('"') and srt_string.endswith('"'):
            srt_string = srt_string[1:-1]  # 去掉 " 和 "
    
    # 处理转义符，将 \n 转换为真正的换行符
    srt_content = srt_string.replace('\\n', '\n')
    
    # 使用 config_loader 转换为绝对路径（确保基于项目根目录）
    output_path = Path(config.get_absolute_path(output_dir))
    
    # 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名（使用当前时间，精确到秒）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.txt"
    file_path = output_path / filename
    
    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    
    return str(file_path)

if __name__ == "__main__":
    # 测试代码
    logger.info("=" * 60)
    logger.info("文本转 SRT 字幕文件测试")
    logger.info("=" * 60)
    
    # 测试字符串（包含 \n 转义符）
    test_srt = "1\\n00:00:00,000 --> 00:00:01,840\\n这男人被逼相亲，态度还挺无所谓\\n\\n2\\n00:00:01,840 --> 00:00:04,560\\n父亲的安排让他很为难，但还是来了\\n\\n3\\n00:00:04,560 --> 00:00:07,120\\n女人一脸不可思议，这年头还有人被逼相亲？"
    
    try:
        # 测试默认方法（使用时间戳命名）
        logger.info("1. 测试使用时间戳命名:")
        file_path = text_to_srt(test_srt)
        logger.info(f"   文件路径: {file_path}")
        
    except Exception as e:
        logger.error(f"错误: {str(e)}")
