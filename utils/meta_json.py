def create_base_segment():
    """创建片段基础结构"""
    return {
        "enable_adjust": True,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "last_nonzero_volume": 1.0,
        "reverse": False,
        "track_attribute": 0,
        "track_render_index": 0,
        "visible": True,
        "common_keyframes": [],
        "keyframe_refs": [],
        "speed": 1.0,
        "is_tone_modify": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.0}
        },
        "uniform_scale": {"on": True, "value": 1.0},
        "render_index": 0
    }

def generate_project_data(video_mat_id, speed_id, total_duration, project_id,
                          audio_materials, video_tracks, audio_tracks,
                          video_filename, video_abs_path, aspect_ratio="16:9",
                          canvas_width=1920, canvas_height=1080,
                          mask_material=None, blur_effect_material=None,
                          text_materials=None, text_tracks=None, 
                          transition_materials=None):
    """
    生成剪映项目的 draft_content.json 数据
    
    Args:
        video_tracks: 视频轨道列表（可以有多个）
        mask_material: 蒙版材料（可选）
        blur_effect_material: 模糊特效材料（可选）
        text_materials: 文本材料列表（可选）
        text_tracks: 文本轨道列表（可选）
        transition_materials: 转场材料列表（可选）
    """
    # 准备蒙版和特效列表
    masks = [mask_material] if mask_material else []
    video_effects = [blur_effect_material] if blur_effect_material else []
    
    # 准备文本材料和轨道
    if text_materials is None:
        text_materials = []
    if text_tracks is None:
        text_tracks = []
    if transition_materials is None:
        transition_materials = []
    
    project = {
        "canvas_config": {"height": canvas_height, "ratio": aspect_ratio, "width": canvas_width},
        "color_space": 0,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": True,
            "material_save_mode": 0,
            "multi_language_current": "none",
            "multi_language_list": [],
            "multi_language_main": "none",
            "multi_language_mode": "none",
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_keywords_config": None,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "video_mute": False,
            "zoom_info_params": None
        },
        "cover": None,
        "create_time": 0,
        "duration": total_duration,
        "extra_info": None,
        "fps": 30,
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": project_id,
        "keyframe_graph_list": [],
        "keyframes": {
            "adjusts": [], "audios": [], "effects": [], "filters": [],
            "handwrites": [], "stickers": [], "texts": [], "videos": []
        },
        "last_modified_platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.9.0",
            "os": "windows"
        },
        "platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.9.0",
            "os": "windows"
        },
        "materials": {
            "ai_translates": [], "audio_balances": [], "audio_effects": [],
            "audio_fades": [], "audio_track_indexes": [], "audios": audio_materials,
            "beats": [], "canvases": [], "chromas": [], "color_curves": [],
            "digital_humans": [], "drafts": [], "effects": [], "flowers": [],
            "green_screens": [], "handwrites": [], "hsl": [], "images": [],
            "log_color_wheels": [], "loudnesses": [], "manual_deformations": [],
            "masks": masks,  # 添加蒙版材料
            "material_animations": [], "material_colors": [],
            "multi_language_refs": [], "placeholders": [], "plugin_effects": [],
            "primary_color_wheels": [], "realtime_denoises": [], "shapes": [],
            "smart_crops": [], "smart_relights": [], "sound_channel_mappings": [],
            "speeds": [{"curve_speed": None, "id": speed_id, "mode": 0, "speed": 1.0, "type": "speed"}],
            "stickers": [], "tail_leaders": [], "text_templates": [], "texts": text_materials,
            "time_marks": [], "transitions": transition_materials,  # 添加转场材料
            "video_effects": video_effects,  # 添加视频特效
            "video_trackings": [],
            "videos": [{
                "audio_fade": None,
                "category_id": "",
                "category_name": "local",
                "check_flag": 63487,
                "crop": {
                    "upper_left_x": 0.0, "upper_left_y": 0.0,
                    "upper_right_x": 1.0, "upper_right_y": 0.0,
                    "lower_left_x": 0.0, "lower_left_y": 1.0,
                    "lower_right_x": 1.0, "lower_right_y": 1.0
                },
                "crop_ratio": "free",
                "crop_scale": 1.0,
                "duration": total_duration,  # 使用项目总时长而不是视频原始时长
                "height": canvas_height,
                "id": video_mat_id,
                "local_material_id": "",
                "material_id": video_mat_id,
                "material_name": video_filename,
                "media_path": "",
                "path": video_abs_path,
                "type": "video",
                "width": canvas_width
            }],
            "vocal_beautifys": [], "vocal_separations": []
        },
        "mutable_config": None,
        "name": "",
        "new_version": "110.0.0",
        "relationships": [],
        "render_index_track_mode_on": False,
        "retouch_cover": None,
        "src": "default",
        "static_cover_image_path": "",
        "time_marks": None,
        "tracks": video_tracks + audio_tracks + text_tracks,  # 支持多个视频轨道和文本轨道
        "update_time": 0,
        "version": 360000
    }
    
    return project


