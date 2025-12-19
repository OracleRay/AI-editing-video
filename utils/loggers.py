"""
日志系统模块
提供统一的日志配置和管理功能
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import threading


def _get_exe_dir() -> Path:
    """获取 exe 所在目录（日志等外部文件应写到这里）"""
    if getattr(sys, 'frozen', False):
        # 打包环境：获取 exe 所在目录
        import os
        
        # 方法1: 尝试从 sys.argv[0] 获取（Nuitka 单文件模式下更可靠）
        if sys.argv and sys.argv[0]:
            argv_path = Path(sys.argv[0])
            if argv_path.is_absolute():
                # 如果是绝对路径，检查是否在临时目录
                argv_str = str(argv_path)
                # 排除临时目录
                if not ('AppData\\Local\\Temp' in argv_str or 
                        '\\Temp\\' in argv_str or 
                        argv_str.startswith('C:\\Windows\\Temp') or
                        '\\OneDrive\\' in argv_str and '\\Temp\\' in argv_str):
                    if argv_path.exists() and argv_path.is_file():
                        return argv_path.parent.resolve()
            else:
                # 如果是相对路径，转换为绝对路径
                try:
                    abs_path = argv_path.resolve()
                    if abs_path.exists() and abs_path.is_file():
                        abs_str = str(abs_path)
                        # 排除临时目录
                        if not ('AppData\\Local\\Temp' in abs_str or 
                                '\\Temp\\' in abs_str or
                                abs_str.startswith('C:\\Windows\\Temp')):
                            return abs_path.parent
                except:
                    pass
        
        # 方法2: 尝试从 sys.executable 获取
        exe_path = sys.executable
        exe_path_str = str(exe_path)
        # 排除临时目录
        if not ('AppData\\Local\\Temp' in exe_path_str or 
                '\\Temp\\' in exe_path_str or
                exe_path_str.startswith('C:\\Windows\\Temp')):
            exe_dir = Path(exe_path).parent.resolve()
            if exe_dir.exists():
                return exe_dir
        
        # 方法3: 如果前两种方法都失败，尝试使用当前工作目录
        # （假设用户从exe所在目录运行）
        try:
            cwd = Path.cwd().resolve()
            if cwd.exists():
                return cwd
        except:
            pass
        
        # 方法4: 最后的备用方案 - 使用用户目录
        return Path.home() / "Desktop"
    else:
        # 开发环境：项目根目录
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


# 全局变量：统一的日志文件路径和文件处理器
_global_log_file: Optional[Path] = None
_global_file_handler: Optional[logging.FileHandler] = None
_global_log_timestamp: Optional[str] = None  # 程序启动时的时间戳，用于单次运行的所有日志
_global_log_lock = threading.Lock()
_global_log_initialized = False  # 标记日志系统是否已经初始化过


def _get_global_log_file(log_path: Path) -> Path:
    """
    获取全局统一的日志文件路径（单次运行中的所有日志使用同一个文件）
    
    Args:
        log_path: 日志目录路径
    
    Returns:
        统一的日志文件路径
    """
    global _global_log_file, _global_log_timestamp
    
    with _global_log_lock:
        if _global_log_file is None:
            # 在第一次初始化时记录时间戳，后续所有logger都使用这个时间戳
            if _global_log_timestamp is None:
                _global_log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 使用原来的命名规则：YYYYMMDD_HHMMSS.log
            _global_log_file = log_path / f"{_global_log_timestamp}.log"
        
        return _global_log_file


def _get_global_file_handler(log_file: Path, formatter: logging.Formatter) -> logging.FileHandler:
    """
    获取全局统一的文件处理器
    
    Args:
        log_file: 日志文件路径
        formatter: 日志格式化器
    
    Returns:
        文件处理器
    """
    global _global_file_handler
    
    with _global_log_lock:
        if _global_file_handler is None:
            # 创建文件处理器，使用追加模式
            _global_file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
            _global_file_handler.setLevel(logging.INFO)
            _global_file_handler.setFormatter(formatter)
        
        return _global_file_handler


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
    
    # 防止日志传播到父logger（避免重复输出）
    logger.propagate = False
    
    # 先添加控制台处理器（确保可以输出日志信息）
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # 确定日志目录：如果未指定，使用桌面 workspace 目录下的 logs
    log_path = None
    try:
        if log_dir is None:
            # 使用桌面 workspace 目录
            from utils.config_loader import get_workspace_path
            workspace_path = get_workspace_path()
            log_path = workspace_path / "logs"
        else:
            # 如果指定了log_dir，检查是否是绝对路径
            if Path(log_dir).is_absolute():
                log_path = Path(log_dir)
            else:
                # 相对路径也基于 workspace 目录
                from utils.config_loader import get_workspace_path
                workspace_path = get_workspace_path()
                log_path = workspace_path / log_dir
    except Exception as e:
        # 如果获取 workspace 目录失败，使用备用目录
        log_path = Path.home() / "Desktop" / "workspace" / "logs"
        # 此时 logger 已经有控制台处理器了，可以安全调用
        logger.warning(f"获取 workspace 目录失败，使用备用日志目录: {log_path}, 错误: {e}")
    
    # 确保 log_path 有值
    if log_path is None:
        log_path = Path.home() / "Desktop" / "workspace" / "logs"
        logger.warning(f"日志路径未设置，使用默认路径: {log_path}")
    
    # 创建日志目录（添加错误处理）
    log_file = None
    global _global_log_initialized
    try:
        # 确保路径是绝对路径
        log_path = log_path.resolve()
        # 只在第一次初始化时输出目录创建信息
        if not _global_log_initialized and not silent_init:
            logger.info(f"尝试创建日志目录: {log_path}")
        log_path.mkdir(parents=True, exist_ok=True)
        if not _global_log_initialized and not silent_init:
            logger.info(f"✓ 日志目录创建成功: {log_path}")
    except PermissionError as e:
        # 权限错误：尝试使用用户目录
        import os
        fallback_dir = Path.home() / "AppData" / "Local" / "AI剪辑工具" / "logs"
        try:
            logger.warning(f"无法在 {log_path} 创建日志文件夹（权限问题），尝试备用目录: {fallback_dir}")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            log_path = fallback_dir.resolve()
            logger.info(f"✓ 使用备用日志目录: {log_path}")
        except Exception as e2:
            # 如果还是失败，禁用文件输出
            logger.error(f"无法创建日志目录: {e}, {e2}，将只输出到控制台")
            file_output = False
            log_path = None
    except Exception as e:
        # 其他错误：尝试使用用户目录
        import os
        fallback_dir = Path.home() / "AppData" / "Local" / "AI剪辑工具" / "logs"
        try:
            logger.warning(f"无法在 {log_path} 创建日志文件夹，尝试备用目录: {fallback_dir}, 错误: {e}")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            log_path = fallback_dir.resolve()
            logger.info(f"✓ 使用备用日志目录: {log_path}")
        except Exception as e2:
            # 如果还是失败，禁用文件输出
            logger.error(f"无法创建日志目录: {e}, {e2}，将只输出到控制台")
            file_output = False
            log_path = None
    
    # 生成统一的日志文件名（按日期命名，所有日志写入同一个文件）
    log_file = None
    if log_path:
        log_file = _get_global_log_file(log_path)
    
    # 定义文件日志格式（详细信息）
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 添加文件处理器（使用全局统一的文件处理器）
    if file_output and log_file:
        try:
            # 使用全局统一的文件处理器，确保所有日志写入同一个文件
            file_handler = _get_global_file_handler(log_file, file_formatter)
            # 检查这个handler是否已经添加到当前logger（避免重复添加）
            if file_handler not in logger.handlers:
                logger.addHandler(file_handler)
        except Exception as e:
            # 如果创建文件处理器失败，禁用文件输出
            logger.warning(f"无法创建日志文件: {log_file}, 错误: {e}，将只输出到控制台")
            file_output = False
    
    # 记录日志系统初始化信息（只在第一次初始化且不是静默模式时输出）
    if not _global_log_initialized and not silent_init:
        logger.info(f"日志系统初始化完成")
        if log_path:
            logger.info(f"  📁 日志目录: {log_path}")
        if log_file:
            logger.info(f"  📄 日志文件: {log_file}")
        try:
            from utils.config_loader import get_workspace_path
            workspace_path = get_workspace_path()
            logger.info(f"  📂 workspace 目录: {workspace_path}")
        except:
            pass
        # 标记日志系统已初始化
        _global_log_initialized = True
    
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

