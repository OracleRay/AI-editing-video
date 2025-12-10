#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR API服务器
部署在有显卡的Windows机器上，提供OCR识别服务
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
from paddleocr import PaddleOCR
import base64
import io
from PIL import Image
import json
import tempfile
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('ocr_api_server')

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局OCR实例
ocr = None


def init_ocr():
    """初始化PaddleOCR实例"""
    global ocr
    if ocr is None:
        logger.info("正在初始化PaddleOCR...")
        ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False
        )
        logger.info("PaddleOCR初始化完成")
    return ocr


def image_to_numpy(image_data):
    """
    将图片数据转换为numpy数组
    
    Args:
        image_data: 可以是文件对象、base64字符串或numpy数组
    
    Returns:
        numpy数组格式的图像
    """
    if isinstance(image_data, np.ndarray):
        return image_data
    
    # 如果是文件对象
    if hasattr(image_data, 'read'):
        image_bytes = image_data.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    
    # 如果是base64字符串
    if isinstance(image_data, str):
        if image_data.startswith('data:image'):
            # 移除data:image/png;base64,前缀
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    
    raise ValueError("不支持的图片格式")


def ocr_result_to_json(ocr_result):
    """
    将PaddleOCR结果转换为JSON格式（直接返回OCR保存的JSON内容）
    
    Args:
        ocr_result: PaddleOCR的识别结果对象
    
    Returns:
        JSON格式的OCR结果（字典）
    """
    # 使用临时文件保存JSON，然后读取
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # 保存到临时文件
        ocr_result.save_to_json(tmp_path)
        
        # 读取JSON数据并直接返回
        with open(tmp_path, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
    finally:
        # 删除临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    return result_data


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'message': 'OCR API服务运行正常'
    })


@app.route('/ocr', methods=['POST'])
def ocr_recognize():
    """
    OCR识别接口
    
    支持两种方式上传图片：
    1. multipart/form-data: 使用file字段上传图片文件
    2. JSON: 使用base64编码的图片数据
    
    Returns:
        JSON格式的OCR识别结果
    """
    try:
        # 初始化OCR
        ocr_instance = init_ocr()
        
        # 获取图片数据
        image = None
        
        # 方式1: 通过文件上传
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': '未选择文件'}), 400
            image = image_to_numpy(file)
        
        # 方式2: 通过base64编码
        elif request.is_json:
            data = request.get_json()
            if 'image' in data:
                image = image_to_numpy(data['image'])
            else:
                return jsonify({'error': 'JSON中缺少image字段'}), 400
        
        else:
            return jsonify({'error': '请使用文件上传或JSON格式的base64图片'}), 400
        
        if image is None:
            return jsonify({'error': '无法解析图片数据'}), 400
        
        # 进行OCR识别
        ocr_results = ocr_instance.predict(input=image)
        
        # 处理结果（PaddleOCR可能返回多个结果，取第一个）
        if len(ocr_results) > 0:
            # 直接返回OCR保存的JSON内容
            result_json = ocr_result_to_json(ocr_results[0])
            return jsonify({
                'success': True,
                'data': result_json
            })
        else:
            return jsonify({
                'success': True,
                'data': {}
            })
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        logger.error(f"OCR识别失败: {error_msg}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


if __name__ == '__main__':
    # 启动时初始化OCR
    init_ocr()
    
    logger.info("启动OCR API服务器...")
    logger.info("监听地址: 0.0.0.0:1275")
    
    # 运行Flask应用
    # host='0.0.0.0' 允许外部访问
    # 生产环境建议使用gunicorn或uwsgi
    app.run(host='0.0.0.0', port=1275, debug=False)

