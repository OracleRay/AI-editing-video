"""
视频预览工具
提取视频缩略图用于 UI 预览
"""

import cv2
from pathlib import Path
from PIL import Image, ImageTk
import tkinter as tk
from typing import Optional, Tuple


class VideoThumbnailExtractor:
    """视频缩略图提取器"""
    
    @staticmethod
    def extract_thumbnail(
        video_path: str, 
        target_size: Tuple[int, int] = (320, 180),
        frame_position: float = 0.1
    ) -> Optional[Image.Image]:
        """
        从视频中提取缩略图
        
        Args:
            video_path: 视频文件路径
            target_size: 目标尺寸 (宽, 高)
            frame_position: 提取帧的位置（0-1之间，0.1表示视频10%的位置）
        
        Returns:
            PIL Image 对象，失败返回 None
        """
        try:
            # 打开视频文件
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                return None
            
            # 获取视频总帧数
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 计算要提取的帧位置
            frame_idx = int(total_frames * frame_position)
            
            # 定位到指定帧
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            
            # 读取帧
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return None
            
            # BGR 转 RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 转换为 PIL Image
            img = Image.fromarray(frame_rgb)
            
            # 等比例缩放
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # 创建一个固定尺寸的画布（带黑边）
            canvas = Image.new('RGB', target_size, (20, 20, 25))
            
            # 计算居中位置
            offset_x = (target_size[0] - img.width) // 2
            offset_y = (target_size[1] - img.height) // 2
            
            # 粘贴到画布中央
            canvas.paste(img, (offset_x, offset_y))
            
            return canvas
            
        except Exception as e:
            print(f"提取视频缩略图失败: {e}")
            return None
    
    @staticmethod
    def create_placeholder(
        target_size: Tuple[int, int] = (320, 180),
        text: str = "未选择视频"
    ) -> Image.Image:
        """
        创建占位图
        
        Args:
            target_size: 图片尺寸
            text: 显示文本
        
        Returns:
            PIL Image 对象
        """
        from PIL import ImageDraw, ImageFont
        
        # 创建渐变背景
        img = Image.new('RGB', target_size, (236, 231, 224))
        draw = ImageDraw.Draw(img)
        
        # 绘制边框
        draw.rectangle(
            [(0, 0), (target_size[0]-1, target_size[1]-1)],
            outline=(204, 195, 182),
            width=2
        )
        
        # 绘制图标（播放按钮）
        center_x, center_y = target_size[0] // 2, target_size[1] // 2
        icon_size = 40
        
        # 圆形背景
        draw.ellipse(
            [center_x - icon_size, center_y - icon_size - 20,
             center_x + icon_size, center_y + icon_size - 20],
            fill=(217, 209, 198),
            outline=(189, 179, 166),
            width=2
        )
        
        # 播放三角形
        play_points = [
            (center_x - 12, center_y - 30),
            (center_x - 12, center_y - 10),
            (center_x + 12, center_y - 20)
        ]
        draw.polygon(play_points, fill=(140, 137, 131))
        
        # 尝试使用字体，失败则使用默认字体
        try:
            font = ImageFont.truetype("msyh.ttc", 14)  # 微软雅黑
        except:
            font = ImageFont.load_default()
        
        # 绘制文本
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (target_size[0] - text_width) // 2
        text_y = center_y + 30
        
        draw.text((text_x, text_y), text, fill=(118, 112, 105), font=font)
        
        return img


