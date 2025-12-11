#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕位置识别脚本
从视频中随机抽取帧，使用PaddleOCR识别字幕位置
"""

import cv2
import random
import os
from pathlib import Path
import json
from datetime import datetime
import requests
import base64
from io import BytesIO
import tempfile
import shutil
from utils.loggers import get_logger

# 初始化日志记录器
logger = get_logger('subtitle_detector')


def extract_frames(video_path, num_frames=30):
    """
    从视频中随机抽取指定数量的帧
    
    Args:
        video_path: 视频文件路径
        num_frames: 要抽取的帧数，默认20
    
    Returns:
        frames: 抽取的帧列表，每个元素是(frame_number, frame_image)
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {video_path}")
    
    # 获取视频总帧数
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames < num_frames:
        logger.warning(f"视频总帧数({total_frames})少于请求的帧数({num_frames})，将抽取所有帧")
        num_frames = total_frames
    
    # 随机选择帧号
    frame_numbers = sorted(random.sample(range(total_frames), num_frames))
    
    frames = []
    for frame_num in frame_numbers:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret:
            frames.append((frame_num, frame))
        else:
            logger.warning(f"无法读取第 {frame_num} 帧")
    
    cap.release()
    return frames


def detect_subtitles(image, api_url):
    """
    使用API识别图像中的字幕位置
    
    Args:
        image: 输入图像（numpy array）
        api_url: API服务器地址
    
    Returns:
        results: OCR识别结果（模拟结果对象）
    """
    return detect_subtitles_api(image, api_url)


def detect_subtitles_api(image, api_url):
    """
    通过API调用OCR识别
    
    Args:
        image: 输入图像（numpy array）
        api_url: API服务器地址
    
    Returns:
        results: 模拟的OCR结果对象列表
    """
    # 将图像编码为JPEG格式
    _, buffer = cv2.imencode('.jpg', image)
    image_bytes = buffer.tobytes()
    
    # 准备文件上传
    files = {'file': ('image.jpg', image_bytes, 'image/jpeg')}
    
    try:
        # 发送POST请求
        response = requests.post(f"{api_url}/ocr", files=files, timeout=60)
        response.raise_for_status()
        
        result_data = response.json()
        
        if not result_data.get('success', False):
            raise Exception(f"API返回错误: {result_data.get('error', '未知错误')}")
        
        # 获取OCR数据（直接是OCR保存的JSON内容）
        ocr_data = result_data.get('data', {})
        
        # 创建模拟结果对象
        class MockOCRResult:
            def __init__(self, data):
                self.data = data
                # 从JSON数据中提取字段
                self.rec_boxes = data.get('rec_boxes', [])
                self.rec_texts = data.get('rec_texts', [])
                self.rec_scores = data.get('rec_scores', [])
            
            def print(self):
                """打印识别结果"""
                for i, (box, text, score) in enumerate(zip(self.rec_boxes, self.rec_texts, self.rec_scores)):
                    logger.debug(f"  文本 {i+1}: {text} (置信度: {score:.2f}, 位置: {box})")
            
            def save_to_img(self, path):
                """保存可视化结果（API模式暂不支持，跳过）"""
                pass
            
            def save_to_json(self, path):
                """保存JSON结果（直接保存API返回的JSON数据）"""
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            def to_dict(self):
                """转换为字典"""
                return self.data
        
        return [MockOCRResult(ocr_data)]
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"API请求失败: {str(e)}")


