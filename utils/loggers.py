"""
日志系统模块
提供统一的日志配置和管理功能
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def _get_base_path() -> Path:
    """获取程序基础路径（支持打包环境）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record):
        """格式化日志记录，添加颜色"""
        # 保存原始levelname
        levelname = record.levelname
        
        # 为levelname添加颜色
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname:8}{self.COLORS['RESET']}"
        
        # 调用父类的format方法
        result = super().format(record)
        
        # 恢复原始levelname
        record.levelname = levelname
        
        return result


def setup_logger(
    name: Optional[str] = None,
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True,
    silent_init: bool = False
) -> logging.Logger:
    """
    设置并返回一个配置好的日志记录器
    
    Args:
        name: 日志记录器名称，默认为None（根日志记录器）
        log_dir: 日志文件存储目录，默认为None（自动使用项目根目录下的logs）
        level: 日志级别，默认为INFO
        console_output: 是否输出到控制台，默认为True
        file_output: 是否输出到文件，默认为True
        silent_init: 是否静默初始化（不打印初始化信息），默认为False
    
    Returns:
        配置好的日志记录器对象
    """
    # 获取或创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 确定日志目录：如果未指定，使用项目根目录下的logs
    if log_dir is None:
        # 获取项目根目录（支持打包环境）
        project_root = _get_base_path()
        log_path = project_root / "logs"
    else:
        # 如果指定了log_dir，检查是否是绝对路径
        if Path(log_dir).is_absolute():
            log_path = Path(log_dir)
        else:
            # 相对路径也基于项目根目录
            project_root = _get_base_path()
            log_path = project_root / log_dir
    
    # 创建日志目录
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 生成日志文件名（按日期时间命名）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"{timestamp}.log"
    
    # 定义日志格式
    # 文件日志格式：详细信息
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台日志格式：简洁且带颜色
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 添加文件处理器
    if file_output:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # 添加控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # 记录日志系统初始化信息（如果不是静默模式）
    if not silent_init:
        logger.info(f"日志系统初始化完成 | 日志文件: {log_file}")
    
    return logger


def get_logger(name: Optional[str] = None, silent: bool = True) -> logging.Logger:
    """
    获取日志记录器（简化版）
    如果日志系统未初始化，则自动初始化
    
    Args:
        name: 日志记录器名称，默认为None（根日志记录器）
        silent: 是否静默初始化，默认为True（不打印初始化信息）
    
    Returns:
        日志记录器对象
    """
    logger = logging.getLogger(name)
    
    # 如果没有处理器，说明未初始化，进行初始化
    if not logger.handlers:
        return setup_logger(name, silent_init=silent)
    
    return logger


# 全局标志，防止重复初始化
_app_logger_initialized = False
app_logger = None

def get_app_logger() -> logging.Logger:
    """获取应用级日志记录器（单例模式）"""
    global _app_logger_initialized, app_logger
    
    if not _app_logger_initialized:
        app_logger = setup_logger(name='common_video', level=logging.INFO, silent_init=False)
        _app_logger_initialized = True
    
    return app_logger


if __name__ == "__main__":
    """测试日志系统"""
    # 测试默认日志记录器
    test_logger = get_logger('test')
    
    test_logger.debug("这是一条DEBUG级别的日志")
    test_logger.info("这是一条INFO级别的日志")
    test_logger.warning("这是一条WARNING级别的日志")
    test_logger.error("这是一条ERROR级别的日志")
    test_logger.critical("这是一条CRITICAL级别的日志")
    
    # 测试不同模块的日志
    module1_logger = get_logger('module1')
    module1_logger.info("模块1的日志信息")
    
    module2_logger = get_logger('module2')
    module2_logger.info("模块2的日志信息")
    
    print("\n日志测试完成！请查看 logs 目录下的日志文件。")

