"""
配置文件加载工具
提供统一的配置读取接口，支持YAML配置文件
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


def get_base_path() -> Path:
    """
    获取程序运行的基础路径（项目根目录）
    
    - 如果是 PyInstaller 打包后的 exe，返回 exe 所在目录
    - 如果是开发环境，返回项目根目录
    
    Returns:
        基础路径 Path 对象
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的 exe 环境
        # sys.executable 是 exe 文件的完整路径
        return Path(sys.executable).parent
    else:
        # 开发环境：基于当前文件位置
        return Path(__file__).resolve().parent.parent


class ConfigLoader:
    """配置加载器"""
    
    _instance = None
    _config = None
    _config_path = None
    
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
        """加载配置文件"""
        # 获取项目根目录（支持打包环境）
        project_root = get_base_path()
        
        # 配置文件路径
        self._config_path = project_root / "configs" / "config.yaml"
        
        if not self._config_path.exists():
            raise FileNotFoundError(f"配置文件不存在：{self._config_path}")
        
        # 读取YAML配置
        with open(self._config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f) or {}
        
        print(f"配置文件已加载: {self._config_path}")
    
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
        将相对路径转换为绝对路径（相对于项目根目录）
        
        Args:
            relative_path: 相对路径
        
        Returns:
            绝对路径字符串
        
        Examples:
            >>> config = get_config()
            >>> abs_path = config.get_absolute_path("resources/dst/videos/final_clip.mp4")
        """
        if os.path.isabs(relative_path):
            return relative_path
        
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