def extract_subtitle_info(json_path):
    """
    从OCR结果JSON中提取字幕的垂直位置和置信度
    如果识别出多个文本，直接丢弃该帧（返回空列表）
    
    Args:
        json_path: OCR结果JSON文件路径
    
    Returns:
        subtitle_info: 字幕信息列表，如果识别出多个文本则返回空列表
    """
    subtitle_info = []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)
        
        # 提取识别框、文本和置信度
        rec_boxes = ocr_data.get('rec_boxes', [])
        rec_texts = ocr_data.get('rec_texts', [])
        rec_scores = ocr_data.get('rec_scores', [])
        
        # 确保三个数组长度一致
        min_len = min(len(rec_boxes), len(rec_texts), len(rec_scores))
        
        if min_len == 0:
            return subtitle_info
        
        # 如果识别出多个文本，直接丢弃该帧
        if min_len > 1:
            # 过滤掉置信度过低或文本为空的，看看有效文本数量
            valid_count = 0
            for i in range(min_len):
                text = rec_texts[i]
                score = rec_scores[i]
                if float(score) >= 0.5 and text.strip():
                    valid_count += 1
            
            # 如果有多个有效文本，丢弃该帧
            if valid_count > 1:
                return subtitle_info
        
        # 如果只有一个文本（或过滤后只剩一个），处理它
        # 找到第一个有效的文本
        for i in range(min_len):
            box = rec_boxes[i]
            text = rec_texts[i]
            score = rec_scores[i]
            
            # 过滤掉置信度过低或文本为空的
            if float(score) < 0.5 or not text.strip():
                continue
            
            y_top = box[1]
            y_bottom = box[3]
            y_center = (y_top + y_bottom) / 2
            
            subtitle_info.append({
                "text": text,
                "confidence": float(score),
                "vertical_position": {
                    "top": int(y_top),
                    "bottom": int(y_bottom),
                    "center": float(y_center)
                },
                "box": {
                    "x1": int(box[0]),
                    "y1": int(box[1]),
                    "x2": int(box[2]),
                    "y2": int(box[3])
                }
            })
            break  # 只取第一个有效的
    
    except Exception as e:
        logger.warning(f"无法读取OCR结果JSON文件 {json_path}: {e}")
    
    return subtitle_info


def extract_all_text_positions(all_results):
    """
    从所有帧的OCR结果中提取所有文本的位置信息（用于兜底方案）
    
    Args:
        all_results: 所有帧的OCR结果列表
    
    Returns:
        all_texts: 所有文本的位置信息列表，每个元素包含 (frame_num, text, box, score)
    """
    all_texts = []
    
    for frame_result in all_results:
        frame_num = frame_result.get('frame_number', 0)
        
        for ocr_result in frame_result.get('ocr_results', []):
            json_path = ocr_result.get('json_path')
            if not json_path:
                continue
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    ocr_data = json.load(f)
                
                rec_boxes = ocr_data.get('rec_boxes', [])
                rec_texts = ocr_data.get('rec_texts', [])
                rec_scores = ocr_data.get('rec_scores', [])
                
                min_len = min(len(rec_boxes), len(rec_texts), len(rec_scores))
                
                for i in range(min_len):
                    box = rec_boxes[i]
                    text = rec_texts[i]
                    score = rec_scores[i]
                    
                    # 过滤掉置信度过低或文本为空的
                    if float(score) < 0.3 or not text.strip():
                        continue
                    
                    # 过滤掉明显的调试信息（如"Frame:", "Subtitle:"等）
                    text_lower = text.strip().lower()
                    if text_lower.startswith('frame:') or text_lower.startswith('subtitle:'):
                        continue
                    
                    all_texts.append({
                        'frame_num': frame_num,
                        'text': text,
                        'box': box,
                        'score': float(score),
                        'center_y': (box[1] + box[3]) / 2,
                        'height': box[3] - box[1]
                    })
            except Exception as e:
                continue
    
    return all_texts


def find_subtitle_cluster(all_texts, y_threshold=30, min_occurrences=3):
    """
    从所有文本中找出位置最相似的一组文本（字幕）
    使用y坐标的相似度来聚类
    
    Args:
        all_texts: 所有文本的位置信息列表
        y_threshold: y坐标差异阈值（像素），默认30
        min_occurrences: 字幕应该出现的最小次数，默认3
    
    Returns:
        subtitle_texts: 识别为字幕的文本列表
    """
    if not all_texts:
        return []
    
    # 按y坐标分组，找出出现次数最多的位置范围
    # 使用字典记录每个y坐标范围出现的次数和文本
    y_groups = {}
    
    for text_info in all_texts:
        center_y = text_info['center_y']
        # 将y坐标量化到阈值范围内
        y_key = round(center_y / y_threshold) * y_threshold
        
        if y_key not in y_groups:
            y_groups[y_key] = []
        y_groups[y_key].append(text_info)
    
    # 找出出现次数最多的组（字幕应该出现在大多数帧中）
    best_group = None
    best_count = 0
    
    for y_key, texts in y_groups.items():
        # 统计不同帧的数量（字幕应该在多帧中出现）
        frame_nums = set(t['frame_num'] for t in texts)
        frame_count = len(frame_nums)
        
        if frame_count >= min_occurrences and frame_count > best_count:
            best_count = frame_count
            best_group = texts
    
    if best_group is None:
        # 如果没找到满足最小出现次数的，找出现次数最多的
        for y_key, texts in y_groups.items():
            frame_nums = set(t['frame_num'] for t in texts)
            frame_count = len(frame_nums)
            if frame_count > best_count:
                best_count = frame_count
                best_group = texts
    
    return best_group if best_group else []