class VideoPreviewWidget(tk.Frame):
    """视频预览组件"""
    
    def __init__(self, parent, width=320, height=180, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.width = width
        self.height = height
        self.current_image = None
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
            relief=tk.FLAT
        )
        self.canvas.pack(padx=2, pady=2)
        
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
        self._show_placeholder()
    
    def _show_placeholder(self, text: str = "未选择视频"):
        """显示占位图"""
        placeholder = VideoThumbnailExtractor.create_placeholder(
            (self.width, self.height),
            text
        )
        self._display_image(placeholder)
        self.name_label.config(text="")
    
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
        加载视频并显示缩略图
        
        Args:
            video_path: 视频文件路径
        """
        self.video_path = video_path
        video_name = Path(video_path).name
        
        # 显示加载中
        self._show_placeholder("加载中...")
        self.update()
        
        # 提取缩略图
        thumbnail = VideoThumbnailExtractor.extract_thumbnail(
            video_path,
            (self.width, self.height)
        )
        
        if thumbnail:
            self._display_image(thumbnail)
            self.name_label.config(text=video_name)
        else:
            self._show_placeholder("无法加载预览")
            self.name_label.config(text=video_name)
    
    def clear(self):
        """清除预览"""
        self.video_path = None
        self._show_placeholder()


class MultiVideoPreviewWidget(tk.Frame):
    """多视频预览组件 - 支持显示多个视频的缩略图"""
    
    def __init__(self, parent, width=360, height=200, thumb_size=(120, 68), **kwargs):
        super().__init__(parent, **kwargs)
        
        self.width = width
        self.height = height
        self.thumb_size = thumb_size
        self.video_paths = []
        self.thumbnails = []  # 保持引用防止被垃圾回收
        
        # 配置框架样式
        self.config(
            bg='#F2ECE3',
            relief=tk.FLAT,
            bd=0
        )
        
        # 创建带滚动条的画布
        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg='#F2ECE3',
            highlightthickness=0,
            relief=tk.FLAT
        )
        
        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 创建内部框架
        self.inner_frame = tk.Frame(self.canvas, bg='#F2ECE3')
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')
        
        # 布局
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定事件
        self.inner_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.inner_frame.bind('<MouseWheel>', self._on_mousewheel)
        
        # 创建标签显示视频数量
        self.count_label = tk.Label(
            self,
            text="",
            font=("微软雅黑", 9),
            fg="#5B5955",
            bg='#F2ECE3'
        )
        self.count_label.pack(pady=5)
        
        # 显示占位图
        self._show_placeholder()
    
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _show_placeholder(self, text: str = "未选择视频"):
        """显示占位图"""
        # 清除内部框架
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.thumbnails.clear()
        
        placeholder = VideoThumbnailExtractor.create_placeholder(
            (self.width - 20, self.height - 20),
            text
        )
        photo = ImageTk.PhotoImage(placeholder)
        self.thumbnails.append(photo)
        
        label = tk.Label(self.inner_frame, image=photo, bg='#F2ECE3')
        label.pack(padx=5, pady=5)
        self.count_label.config(text="")
    
    def load_videos(self, video_paths: list):
        """
        加载多个视频并显示缩略图
        
        Args:
            video_paths: 视频文件路径列表
        """
        self.video_paths = video_paths
        
        # 清除现有内容
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.thumbnails.clear()
        
        if not video_paths:
            self._show_placeholder()
            return
        
        # 显示加载中
        self._show_placeholder("加载中...")
        self.update()
        
        # 清除加载提示
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.thumbnails.clear()
        
        # 计算每行可放几个缩略图
        cols = max(1, (self.width - 20) // (self.thumb_size[0] + 10))
        
        # 创建缩略图网格
        for idx, video_path in enumerate(video_paths):
            row = idx // cols
            col = idx % cols
            
            # 创建单个视频预览框架
            frame = tk.Frame(self.inner_frame, bg='#F2ECE3')
            frame.grid(row=row, column=col, padx=5, pady=5)
            
            # 提取缩略图
            thumbnail = VideoThumbnailExtractor.extract_thumbnail(
                video_path,
                self.thumb_size
            )
            
            if thumbnail:
                photo = ImageTk.PhotoImage(thumbnail)
                self.thumbnails.append(photo)
                
                img_label = tk.Label(frame, image=photo, bg='#F2ECE3')
                img_label.pack()
            else:
                # 显示失败占位符
                placeholder = VideoThumbnailExtractor.create_placeholder(
                    self.thumb_size,
                    "加载失败"
                )
                photo = ImageTk.PhotoImage(placeholder)
                self.thumbnails.append(photo)
                
                img_label = tk.Label(frame, image=photo, bg='#F2ECE3')
                img_label.pack()
            
            # 显示文件名（截断）
            video_name = Path(video_path).stem
            if len(video_name) > 12:
                video_name = video_name[:10] + "..."
            
            name_label = tk.Label(
                frame,
                text=video_name,
                font=("微软雅黑", 8),
                fg="#5B5955",
                bg='#F2ECE3',
                wraplength=self.thumb_size[0]
            )
            name_label.pack()
        
        # 更新数量标签
        self.count_label.config(text=f"共 {len(video_paths)} 个视频")
        
        # 滚动到顶部
        self.canvas.yview_moveto(0)
    
    def load_video(self, video_path: str):
        """
        加载单个视频（兼容单视频模式）
        
        Args:
            video_path: 视频文件路径
        """
        self.load_videos([video_path] if video_path else [])
    
    def clear(self):
        """清除预览"""
        self.video_paths = []
        self._show_placeholder()
