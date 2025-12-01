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
                          audio_materials, video_track, audio_tracks,
                          video_filename, video_abs_path, aspect_ratio="16:9",
                          canvas_width=1920, canvas_height=1080):
    """生成剪映项目的 draft_content.json 数据"""
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
            "masks": [], "material_animations": [], "material_colors": [],
            "multi_language_refs": [], "placeholders": [], "plugin_effects": [],
            "primary_color_wheels": [], "realtime_denoises": [], "shapes": [],
            "smart_crops": [], "smart_relights": [], "sound_channel_mappings": [],
            "speeds": [{"curve_speed": None, "id": speed_id, "mode": 0, "speed": 1.0, "type": "speed"}],
            "stickers": [], "tail_leaders": [], "text_templates": [], "texts": [],
            "time_marks": [], "transitions": [], "video_effects": [], "video_trackings": [],
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
        "tracks": [video_track] + audio_tracks,
        "update_time": 0,
        "version": 360000
    }
    
    return project


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