def calculate_subtitle_statistics_fallback(all_results):
    """
    兜底方案：从所有帧的OCR结果中找出位置最相似的字幕
    
    Args:
        all_results: 所有帧的OCR结果列表
    
    Returns:
        statistics: 包含中心点坐标和高度等统计信息的字典，如果找不到则返回None
    """
    logger.info("使用兜底方案：从所有帧结果中识别字幕位置...")
    
    # 提取所有文本位置
    all_texts = extract_all_text_positions(all_results)
    
    if not all_texts:
        logger.warning("未能提取到任何文本位置信息")
        return None
    
    logger.info(f"共提取到 {len(all_texts)} 个文本位置")
    
    # 找出字幕聚类
    subtitle_texts = find_subtitle_cluster(all_texts, y_threshold=30, min_occurrences=3)
    
    if not subtitle_texts:
        logger.warning("未能找到位置相似的字幕文本")
        return None
    
    logger.info(f"识别出 {len(subtitle_texts)} 个字幕文本（来自 {len(set(t['frame_num'] for t in subtitle_texts))} 帧）")
    
    # 计算统计信息
    center_x_list = []
    center_y_list = []
    height_list = []
    
    for text_info in subtitle_texts:
        box = text_info['box']
        x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
        
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        height = y2 - y1
        
        if height > 0:
            center_x_list.append(center_x)
            center_y_list.append(center_y)
            height_list.append(height)
    
    if not center_x_list:
        return None
    
    # 计算平均值
    import statistics
    
    avg_center_x = sum(center_x_list) / len(center_x_list)
    avg_center_y = sum(center_y_list) / len(center_y_list)
    avg_height = sum(height_list) / len(height_list)
    
    # 计算标准差
    std_center_x = statistics.stdev(center_x_list) if len(center_x_list) > 1 else 0
    std_center_y = statistics.stdev(center_y_list) if len(center_y_list) > 1 else 0
    std_height = statistics.stdev(height_list) if len(height_list) > 1 else 0
    
    # 计算范围
    min_x = min(center_x_list)
    max_x = max(center_x_list)
    min_y = min(center_y_list)
    max_y = max(center_y_list)
    min_height = min(height_list)
    max_height = max(height_list)
    
    logger.info(f"字幕位置: 中心点({int(round(avg_center_x))}, {int(round(avg_center_y))}), 高度: {int(round(avg_height))}")
    
    return {
        "center_x": int(round(avg_center_x)),
        "center_y": int(round(avg_center_y)),
        "height": int(round(avg_height)),
        "valid_count": len(center_x_list),
        "original_count": len(center_x_list),
        "filtered_out": 0,
        "std_center_x": float(std_center_x),
        "std_center_y": float(std_center_y),
        "std_height": float(std_height),
        "range": {
            "center_x": {"min": int(round(min_x)), "max": int(round(max_x))},
            "center_y": {"min": int(round(min_y)), "max": int(round(max_y))},
            "height": {"min": int(round(min_height)), "max": int(round(max_height))}
        },
        "fallback_method": True  # 标记这是兜底方案的结果
    }


