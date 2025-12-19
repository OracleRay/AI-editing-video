"""
配置文件加载工具
提供统一的配置读取接口，支持从API获取加密的YAML配置文件
"""

import sys
import yaml
from pathlib import Path
from typing import Any, Dict
from configs.get_configs import get_config_content


def get_base_path() -> Path:
    """
    获取程序运行的基础路径（打包内部资源目录）
    
    - 如果是 PyInstaller 打包后的 exe（单文件模式），返回临时解压目录 sys._MEIPASS
    - 如果是 Nuitka 打包后的 exe，返回临时解压目录（通过 __file__ 获取）
    - 如果是开发环境，返回项目根目录
    
    Returns:
        基础路径 Path 对象
    """
    if getattr(sys, 'frozen', False):
        # 打包后的 exe 环境
        # PyInstaller: 使用 sys._MEIPASS
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        # Nuitka: 使用当前模块所在目录（指向临时解压目录）
        # 在 Nuitka 单文件模式下，__file__ 指向临时解压目录中的文件
        return Path(__file__).resolve().parent.parent
    else:
        # 开发环境：基于当前文件位置
        return Path(__file__).resolve().parent.parent


def get_exe_dir() -> Path:
    """
    获取 exe 所在目录（用于日志等外部文件）
    
    - 如果是打包环境，返回 exe 所在目录（用于创建 logs 等外部文件）
    - 如果是开发环境，返回项目根目录
    
    Returns:
        exe 所在目录 Path 对象
    """
    if getattr(sys, 'frozen', False):
        # 打包环境：获取 exe 所在目录
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
        try:
            cwd = Path.cwd().resolve()
            if cwd.exists():
                return cwd
        except:
            pass
        
        # 方法4: 最后的备用方案 - 使用用户目录
        return Path.home() / "Desktop"
    else:
        # 开发环境：基于当前文件位置
        return Path(__file__).resolve().parent.parent


def get_resources_path() -> Path:
    """
    获取 resources 目录路径
    resources 已打包进 exe，从内部资源目录读取
    
    Returns:
        resources 目录 Path 对象
    """
    return get_base_path() / "resources"


class ConfigLoader:
    """配置加载器"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """单例模式，确保只有一个配置实例"""
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置加载器"""
        if self._config is None:
            self._load_config()
    
    def _load_config(self):
        """从API加载加密的配置文件"""
        try:
            # 从 get_configs 模块获取解密后的配置内容
            config_content = get_config_content()
            # 解析YAML内容
            self._config = yaml.safe_load(config_content) or {}
            if not self._config:
                raise ValueError("从API获取的配置文件为空")
            print(f"✓ 配置已从API加载")
        except Exception as e:
            raise ValueError(f"从API获取配置失败: {e}")
    
    def reload(self):
        """重新加载配置文件"""
        self._config = None
        self._load_config()
        print("配置文件已重新加载")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的路径
        
        Args:
            key_path: 配置键路径，如 "video.video_file" 或 "tts.speed"
            default: 默认值，如果键不存在则返回此值
        
        Returns:
            配置值
        
        Examples:
            >>> config = get_config()
            >>> video_file = config.get("video.video_file")
            >>> tts_speed = config.get("tts.speed", 1.0)
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置的某个完整部分
        
        Args:
            section: 配置部分名称，如 "video", "tts", "audio"
        
        Returns:
            配置字典
        
        Examples:
            >>> config = get_config()
            >>> tts_config = config.get_section("tts")
            >>> print(tts_config["model"])
        """
        return self._config.get(section, {})
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            完整的配置字典
        """
        return self._config.copy()
    
    def get_project_root(self) -> Path:
        """
        获取项目根目录（支持打包环境）
        
        Returns:
            项目根目录路径
        """
        return get_base_path()
    
    def get_absolute_path(self, relative_path: str) -> str:
        """
        将相对路径转换为绝对路径
        - 如果是 ffmpeg 相关路径，使用 workspace/ffmpeg 目录
        - 如果是 resources 路径，使用内部资源目录（已打包进 exe）
        - 其他路径，使用项目根目录
        
        Args:
            relative_path: 相对路径
        
        Returns:
            绝对路径字符串
        
        Examples:
            >>> config = get_config()
            >>> abs_path = config.get_absolute_path("resources/dst/videos/final_clip.mp4")
        """
        import os
        if os.path.isabs(relative_path):
            return relative_path
        
        # 如果是 ffmpeg 相关路径，使用 workspace/ffmpeg 目录
        if "ffmpeg" in relative_path.lower() and relative_path.endswith(".exe"):
            workspace_path = self.get_workspace_path()
            # 提取文件名（如 ffmpeg.exe, ffprobe.exe）
            filename = Path(relative_path).name
            ffmpeg_path = workspace_path / "ffmpeg" / filename
            return str(ffmpeg_path)
        
        # 如果是 resources 路径，使用内部资源目录（已打包进 exe）
        if relative_path.startswith("resources/"):
            base_path = get_base_path()
            return str(base_path / relative_path)
        
        # 其他路径使用项目根目录
        project_root = self.get_project_root()
        return str(project_root / relative_path)

    def get_workspace_path(self, relative_path: str = "") -> Path:
        """
        获取工作空间根目录（自动使用桌面路径下的 workspace 目录）
        
        Args:
            relative_path: 相对路径，如果提供则返回相对于此路径的绝对路径
        
        Returns:
            工作空间根目录路径
        """
        # 自动使用桌面路径下的 workspace 目录
        workspace_root = Path.home() / "Desktop" / "workspace"
        
        # 如果目录不存在则创建
        if not workspace_root.exists():
            workspace_root.mkdir(parents=True)
        
        if relative_path:
            return workspace_root / relative_path
        return workspace_root


