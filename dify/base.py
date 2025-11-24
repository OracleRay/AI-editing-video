"""
Dify API 基类
提供调用 Dify 工作流的统一接口
"""

import os
import yaml
import json
import requests
from pathlib import Path
from typing import Any, Dict, Optional


class DifyClient:
    """Dify API 客户端基类"""
    
    def __init__(self, workflow_name: str):
        """
        初始化 Dify 客户端
        
        Args:
            workflow_name: 工作流名称，如 'commentary' 或 'editing'
        """
        self.workflow_name = workflow_name
        self.config = self._load_dify_config()
        self.base_url = self.config.get('base_url')
        self.workflow_config = self.config.get('workflows', {}).get(workflow_name)
        
        if not self.workflow_config:
            raise ValueError(f"未找到工作流配置: {workflow_name}")
        
        self.api_key = self.workflow_config.get('api_key')
        self.description = self.workflow_config.get('description', '')
        
        if not self.api_key:
            raise ValueError(f"工作流 {workflow_name} 缺少 API Key")
    
    def _load_dify_config(self) -> Dict[str, Any]:
        """
        加载 Dify 配置文件
        
        Returns:
            配置字典
        """
        # 获取项目根目录
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        
        # Dify 配置文件路径
        config_path = project_root / "configs" / "dify.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Dify 配置文件不存在：{config_path}")
        
        # 读取 YAML 配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        return config
    
    def upload_file(self, content: str, filename: str = "input.txt", user: str = "user") -> Dict[str, Any]:
        """
        上传文本内容为文件到 Dify
        
        Args:
            content: 文本内容
            filename: 文件名
            user: 用户标识
        
        Returns:
            包含 id 的文件信息字典
        """
        # 构建 API 端点
        endpoint = f"{self.base_url}/files/upload"
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 准备文件数据
        files = {
            'file': (filename, content.encode('utf-8'), 'text/plain')
        }
        
        data = {
            'user': user
        }
        
        try:
            # 发送请求
            response = requests.post(
                endpoint,
                headers=headers,
                files=files,
                data=data,
                timeout=60
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            return result
            
        except requests.exceptions.RequestException as e:
            # 尝试获取详细的错误信息
            error_detail = ""
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_detail = f"\n响应内容: {e.response.text}"
            except:
                pass
            raise Exception(f"文件上传失败: {str(e)}{error_detail}")
    
    def run_workflow(self, inputs: Dict[str, Any], user: str = "abc-123") -> str:
        """
        运行 Dify 工作流
        
        Args:
            inputs: 输入参数字典
            user: 用户标识，默认为 "user"
        
        Returns:
            工作流生成的文本内容
        
        Raises:
            Exception: 当 API 调用失败时抛出异常
        """
        # 构建 API 端点
        endpoint = f"{self.base_url}/workflows/run"
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体
        payload = {
            "inputs": inputs,
            "response_mode": "streaming",
            "user": user
        }
        
        try:
            # 发送请求，使用 stream=True 以支持流式响应
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=300,  # 5分钟超时
                stream=True
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 处理流式响应
            text = self._process_streaming_response(response)
            
            return text
            
        except requests.exceptions.Timeout:
            raise Exception(f"Dify 工作流 '{self.workflow_name}' 请求超时")
        except requests.exceptions.RequestException as e:
            # 尝试获取详细的错误信息
            error_detail = ""
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_detail = f"\n响应内容: {e.response.text}"
            except:
                pass
            raise Exception(f"Dify 工作流 '{self.workflow_name}' 调用失败: {str(e)}{error_detail}")
        except Exception as e:
            raise Exception(f"处理 Dify 响应时出错: {str(e)}")
    
    def _process_streaming_response(self, response: requests.Response) -> str:
        """
        处理流式响应（SSE 格式）
        
        Args:
            response: requests 响应对象
        
        Returns:
            完整的生成文本
        """
        full_text = ""
        node_outputs = {}  # 存储所有节点的输出
        
        # 逐行读取流式响应
        for line in response.iter_lines():
            if not line:
                continue
            
            # 解码字节为字符串
            line_str = line.decode('utf-8')
            
            # SSE 格式: "data: {json}"
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # 去掉 "data: " 前缀
                
                # 跳过特殊标记
                if data_str == '[DONE]':
                    break
                
                try:
                    # 解析 JSON
                    data = json.loads(data_str)
                    
                    # 提取文本内容
                    event = data.get('event', '')
                    
                    if event == 'workflow_finished':
                        # 工作流完成，提取最终结果
                        outputs = data.get('data', {}).get('outputs', {})
                        
                        if 'text' in outputs:
                            full_text = outputs['text']
                        elif outputs:
                            # 获取第一个输出值
                            first_key = list(outputs.keys())[0]
                            full_text = str(outputs[first_key])
                        
                    elif event == 'text_chunk' or event == 'agent_message':
                        # 文本块
                        chunk = data.get('data', {}).get('text', '')
                        full_text += chunk
                        
                    elif event == 'workflow_started':
                        pass
                        
                    elif event == 'node_started':
                        pass
                        
                    elif event == 'node_finished':
                        node_title = data.get('data', {}).get('title', '')
                        node_data = data.get('data', {})
                        
                        # 保存节点输出
                        if 'outputs' in node_data:
                            node_outputs[node_title] = node_data['outputs']
                    
                    elif event == 'error':
                        error_msg = data.get('data', {}).get('message', '未知错误')
                        raise Exception(f"工作流执行错误: {error_msg}")
                    
                except json.JSONDecodeError as e:
                    continue
                except Exception as e:
                    continue
        
        # 如果 full_text 为空，尝试从节点输出中获取
        if not full_text and node_outputs:
            # 尝试从各个节点中找到非空的文本输出
            for node_name, outputs in node_outputs.items():
                if isinstance(outputs, dict):
                    # 尝试常见的字段名
                    for key in ['text', 'result', 'output', 'content', 'data']:
                        if key in outputs and outputs[key]:
                            full_text = str(outputs[key])
                            break
                    if full_text:
                        break
                elif isinstance(outputs, str) and outputs:
                    full_text = outputs
                    break
        
        if not full_text:
            raise Exception("未从流式响应中获取到任何文本内容")
        
        # 清理返回的文本：如果是 Python 列表格式 ['...']，提取内容
        full_text = self._clean_response_text(full_text)
        
        return full_text
    
    def _clean_response_text(self, text: str) -> str:
        """
        清理响应文本，处理特殊格式
        
        Args:
            text: 原始文本
        
        Returns:
            清理后的文本
        """
        # 去除首尾空白
        text = text.strip()
        
        # 如果文本是 Python 列表格式 ['...']，提取内容
        if text.startswith('[') and text.endswith(']'):
            # 去掉首尾的方括号
            text = text[1:-1].strip()
            # 去掉引号（单引号或双引号）
            if (text.startswith("'") and text.endswith("'")) or \
               (text.startswith('"') and text.endswith('"')):
                text = text[1:-1]
        
        return text
    
    def _extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        从响应中提取文本内容
        
        Args:
            response: API 响应字典
        
        Returns:
            提取的文本内容
        """
        # 尝试从 data.outputs.text 提取
        if 'data' in response and 'outputs' in response['data']:
            outputs = response['data']['outputs']
            if 'text' in outputs:
                return outputs['text']
            # 如果没有 text 字段，尝试其他常见字段
            if 'result' in outputs:
                return outputs['result']
            if 'content' in outputs:
                return outputs['content']
        
        # 尝试直接从 outputs 提取
        if 'outputs' in response:
            outputs = response['outputs']
            if 'text' in outputs:
                return outputs['text']
            if 'result' in outputs:
                return outputs['result']
            if 'content' in outputs:
                return outputs['content']
        
        # 如果都没找到，返回整个响应的字符串形式
        return str(response)
    
    def get_workflow_info(self) -> Dict[str, str]:
        """
        获取工作流信息
        
        Returns:
            包含工作流名称和描述的字典
        """
        return {
            "name": self.workflow_name,
            "description": self.description,
            "base_url": self.base_url
        }


# ==================== 便捷函数 ====================

def create_dify_client(workflow_name: str) -> DifyClient:
    """
    创建 Dify 客户端实例（便捷函数）
    
    Args:
        workflow_name: 工作流名称，'commentary' 或 'editing'
    
    Returns:
        DifyClient 实例
    
    Examples:
        >>> from dify.base import create_dify_client
        >>> client = create_dify_client("commentary")
        >>> result = client.run_workflow({"video_url": "http://example.com/video.mp4"})
        >>> print(result)
    """
    return DifyClient(workflow_name)


if __name__ == "__main__":
    # 测试代码
    print("\n" + "="*60)
    print("Dify 客户端测试")
    print("="*60)
    
    try:
        # 测试解说工作流客户端
        print("\n1. 创建 commentary 工作流客户端:")
        commentary_client = create_dify_client("commentary")
        info = commentary_client.get_workflow_info()
        print(f"   工作流名称: {info['name']}")
        print(f"   工作流描述: {info['description']}")
        print(f"   API 地址: {info['base_url']}")
        
        # 测试剪辑工作流客户端
        print("\n2. 创建 editing 工作流客户端:")
        editing_client = create_dify_client("editing")
        info = editing_client.get_workflow_info()
        print(f"   工作流名称: {info['name']}")
        print(f"   工作流描述: {info['description']}")
        print(f"   API 地址: {info['base_url']}")
        
        print("\n" + "="*60)
        print("客户端初始化测试通过")
        print("="*60)
        
    except Exception as e:
        print(f"\n错误: {str(e)}")