def calculate_subtitle_statistics(all_results):
    """
    根据多个帧的OCR结果，合并计算字幕中心点坐标和字幕高度
    只统计每帧的第一个有效字幕（因为已经过滤过，每帧应该只有一个字幕）
    
    Args:
        all_results: 所有帧的OCR结果列表
    
    Returns:
        statistics: 包含中心点坐标和高度等统计信息的字典
    """
    # 收集所有有效的字幕位置信息
    center_x_list = []
    center_y_list = []
    height_list = []
    original_count = 0
    
    for frame_result in all_results:
        # 每帧只取第一个有效的字幕
        frame_subtitle_found = False
        for ocr_result in frame_result.get('ocr_results', []):
            subtitles = ocr_result.get('subtitles', [])
            if subtitles and not frame_subtitle_found:
                # 只取第一个字幕（应该只有一个，因为已经过滤过）
                subtitle = subtitles[0]
                box = subtitle.get('box', {})
                confidence = subtitle.get('confidence', 0)
                
                if box and confidence >= 0.5:  # 置信度过滤
                    x1 = box.get('x1', 0)
                    y1 = box.get('y1', 0)
                    x2 = box.get('x2', 0)
                    y2 = box.get('y2', 0)
                    
                    # 计算中心点
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    
                    # 计算高度
                    height = y2 - y1
                    
                    # 只收集有效的字幕（高度大于0，且置信度足够）
                    if height > 0:
                        center_x_list.append(center_x)
                        center_y_list.append(center_y)
                        height_list.append(height)
                        original_count += 1
                        frame_subtitle_found = True
                        break  # 每帧只统计一个字幕
    
    if not center_x_list:
        return None
    
    # 过滤异常值：字幕通常位置比较固定，使用Z-score方法过滤异常值
    import statistics
    
    filtered_count = len(center_x_list)
    
    # 先计算初始统计值
    if len(center_y_list) > 1:
        avg_center_y = sum(center_y_list) / len(center_y_list)
        std_center_y = statistics.stdev(center_y_list)
        
        # 使用Z-score过滤异常值（字幕的y坐标应该比较接近）
        # 过滤掉距离平均值超过2个标准差的点
        filtered_indices = []
        for i, center_y in enumerate(center_y_list):
            z_score = abs((center_y - avg_center_y) / std_center_y) if std_center_y > 0 else 0
            if z_score <= 2.0:  # 保留在2个标准差内的点
                filtered_indices.append(i)
        
        # 如果过滤后数据太少（少于原始数据的50%），说明可能没有明显的异常值，使用原始数据
        if len(filtered_indices) >= len(center_y_list) * 0.5:
            center_x_list = [center_x_list[i] for i in filtered_indices]
            center_y_list = [center_y_list[i] for i in filtered_indices]
            height_list = [height_list[i] for i in filtered_indices]
            filtered_count = len(filtered_indices)
    
    if not center_x_list:
        return None
    
    # 重新计算过滤后的平均值
    avg_center_x = sum(center_x_list) / len(center_x_list)
    avg_center_y = sum(center_y_list) / len(center_y_list)
    avg_height = sum(height_list) / len(height_list)
    
    # 计算标准差（用于评估一致性）
    std_center_x = statistics.stdev(center_x_list) if len(center_x_list) > 1 else 0
    std_center_y = statistics.stdev(center_y_list) if len(center_y_list) > 1 else 0
    std_height = statistics.stdev(height_list) if len(height_list) > 1 else 0
    
    # 计算范围
    min_x = min(center_x_list)
    max_x = max(center_x_list)
    min_y = min(center_y_list)
    max_y = max(center_y_list)
    min_height = min(height_list)
    max_height = max(height_list)
    
    return {
        "center_x": int(round(avg_center_x)),
        "center_y": int(round(avg_center_y)),
        "height": int(round(avg_height)),
        "valid_count": len(center_x_list),
        "original_count": original_count,
        "filtered_out": original_count - filtered_count,
        "std_center_x": float(std_center_x),
        "std_center_y": float(std_center_y),
        "std_height": float(std_height),
        "range": {
            "center_x": {"min": int(round(min_x)), "max": int(round(max_x))},
            "center_y": {"min": int(round(min_y)), "max": int(round(max_y))},
            "height": {"min": int(round(min_height)), "max": int(round(max_height))}
        }
    }