# 全局配置实例
_global_config_loader = None


def get_config() -> ConfigLoader:
    """
    获取全局配置加载器实例（推荐使用此函数）
    
    Returns:
        ConfigLoader实例
    
    Examples:
        >>> from utils.config_loader import get_config
        >>> config = get_config()
        >>> video_file = config.get("video.video_file")
        >>> tts_speed = config.get("tts.speed")
    """
    global _global_config_loader
    if _global_config_loader is None:
        _global_config_loader = ConfigLoader()
    return _global_config_loader


def reload_config():
    """
    重新加载配置文件
    当配置文件被修改后，可以调用此函数重新加载
    """
    config = get_config()
    config.reload()


# ==================== 便捷函数 ====================

def get_value(key_path: str, default: Any = None) -> Any:
    """
    快捷方式：直接获取配置值
    
    Examples:
        >>> from utils.config_loader import get_value
        >>> video_file = get_value("video.video_file")
    """
    return get_config().get(key_path, default)


def get_section(section: str) -> Dict[str, Any]:
    """
    快捷方式：直接获取配置部分
    
    Examples:
        >>> from utils.config_loader import get_section
        >>> tts_config = get_section("tts")
    """
    return get_config().get_section(section)


def get_absolute_path(relative_path: str) -> str:
    """
    快捷方式：获取绝对路径
    
    Examples:
        >>> from utils.config_loader import get_absolute_path
        >>> abs_path = get_absolute_path("resources/dst/videos/final_clip.mp4")
    """
    return get_config().get_absolute_path(relative_path)


def get_workspace_path(relative_path: str = "") -> Path:
    """
    快捷方式：获取工作空间根目录
    
    Args:
        relative_path: 相对路径，如果提供则返回相对于此路径的绝对路径
    
    Examples:
        >>> from utils.config_loader import get_workspace_path
        >>> workspace_root = get_workspace_path()
    """
    return get_config().get_workspace_path(relative_path)


if __name__ == "__main__":
    # 测试代码
    print("\n" + "="*60)
    print("配置加载器测试")
    print("="*60)
    
    config = get_config()
    
    print("\n1. 测试获取配置值:")
    print(f"   video.video_file: {config.get('video.video_file')}")
    print(f"   tts.speed: {config.get('tts.speed')}")
    print(f"   tts.model: {config.get('tts.model')}")
    
    print("\n2. 测试获取配置部分:")
    tts_config = config.get_section('tts')
    print(f"   TTS配置: {tts_config}")
    
    print("\n3. 测试获取绝对路径:")
    video_file = config.get('video.video_file')
    abs_path = config.get_absolute_path(video_file)
    print(f"   相对路径: {video_file}")
    print(f"   绝对路径: {abs_path}")
    
    print("\n4. 测试便捷函数:")
    print(f"   get_value('audio.output_dir'): {get_value('audio.output_dir')}")
    print(f"   get_section('ffmpeg'): {get_section('ffmpeg')}")
    
    print("\n" + "="*60)
    print("所有测试通过")
    print("="*60)

