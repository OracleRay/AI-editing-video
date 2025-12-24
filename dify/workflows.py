"""
Dify 工作流调用模块
提供便捷的工作流调用函数
"""

from typing import Dict, Any
from .base import create_dify_client


def run_commentary_workflow(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    运行 AI 解说工作流（commentary）
    
    如果 inputs 中包含 'short_copy' 或 'long_commentary' 且为字符串，会自动上传为文件

    Examples:
        >>> from dify.workflows import run_commentary_workflow
        >>> inputs = {
        ...     "plot": "剧情简介...",
        ...     "short_copy": "短文案内容...",
        ... }
        >>> result = run_commentary_workflow(inputs)
        >>> print(result["text"])
    """
    # 创建 commentary 工作流客户端
    client = create_dify_client("commentary")
    
    # 如果 short_copy 是字符串，先上传为文件
    if "short_copy" in inputs and isinstance(inputs["short_copy"], str):
        text_content = inputs["short_copy"]
        
        # 统一换行符为 \r\n（Windows 格式）
        text_content = text_content.replace('\r\n', '\n')
        
        # 上传文件
        file_info = client.upload_file(text_content, filename="short_copy.txt")
        
        # 替换为文件对象（单个对象，不是列表）
        inputs["short_copy"] = {
            "type": "document",
            "transfer_method": "local_file", 
            "upload_file_id": file_info["id"]
        }
    
    # 调用工作流并返回结果字典
    result = client.run_workflow(inputs)
    
    return result


def run_editing_workflow(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    运行 AI 剪辑工作流（editing）
    
    如果 inputs 中包含 'long_lines' 且为字符串，会自动上传为文件

    Examples:
        >>> from dify.workflows import run_editing_workflow
        >>> inputs = {
        ...     "long_lines": "这是一段长文本...",
        ...     "plot": "可选字段"
        ... }
        >>> result = run_editing_workflow(inputs)
        >>> print(result["text"])
    """
    # 创建 editing 工作流客户端
    client = create_dify_client("editing")
    
    # 如果 long_lines 是字符串，先上传为文件
    if "long_lines" in inputs and isinstance(inputs["long_lines"], str):
        text_content = inputs["long_lines"]
        
        # 统一换行符为 \r\n（Windows 格式）
        # 先将所有 \r\n 转换为 \n，然后统一转换为 \r\n
        text_content = text_content.replace('\r\n', '\n')
        
        # 上传文件
        file_info = client.upload_file(text_content, filename="input_lines.txt")
        
        # 替换为文件对象列表
        inputs["long_lines"] = [{
            "type": "document",
            "transfer_method": "local_file", 
            "upload_file_id": file_info["id"]
        }]
    
    # 调用工作流并返回结果字典
    result = client.run_workflow(inputs)
    
    return result


def run_typo_workflow(merged_srt_file: str, commentary_txt_file: str = None) -> Dict[str, Any]:
    """
    运行错别字修正工作流（typo_correct）
    
    将合并后的SRT文件和解说工作流输出的txt文件上传到Dify工作流进行错别字修正处理
    
    Args:
        merged_srt_file: 合并后的SRT文件路径（merge.txt）
        commentary_txt_file: 解说工作流输出的txt文件路径（可选）
    
    Returns:
        工作流返回的结果字典
    
    Examples:
        >>> from dify.workflows import run_typo_workflow
        >>> result = run_typo_workflow("merge.txt", "commentary.txt")
        >>> print(result["text"])
    """
    # 创建 typo_correct 工作流客户端
    client = create_dify_client("typo_correct")
    
    # 读取合并后的SRT文件内容
    with open(merged_srt_file, "r", encoding="utf-8") as f:
        srt_content = f.read()
    with open(commentary_txt_file, "r", encoding="utf-8") as f:
        commentary_content = f.read()
    
    # 统一换行符为 \r\n（Windows 格式）
    srt_content = srt_content.replace('\r\n', '\n')
    commentary_content = commentary_content.replace('\r\n', '\n')

    # 上传SRT文件到Dify
    file_info = client.upload_file(srt_content, filename="merged_srt.txt")
    commentary_file_info = client.upload_file(commentary_content, filename="commentary.txt")
    
    # 构建输入参数字典
    inputs = {
        "asr_srt_file": {
            "type": "document",
            "transfer_method": "local_file", 
            "upload_file_id": file_info["id"]
        },
        "source_srt_file": {
            "type": "document",
            "transfer_method": "local_file",
            "upload_file_id": commentary_file_info["id"]
        }
    }
    
    # 调用工作流并返回结果字典
    result = client.run_workflow(inputs)
    
    return result