def create_rectangle_mask(mask_id, subtitle_center_y, subtitle_height, canvas_height):
    """
    创建矩形蒙版材料（用于遮挡字幕）
    
    Args:
        mask_id: 蒙版ID
        subtitle_center_y: 字幕中心Y坐标（像素，从顶部开始）
        subtitle_height: 字幕高度（像素）
        canvas_height: 画布高度（像素）
    
    Returns:
        蒙版材料字典（符合剪映实际格式）
    """
    
    # 将像素坐标转换为剪映坐标系统
    # 剪映坐标系：-1（底部）到 1（顶部），0（中心）
    # 像素坐标系：0（顶部）到 canvas_height（底部）
    
    center_x = 0  # 水平居中
    width = 0.7  # 蒙版宽度：默认覆盖70%的画布宽度
    
    mask = {
        "config": {
            "aspectRatio": 1.0,
            "centerX": center_x,
            "centerY": subtitle_center_y,
            "feather": 0.0,
            "height": subtitle_height,
            "invert": False,
            "rotation": 0.0,
            "roundCorner": 0.0,
            "width": width
        },
        "id": mask_id,
        "name": "矩形",  # 剪映内置矩形蒙版的固定名称
        "path": "",  # 空字符串，剪映会自动处理缓存路径
        "platform": "all",
        "position_info": "",
        "resource_id": "6791700809454195207",  # 剪映内置矩形蒙版的固定资源ID
        "resource_type": "rectangle",  # 矩形蒙版类型
        "type": "mask"
    }
    
    return mask


def create_blur_effect(effect_id, intensity=50.0):
    """
    创建模糊特效材料
    
    Args:
        effect_id: 特效ID（UUID）
        intensity: 模糊强度 (0-100)
    
    Returns:
        特效材料字典（符合剪映实际格式）
    """
    # 根据真实剪映项目分析的格式
    # 使用剪映内置的模糊特效
    
    effect = {
        "adjust_params": [],
        "algorithm_artifact_path": "",
        "apply_target_type": 0,
        "apply_time_range": None,
        "category_id": "heycan_search_special_effect",
        "category_name": "heycan_search_special_effect",
        "common_keyframes": [],
        "disable_effect_faces": [],
        "effect_id": "634287",  # 剪映内置模糊特效的固定ID
        "formula_id": "",
        "id": effect_id,
        "name": "模糊",
        "path": "",  # 空字符串，剪映会自动处理缓存路径
        "platform": "all",
        "render_index": 11000,
        "request_id": "",
        "resource_id": "6710091790797509132",  # 剪映模糊特效的固定资源ID
        "source_platform": 0,
        "time_range": None,
        "track_render_index": 0,
        "type": "video_effect",
        "value": intensity / 100.0,  # 强度归一化到 0-1
        "version": ""
    }
    return effect


