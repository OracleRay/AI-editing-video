"""
剪映项目复制工具
负责将生成的 JSON 项目复制到用户指定目录
"""

import shutil
from pathlib import Path

from utils.config_loader import get_config
from utils.loggers import get_logger

logger = get_logger('jianying_drafts', silent=True)
config = get_config()


def copy_project_to_directory(
    project_json_dir: str,
    destination_dir: str
) -> str:
    """
    将项目 JSON 目录复制到指定目录
    
    Args:
        project_json_dir: 项目 JSON 输出目录（相对或绝对路径）
        destination_dir: 用户选择的目标目录
    
    Returns:
        复制后的目标目录绝对路径
    """
    src_path = Path(config.get_absolute_path(project_json_dir)).resolve()
    if not src_path.exists():
        raise FileNotFoundError(f"项目 JSON 目录不存在: {src_path}")
    
    destination_path = Path(destination_dir).expanduser().resolve()
    destination_path.mkdir(parents=True, exist_ok=True)
    
    dest_path = destination_path / src_path.name
    if dest_path.exists():
        shutil.rmtree(dest_path)
    
    shutil.copytree(src_path, dest_path)
    logger.info(f"剪映项目已复制到: {dest_path}")
    return str(dest_path)