def process_video(video_path, output_dir="output", num_frames=30, api_url=None):
    """
    处理视频，识别字幕位置（仅支持API模式）
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        num_frames: 要抽取的帧数
        api_url: OCR API服务器地址（必需）
    """
    if not api_url:
        raise ValueError("必须提供API服务器地址，本地OCR模式已移除")
    
    logger.info(f"开始处理视频: {video_path}")
    logger.info(f"使用API模式，服务器地址: {api_url}")
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 测试API连接
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            logger.info("API服务器连接正常")
        else:
            logger.warning(f"API服务器响应异常 (状态码: {response.status_code})")
    except Exception as e:
        raise ConnectionError(f"无法连接到API服务器: {e}，请确保API服务器正在运行")
    
    # 抽取帧
    logger.info(f"从视频中随机抽取 {num_frames} 帧...")
    frames = extract_frames(video_path, num_frames)
    logger.info(f"成功抽取 {len(frames)} 帧")
    
    # 处理每一帧
    all_results = []
    for idx, (frame_num, frame) in enumerate(frames):
        logger.info(f"处理第 {idx+1}/{len(frames)} 帧 (原始帧号: {frame_num})...")
        
        # 保存原始图像
        frame_image_path = output_path / f"frame_{frame_num}.jpg"
        cv2.imwrite(str(frame_image_path), frame)
        
        # OCR识别
        logger.debug(f"进行OCR识别...")
        ocr_results = detect_subtitles(frame, api_url)
        
        # 处理结果
        frame_result = {
            "frame_number": int(frame_num),
            "frame_image_path": str(frame_image_path),
            "ocr_results": []
        }
        
        for res in ocr_results:
            # 打印结果
            res.print()

            # 保存可视化结果
            vis_path = output_path / f"frame_{frame_num}_ocr_vis.jpg"
            res.save_to_img(str(vis_path))

            # 保存JSON结果
            json_path = output_path / f"frame_{frame_num}_ocr_result.json"
            res.save_to_json(str(json_path))

            # 从JSON中提取字幕垂直位置和置信度
            subtitle_info = extract_subtitle_info(json_path)
            
            # 保存完整的结果信息
            frame_result["ocr_results"].append({
                "visualization_path": str(vis_path),
                "json_path": str(json_path),
                "subtitles": subtitle_info
            })
        
        all_results.append(frame_result)
    
    # 计算字幕中心点和高度
    subtitle_stats = calculate_subtitle_statistics(all_results)
    
    # 如果常规方法失败或结果不够可靠（有效数量少于3），使用兜底方案
    use_fallback = False
    if subtitle_stats is None:
        use_fallback = True
    elif subtitle_stats.get('valid_count', 0) < 3:
        # 常规方法结果不够可靠，使用兜底方案
        logger.info(f"常规方法检测到的有效字幕数量({subtitle_stats.get('valid_count', 0)})过少，切换到兜底方案...")
        use_fallback = True
    
    if use_fallback:
        subtitle_stats = calculate_subtitle_statistics_fallback(all_results)

    summary = {
        "video_path": str(video_path),
        "processed_time": datetime.now().isoformat(),
        "total_frames_processed": len(frames),
        "frames": all_results,
        "subtitle_statistics": subtitle_stats
    }
    
    logger.info(f"处理完成！结果已保存到: {output_path}")
    if subtitle_stats:
        logger.info("字幕统计信息:")
        if subtitle_stats.get('fallback_method', False):
            logger.info("  [使用兜底方案]")
        logger.info(f"  中心点坐标: ({subtitle_stats['center_x']}, {subtitle_stats['center_y']})")
        logger.info(f"  字幕高度: {subtitle_stats['height']} 像素")
        logger.info(f"  有效字幕数量: {subtitle_stats['valid_count']}")
        if subtitle_stats.get('filtered_out', 0) > 0:
            logger.info(f"  已过滤异常值: {subtitle_stats['filtered_out']} 个")
    else:
        logger.warning("未能获取字幕统计信息")
    
    return summary


def detect_subtitle_position(video_path, num_frames=30):
    """
    生产环境调用函数：检测视频字幕位置
    
    Args:
        video_path: 视频文件路径
        num_frames: 要抽取的帧数，默认30
    
    Returns:
        dict: 包含字幕位置信息的JSON格式字典
        {
            "center_x": int,
            "center_y": int,
            "height": int
        }
        如果检测失败，返回None
    """
    # 硬编码API URL
    API_URL = "http://172.17.7.215:1275"
    
    # 使用临时目录
    temp_dir = tempfile.mkdtemp(prefix='subtitle_detect_')
    
    try:
        # 调用process_video处理视频
        summary = process_video(
            video_path=video_path,
            output_dir=temp_dir,
            num_frames=num_frames,
            api_url=API_URL
        )
        
        # 获取字幕统计信息
        subtitle_stats = summary.get('subtitle_statistics')
        
        if not subtitle_stats:
            logger.warning("未能获取字幕统计信息")
            return None
        
        # 提取结果
        center_x = subtitle_stats.get('center_x')
        center_y = subtitle_stats.get('center_y')
        height = subtitle_stats.get('height')
        
        # 构建返回的JSON
        result = {
            "center_x": center_x,
            "center_y": center_y,
            "height": height
        }
        
        return result
        
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
        
    finally:
        # 清理临时文件（中间图片和JSON）
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"清理临时文件时发生错误: {e}")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 3:
        logger.info("使用方法: python subtitle_detector.py <视频文件路径> <API地址> [输出目录] [帧数]")
        logger.info("示例: python subtitle_detector.py video.mp4 http://192.168.1.100:1275 output 20")
        logger.info("注意: 必须提供API服务器地址，本地OCR模式已移除")
        sys.exit(1)
    
    video_path = sys.argv[1]
    api_url = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output"
    num_frames = int(sys.argv[4]) if len(sys.argv) > 4 else 30
    
    if not os.path.exists(video_path):
        logger.error(f"视频文件不存在: {video_path}")
        sys.exit(1)
    
    try:
        process_video(video_path, output_dir, num_frames, api_url=api_url)
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