def create_text_material(text_id, text_content, 
                        color=(1.0, 1.0, 1.0),      # 字幕颜色 RGB (白色)
                        font_size=5.0,               # 字体大小
                        text_size=30               # 文本像素大小
                        ):
    """
    创建字幕文本材料（符合剪映实际格式）
    
    Args:
        text_id: 文本材料ID
        text_content: 字幕文本内容
        color: 字幕颜色 RGB 元组，范围 0.0-1.0，如 (1.0, 1.0, 0.0) 为黄色
        font_size: 字体大小，范围 1.0-20.0
        text_size: 文本像素大小
    
    Returns:
        文本材料字典
    """
    import json
    
    # 计算文本长度
    text_length = len(text_content)
    
    # 构建 content 字段（JSON 字符串格式）
    content_dict = {
        "styles": [{
            "fill": {
                "alpha": 1.0,
                "content": {
                    "render_type": "solid",
                    "solid": {
                        "alpha": 1.0,
                        "color": list(color)  # 使用参数
                    }
                }
            },
            "font": {
                "id": "",
                "path": "C:/JianyingPro/5.9.0.11632/Resources/Font/SystemFont/zh-hans.ttf"
            },
            "strokes": [
                {
                    "content": {
                        "solid": {
                            "color": [0, 0, 0],
                        }
                    },
                    "width": 0.08,
                }
            ],
            "size": font_size,
            "range": [0, text_length]
        }],
        "text": text_content
    }
    
    text_material = {
        "add_type": 0,
        "alignment": 1,  # 使用参数
        "background_alpha": 1.0,  # 使用参数
        "background_color": "#000000",
        "background_height": 0.14,
        "background_horizontal_offset": 0.0,
        "background_round_radius": 0.0,
        "background_style": 0,  # 使用参数
        "background_vertical_offset": 0.0,
        "background_width": 0.14,
        "base_content": "",
        "bold_width": 0.08,
        "border_alpha": 1.0,
        "border_color": "#000000",  # 使用参数
        "border_width": 0.08,
        "caption_template_info": {
            "category_id": "",
            "category_name": "",
            "effect_id": "",
            "is_new": False,
            "path": "",
            "request_id": "",
            "resource_id": "",
            "resource_name": "",
            "source_platform": 0
        },
        "check_flag": 15,
        "combo_info": {
            "text_templates": []
        },
        "content": json.dumps(content_dict, ensure_ascii=False),
        "fixed_height": -1.0,
        "fixed_width": -1.0,
        "font_category_id": "",
        "font_category_name": "",
        "font_id": "",
        "font_name": "",
        "font_path": "C:/JianyingPro/5.9.0.11632/Resources/Font/SystemFont/zh-hans.ttf",
        "font_resource_id": "",
        "font_size": 5.0,
        "font_source_platform": 0,
        "font_team_id": "",
        "font_title": "none",
        "font_url": "",
        "fonts": [],
        "force_apply_line_max_width": False,
        "global_alpha": 1.0,
        "group_id": "",
        "has_shadow": False,
        "id": text_id,
        "initial_scale": 1.0,
        "inner_padding": -1.0,
        "is_rich_text": False,
        "italic_degree": 0,
        "ktv_color": "",
        "language": "",
        "layer_weight": 1,
        "letter_spacing": 0.0,
        "line_feed": 1,
        "line_max_width": 0.82,
        "line_spacing": 0.02,
        "multi_language_current": "none",
        "name": "",
        "original_size": [],
        "preset_category": "",
        "preset_category_id": "",
        "preset_has_set_alignment": False,
        "preset_id": "",
        "preset_index": 0,
        "preset_name": "",
        "recognize_task_id": "",
        "recognize_type": 0,
        "relevance_segment": [],
        "shadow_alpha": 0.9,
        "shadow_angle": -45.0,
        "shadow_color": "",
        "shadow_distance": 5.0,
        "shadow_point": {
            "x": 0.6363961030678928,
            "y": -0.6363961030678928
        },
        "shadow_smoothing": 0.45,
        "shape_clip_x": False,
        "shape_clip_y": False,
        "source_from": "",
        "style_name": "",
        "sub_type": 0,
        "subtitle_keywords": None,
        "subtitle_template_original_fontsize": 0.0,
        "text_alpha": 1.0,
        "text_color": "#FFFFFF",
        "text_curve": None,
        "text_preset_resource_id": "",
        "text_size": text_size,  # 使用参数
        "text_to_audio_ids": [],
        "tts_auto_update": False,
        "type": "subtitle",
        "typesetting": 0,
        "underline": False,
        "underline_offset": 0.22,
        "underline_width": 0.05,
        "use_effect_default_color": True,
        "words": {
            "end_time": [],
            "start_time": [],
            "text": []
        }
    }
    return text_material


