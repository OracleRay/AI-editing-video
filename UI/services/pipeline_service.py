"""
视频处理流程服务
封装 step.py 中的流程，提供给 UI 调用
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# 添加项目根目录到路径（支持打包环境）
def _get_base_path() -> Path:
    """获取程序基础路径"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent.parent

project_root = _get_base_path()
sys.path.insert(0, str(project_root))

from step import (
    step1_video_to_audio,
    step2_audio_to_subtitles,
    step3_ai_editing_workflow,
    step4_editing_text_to_srt,
    step5_edit_video,
    step6_refresh_timeline,
    step7_ai_commentary_workflow,
    step8_commentary_text_to_srt,
    step9_generate_capcut_project,
    step10_copy_project_to_destination
)
from utils.config_loader import get_config
from utils.loggers import get_logger

# 静默模式，避免重复打印初始化信息
logger = get_logger('pipeline_service', silent=True)


class PipelineService:
    """视频处理流程服务类"""
    
    def __init__(self):
        self.config = get_config()
        self.step_data = {}
    
    def run_editing_only(
        self, 
        video_path: str, 
        progress_callback: Optional[Callable[[str, int], None]] = None,
        story_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        功能 1：只执行 AI 剪辑（步骤 1-6）
        
        Args:
            video_path: 上传的视频文件路径
            progress_callback: 进度回调函数，参数为(消息, 进度百分比)
            story_content: 剧情内容
        
        Returns:
            包含处理结果的字典
        """
        self.step_data = {}
        
        try:
            # 更新配置中的视频路径
            self._update_video_config(video_path)
            
            # 步骤 1：视频转音频
            if progress_callback:
                progress_callback("正在转换视频为音频...", 10)
            result = step1_video_to_audio()
            self.step_data.update(result)
            
            # 步骤 2：音频转字幕
            if progress_callback:
                progress_callback("正在识别音频生成字幕...", 25)
            result = step2_audio_to_subtitles(
                self.step_data["audio_output_path"],
                self.step_data["video_src_path"]
            )
            self.step_data.update(result)
            
            # 步骤 3：AI 剪辑工作流
            if progress_callback:
                progress_callback("正在运行 AI 剪辑工作流...", 45)
            editing_result = step3_ai_editing_workflow(self.step_data["original_text"], story_content)
            self.step_data["editing_text"] = editing_result["editing_text"]
            self.step_data["generated_plot"] = editing_result["generated_plot"]
            
            # 步骤 4：剪辑文本转 SRT
            if progress_callback:
                progress_callback("正在生成剪辑字幕文件...", 65)
            clip_srt_file = step4_editing_text_to_srt(self.step_data["editing_text"])
            self.step_data["clip_srt_file"] = clip_srt_file
            
            # 步骤 5：根据 SRT 剪辑视频
            if progress_callback:
                progress_callback("正在剪辑视频...", 75)
            edited_video = step5_edit_video(self.step_data["clip_srt_file"])
            self.step_data["edited_video"] = edited_video
            
            # 步骤 6：刷新时间戳
            if progress_callback:
                progress_callback("正在刷新时间戳...", 90)
            refreshed_clip_srt = step6_refresh_timeline(self.step_data["clip_srt_file"])
            self.step_data["refreshed_clip_srt"] = refreshed_clip_srt
            self.step_data["clip_srt_file"] = refreshed_clip_srt
            
            if progress_callback:
                progress_callback("AI 剪辑完成！", 100)
            
            logger.info("✅ AI 剪辑流程执行完成")
            return {
                "success": True,
                "edited_video": self.step_data["edited_video"],
                "clip_srt_file": self.step_data["clip_srt_file"],
                "message": "AI 剪辑完成"
            }
            
        except Exception as e:
            logger.error(f"AI 剪辑流程执行失败: {str(e)}")
            if progress_callback:
                progress_callback(f"错误: {str(e)}", -1)
            return {
                "success": False,
                "error": str(e),
                "message": f"执行失败: {str(e)}"
            }
    
    def run_full_pipeline(
        self, 
        video_path: str, 
        progress_callback: Optional[Callable[[str, int], None]] = None,
        plot_params: Optional[str] = None,
        export_target_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        功能 2：执行完整流程（步骤 1-10）
        
        Args:
            video_path: 上传的视频文件路径
            progress_callback: 进度回调函数，参数为(消息, 进度百分比)
            plot_params: 剧情参数（可选）
            export_target_dir: 导出目录
        
        Returns:
            包含处理结果的字典
        """
        self.step_data = {}
        if not export_target_dir:
            raise ValueError("请先选择剪映导出目录")
        
        try:
            # 更新配置中的视频路径
            self._update_video_config(video_path)
            
            # 步骤 1-6：AI 剪辑
            if progress_callback:
                progress_callback("正在执行 AI 剪辑（步骤 1-6）...", 5)
            
            result = self.run_editing_only(
                video_path, 
                lambda msg, pct: progress_callback(
                    msg,
                    int(min(pct * 0.6, 60))
                ),
                story_content=plot_params  # 直接传递 plot_params
            )
            
            if not result.get("success"):
                return result
            
            # 步骤 7：AI 解说工作流
            if progress_callback:
                progress_callback("正在运行 AI 解说工作流...", 70)
            # 使用从 AI 剪辑工作流生成的 plot，如果没有则使用用户输入的 plot
            commentary_plot = self.step_data.get("generated_plot") or plot_params
            commentary_text = step7_ai_commentary_workflow(
                self.step_data["clip_srt_file"],
                plot=commentary_plot
            )
            self.step_data["commentary_text"] = commentary_text
            
            # 步骤 8：解说文本转 SRT
            if progress_callback:
                progress_callback("正在生成解说字幕文件...", 80)
            commentary_srt_file = step8_commentary_text_to_srt(self.step_data["commentary_text"])
            self.step_data["commentary_srt_file"] = commentary_srt_file
            
            # 步骤 9：生成剪映项目
            if progress_callback:
                progress_callback("正在生成剪映项目...", 90)
            project_json_dir = step9_generate_capcut_project(
                self.step_data["edited_video"],
                self.step_data["commentary_srt_file"]
            )
            self.step_data["project_json_dir"] = project_json_dir
            self.step_data["export_destination_dir"] = export_target_dir or self.step_data.get("export_destination_dir")
            
            # 步骤 10：复制项目到指定目录
            if progress_callback:
                progress_callback("正在复制剪映项目到导出目录...", 95)
            desktop_project_path = step10_copy_project_to_destination(
                project_json_dir,
                self.step_data.get("export_destination_dir")
            )
            self.step_data["desktop_project_path"] = desktop_project_path
            
            if progress_callback:
                progress_callback("完整流程执行完成！", 100)
            
            logger.info("✅ 完整流程执行完成")
            return {
                "success": True,
                "edited_video": self.step_data["edited_video"],
                "commentary_srt_file": self.step_data["commentary_srt_file"],
                "project_json_dir": self.step_data.get("project_json_dir"),
                "desktop_project_path": self.step_data.get("desktop_project_path"),
                "message": "完整流程执行完成，已复制到 JianyingPro Drafts"
            }
            
        except Exception as e:
            logger.error(f"完整流程执行失败: {str(e)}")
            if progress_callback:
                progress_callback(f"错误: {str(e)}", -1)
            return {
                "success": False,
                "error": str(e),
                "message": f"执行失败: {str(e)}"
            }
    
    def run_multi_commentary(
        self, 
        clip_srt_file: str,
        edited_video: str,
        count: int = 3,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        commentary_params: Optional[Dict[str, str]] = None,
        export_target_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        功能 3：从步骤 7 开始，生成多次 AI 解说（循环执行）
        
        Args:
            clip_srt_file: 剪辑字幕文件路径
            edited_video: 剪辑后的视频文件路径
            count: 生成次数，默认 3 次
            progress_callback: 进度回调函数，参数为(消息, 进度百分比)
        
        Returns:
            包含处理结果的字典
        """
        results = []
        
        if not export_target_dir:
            raise ValueError("请先选择剪映导出目录")
        
        try:
            params = commentary_params or {}
            for i in range(count):
                if progress_callback:
                    progress_callback(f"正在生成第 {i+1}/{count} 次解说...", int((i / count) * 100))
                
                # 步骤 7：AI 解说工作流
                commentary_text = step7_ai_commentary_workflow(
                    clip_srt_file,
                    plot=params.get("plot")
                )
                
                # 步骤 8：解说文本转 SRT
                commentary_srt_file = step8_commentary_text_to_srt(commentary_text)
                
                # 步骤 9：生成剪映项目
                project_json_dir = step9_generate_capcut_project(edited_video, commentary_srt_file)
                
                # 步骤 10：复制到指定目录
                desktop_project_path = step10_copy_project_to_destination(
                    project_json_dir,
                    export_target_dir
                )
                
                results.append({
                    "iteration": i + 1,
                    "commentary_srt_file": commentary_srt_file,
                    "project_json_dir": project_json_dir,
                    "desktop_project_path": desktop_project_path,
                    "success": True
                })
                
                logger.info(f"✅ 第 {i+1} 次解说生成完成")
            
            if progress_callback:
                progress_callback(f"已完成 {count} 次解说生成！", 100)
            
            return {
                "success": True,
                "results": results,
                "count": count,
                "message": f"成功生成 {count} 次 AI 解说，并已复制到 JianyingPro Drafts"
            }
            
        except Exception as e:
            logger.error(f"多次解说生成失败: {str(e)}")
            if progress_callback:
                progress_callback(f"错误: {str(e)}", -1)
            return {
                "success": False,
                "error": str(e),
                "results": results,
                "message": f"执行失败: {str(e)}"
            }
    
    def _update_video_config(self, video_path: str):
        """
        更新配置中的视频路径
        
        Args:
            video_path: 新的视频文件路径
        """
        # 将上传的视频路径转换为相对于项目根目录的路径
        video_path_obj = Path(video_path)
        
        # 获取配置字典（通过 get_all 方法）
        config_dict = self.config.get_all()
        
        # 如果是绝对路径，尝试转换为相对路径
        if video_path_obj.is_absolute():
            try:
                rel_path = video_path_obj.relative_to(project_root)
                config_dict['video']['src'] = str(rel_path)
            except ValueError:
                # 如果不在项目根目录下，直接使用绝对路径
                config_dict['video']['src'] = str(video_path)
        else:
            config_dict['video']['src'] = str(video_path)
        
        # 更新内部配置（访问私有属性）
        self.config._config = config_dict
        
        logger.info(f"已更新视频配置路径: {config_dict['video']['src']}")
    
    def get_step_data(self) -> Dict[str, Any]:
        """
        获取当前流程的步骤数据
        
        Returns:
            步骤数据字典
        """
        return self.step_data.copy()

