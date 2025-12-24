"""
配置获取模块 - 从API获取并解密配置文件
"""
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os


def derive_key_from_password(password: str) -> bytes:
    """从密码派生加密密钥（与服务端保持一致）"""
    password_bytes = password.encode('utf-8')
    salt = b'fixed_salt_for_key_derivation'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
    return key


def decrypt_content(encrypted_content: str, password: str) -> str:
    """使用密码解密内容"""
    try:
        key = derive_key_from_password(password)
        fernet = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_content.encode('utf-8'))
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    except Exception as e:
        raise ValueError(f"解密失败: {str(e)}")


def get_file(api_url: str, key: str):
    """
    从API获取加密文件并解密

    Args:
        api_url: API地址，例如 'http://localhost:5000/api/get'
        key: 密钥

    Returns:
        解密后的文件内容
    """
    try:
        # 方式1: GET请求
        response = requests.get(api_url, params={'key': key}, timeout=10)

        # 方式2: POST请求（可选）
        # response = requests.post(api_url, json={'key': key})

        if response.status_code == 404:
            raise ValueError("未找到对应的文件，请检查密钥是否正确")

        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            raise ValueError(data.get('error', '获取文件失败'))

        encrypted_content = data['encrypted_content']
        filename = data.get('filename', 'config.yaml')

        # 解密内容
        decrypted_content = decrypt_content(encrypted_content, key)

        print(f"✓ 成功获取文件: {filename}")
        print(f"✓ 解密成功")

        return decrypted_content

    except requests.exceptions.RequestException as e:
        raise ValueError(f"API请求失败: {str(e)}")


def get_config_content():
    """
    获取配置文件内容（从API获取并解密）
    
    优先从环境变量读取 API URL 和 key，如果未设置则使用默认值
    
    Returns:
        解密后的配置文件内容（字符串）
    
    Raises:
        ValueError: 如果API请求失败或解密失败
    """
    # 从环境变量获取，如果没有则使用默认值（示例值，实际使用时需要配置）
    api_url = 'http://172.17.3.115:3903/api/get'
    # api_key = 'eRJv4EHncPpUjdXdJMs8'
    api_key = 'EWnkpBhRfDCPxCvapNWX'

    return get_file(api_url, api_key)


if __name__ == '__main__':
    # 示例使用
    API_URL = 'http://172.17.3.115:3903/api/get'
    KEY = 'EWnkpBhRfDCPxCvapNWX'

    try:
        content = get_file(API_URL, KEY)
        print("\n" + "=" * 50)
        print("解密后的文件内容:")
        print("=" * 50)
        print(content)
    except Exception as e:
        print(f"错误: {e}")