def create_text_segment(text_id, start_time, duration,
                       position_y=-0.75): # 垂直位置 (-1.0 到 1.0)
    """
    创建字幕文本片段（符合剪映实际格式）
    
    Args:
        text_id: 文本材料ID（与 segment ID 相同）
        start_time: 开始时间（微秒）
        duration: 持续时间（微秒）
        position_y: 垂直位置，-1.0(上) 到 1.0(下)，0.42 为底部（默认）
    
    Returns:
        文本片段字典
    """
    segment = {
        "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {
                "horizontal": False,
                "vertical": False
            },
            "rotation": 0.0,
            "scale": {
                "x": 1.0,
                "y": 1.0
            },
            "transform": {
                "x": 0.0,  # 使用参数
                "y": position_y   # 使用参数
            }
        },
        "common_keyframes": [],
        "enable_adjust": True,
        "enable_color_correct_adjust": True,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [],
        "group_id": "",
        "hdr_settings": {
            "intensity": 1.0,
            "mode": 1,
            "nits": 1000
        },
        "id": text_id,
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1.0,
        "material_id": text_id,
        "render_index": 0,
        "reverse": False,
        "source_timerange": None,
        "speed": 1.0,
        "target_timerange": {
            "duration": duration,
            "start": start_time
        },
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 0,
        "uniform_scale": {
            "on": True,
            "value": 1.0
        },
        "visible": True,
        "volume": 1.0
    }
    return segment


def create_transition(transition_id, name, resource_id, effect_id, duration=500000):
    """
    创建转场材料
    
    Args:
        transition_id: 转场ID（UUID）
        name: 转场名称
        resource_id: 资源ID
        effect_id: 特效ID
        duration: 转场时长（微秒），默认800000（0.8秒）
    
    Returns:
        转场材料字典
    """
    import uuid
    
    transition = {
        "category_id": "39663",
        "category_name": "热门",
        "duration": duration,
        "effect_id": effect_id,
        "id": transition_id,
        "is_overlap": True,
        "name": name,
        "path": "",  # 空路径，剪映会自动处理缓存
        "platform": "all",
        "request_id": uuid.uuid4().hex.upper(),
        "resource_id": resource_id,
        "type": "transition"
    }
    return transition


def generate_meta_info(project_id, total_duration):
    """生成剪映项目的 draft_meta_info.json 数据"""
    meta_info = {
        "cloud_package_completed_time": "",
        "draft_cloud_capcut_purchase_info": "",
        "draft_cloud_last_action_download": False,
        "draft_cloud_materials": [],
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "",
        "draft_deeplink_url": "",
        "draft_enterprise_info": {
            "draft_enterprise_extra": "",
            "draft_enterprise_id": "",
            "draft_enterprise_name": "",
            "enterprise_material": []
        },
        "draft_fold_path": "",
        "draft_id": project_id,
        "draft_is_ai_packaging_used": False,
        "draft_is_ai_shorts": False,
        "draft_is_ai_translate": False,
        "draft_is_article_video_draft": False,
        "draft_is_from_deeplink": "false",
        "draft_is_invisible": False,
        "draft_materials": [
            {"type": 0, "value": []}, {"type": 1, "value": []},
            {"type": 2, "value": []}, {"type": 3, "value": []},
            {"type": 6, "value": []}, {"type": 7, "value": []},
            {"type": 8, "value": []}
        ],
        "draft_materials_copied_info": [],
        "draft_name": "",
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": "",
        "draft_segment_extra_info": [],
        "draft_type": "",
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_modified": 0,
        "tm_draft_removed": 0,
        "tm_duration": total_duration
    }
    
    return meta_info

