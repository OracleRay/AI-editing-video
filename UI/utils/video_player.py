"""
视频播放器组件
支持视频预览功能，点击后使用系统默认播放器打开视频
"""

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path

import cv2
from PIL import Image, ImageTk


class VideoPlayerWidget(tk.Frame):
    """视频播放器组件"""
    
    def __init__(self, parent, width=360, height=200, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.width = width
        self.height = height
        self.video_path = None

        # 配置框架样式
        self.config(
            bg='#F2ECE3',
            relief=tk.FLAT,
            bd=0
        )
        
        # 创建画布
        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg='#F2ECE3',
            highlightthickness=0,
            relief=tk.FLAT,
            cursor='hand2'  # 鼠标悬停时显示手型
        )
        self.canvas.pack(padx=2, pady=2)
        
        # 绑定点击事件
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<Enter>', lambda e: self.canvas.config(cursor='hand2'))
        self.canvas.bind('<Leave>', lambda e: self.canvas.config(cursor=''))
        
        # 创建标签显示视频名称
        self.name_label = tk.Label(
            self,
            text="",
            font=("微软雅黑", 9),
            fg="#5B5955",
            bg='#F2ECE3',
            wraplength=width-20
        )
        self.name_label.pack(pady=5)
        
        # 显示占位图
        self._show_placeholder("请选择原视频")
    
    def _show_placeholder(self, text: str = "请选择原视频", clear_video_path: bool = True):
        """显示占位图
        
        Args:
            text: 占位图文本
            clear_video_path: 是否清除视频路径，默认True
        """
        from UI.utils.video_preview import VideoThumbnailExtractor
        placeholder = VideoThumbnailExtractor.create_placeholder(
            (self.width, self.height),
            text
        )
        self._display_image(placeholder)
        self.name_label.config(text="")
        
        # 只有在明确要求时才清除video_path
        if clear_video_path:
            self.video_path = None
    
    def _display_image(self, pil_image: Image.Image):
        """在画布上显示图片"""
        # 转换为 PhotoImage
        self.current_image = ImageTk.PhotoImage(pil_image)
        
        # 清除画布
        self.canvas.delete("all")
        
        # 显示图片
        self.canvas.create_image(
            self.width // 2,
            self.height // 2,
            image=self.current_image,
            anchor=tk.CENTER
        )
    
    def load_video(self, video_path: str):
        """
        加载视频
        
        Args:
            video_path: 视频文件路径
        """
        print(f"load_video 被调用, video_path: {video_path}")
        
        # 设置视频路径
        self.video_path = video_path
        video_name = Path(video_path).name
        
        print(f"video_path 已设置: {self.video_path}")
        
        # 提取第一帧作为预览
        thumbnail = self._extract_first_frame(video_path)
        
        if thumbnail:
            self._display_image(thumbnail)
            self.name_label.config(text=video_name)
            print(f"视频预览加载成功: {video_name}")
        else:
            # 如果提取失败，显示占位图但不清除video_path
            from UI.utils.video_preview import VideoThumbnailExtractor
            placeholder = VideoThumbnailExtractor.create_placeholder(
                (self.width, self.height),
                "无法加载视频"
            )
            self._display_image(placeholder)
            self.name_label.config(text=video_name)
            print(f"视频预览加载失败: {video_name}")
    
    def _extract_first_frame(self, video_path: str):
        """提取视频第一帧"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return None
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return None
            
            # BGR 转 RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 转换为 PIL Image
            img = Image.fromarray(frame_rgb)
            
            # 等比例缩放
            img.thumbnail((self.width, self.height), Image.Resampling.LANCZOS)
            
            # 创建一个固定尺寸的画布（带黑边）
            canvas = Image.new('RGB', (self.width, self.height), (20, 20, 25))
            
            # 计算居中位置
            offset_x = (self.width - img.width) // 2
            offset_y = (self.height - img.height) // 2
            
            # 粘贴到画布中央
            canvas.paste(img, (offset_x, offset_y))
            
            return canvas
            
        except Exception as e:
            print(f"提取视频帧失败: {e}")
            return None
    
    def _on_click(self, event):
        """点击画布时使用系统默认播放器打开视频"""
        print(f"点击视频预览区域, video_path: {self.video_path}")

        if not self.video_path:
            print("视频路径为空，无法播放")
            return

        video_path_obj = Path(self.video_path)
        if not video_path_obj.exists():
            print(f"视频文件不存在: {self.video_path}")
            return

        self._open_with_system_player(video_path_obj)

    def _open_with_system_player(self, video_path: Path):
        """调用系统默认播放器打开视频"""
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(video_path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(video_path)])
            else:
                subprocess.Popen(["xdg-open", str(video_path)])
            print(f"已尝试使用系统播放器打开视频: {video_path}")
        except Exception as exc:
            print(f"打开系统播放器失败: {exc}")

    def clear(self):
        """清除预览"""
        self.video_path = None
        self._show_placeholder("请选择原视频", clear_video_path=True)

