"""
AI 剪辑面板
功能 1：上传视频，生成 AI 剪辑结果到草稿（步骤 1-6）
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from pathlib import Path
import sys

# 添加项目根目录到路径（支持打包环境）
def _get_base_path() -> Path:
    """获取程序基础路径"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent.parent

project_root = _get_base_path()
sys.path.insert(0, str(project_root))

from UI.services.pipeline_service import PipelineService
from UI.utils.ui_helpers import (
    ThreadExecutor,
    show_error_message
)
from UI.utils.video_preview import VideoPreviewWidget
from UI.utils.video_player import VideoPlayerWidget


class EditingPanel(ttk.Frame):
    """AI 剪辑面板"""
    
    # 配色方案
    COLORS = {
        'bg': '#F5F1EB',
        'panel_bg': '#FFFFFF',
        'input_bg': '#F0EAE2',
        'text_bg': '#FAF7F2',
        'fg': '#3A3A38',
        'accent': '#7FA1A6',
        'border': '#D8D2C8',
        'text_gray': '#8B8378'
    }
    
    def __init__(self, parent):
        super().__init__(parent)
        self.pipeline_service = PipelineService()
        self.video_path = None
        self.progress_line_start = None  # 记录进度行的起始位置
        self.edited_video_player = None  # 剪辑视频播放器
        
        self.config(style='TFrame')
        self._create_widgets()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # 顶部说明区域
        header_frame = ttk.Frame(container)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title = ttk.Label(
            header_frame,
            text="AI 智能剪辑",
            font=("微软雅黑", 14, "bold"),
            foreground=self.COLORS['fg']
        )
        title.pack(anchor=tk.W)
        
        desc = ttk.Label(
            header_frame,
            text="上传视频文件，自动执行 AI 智能剪辑（步骤 1-6）\n生成剪辑后的视频和字幕文件",
            font=("微软雅黑", 9),
            foreground=self.COLORS['text_gray']
        )
        desc.pack(anchor=tk.W, pady=(5, 0))
        
        # 中间内容区域（两列布局：左-文件选择/按钮，右-视频预览+日志）
        content_frame = ttk.Frame(container)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.grid_columnconfigure(0, weight=1, minsize=350)  # 左侧：文件选择和按钮（可扩展）
        content_frame.grid_columnconfigure(1, weight=2)  # 右侧：视频预览+日志
        content_frame.grid_rowconfigure(0, weight=1)
        
        # ========== 左侧：文件选择和按钮（带滚动条）==========
        left_container = ttk.Frame(content_frame)
        left_container.grid(row=0, column=0, sticky='nsew', padx=(0, 10), pady=0)
        left_container.grid_rowconfigure(0, weight=1)
        left_container.grid_columnconfigure(0, weight=1)
        
        # 创建Canvas和Scrollbar
        left_canvas = tk.Canvas(
            left_container,
            bg=self.COLORS['panel_bg'],
            highlightthickness=0,
            relief=tk.FLAT
        )
        left_scrollbar = ttk.Scrollbar(
            left_container,
            orient=tk.VERTICAL,
            command=left_canvas.yview
        )
        
        # 创建可滚动的Frame
        left_frame = ttk.Frame(left_canvas, style='Panel.TFrame')
        left_frame_id = left_canvas.create_window((0, 0), window=left_frame, anchor='nw')
        
        # 配置Canvas滚动
        def configure_scroll_region(event):
            left_canvas.configure(scrollregion=left_canvas.bbox('all'))
        
        def configure_canvas_width(event):
            canvas_width = event.width
            left_canvas.itemconfig(left_frame_id, width=canvas_width)
        
        left_frame.bind('<Configure>', configure_scroll_region)
        left_canvas.bind('<Configure>', configure_canvas_width)
        
        # 鼠标滚轮支持
        def on_mousewheel(event):
            if left_canvas.winfo_containing(event.x_root, event.y_root):
                left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        left_canvas.bind("<MouseWheel>", on_mousewheel)
        left_frame.bind("<MouseWheel>", on_mousewheel)
        
        # 布局Canvas和Scrollbar（先pack滚动条，再pack Canvas）
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # 操作按钮区域
        button_frame = ttk.LabelFrame(left_frame, text=" 操作 ", padding=15)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 选择视频按钮
        select_btn = ttk.Button(
            button_frame,
            text="🎬 选择视频文件",
            command=self._select_video,
            style='TButton'
        )
        select_btn.pack(fill=tk.X, pady=(0, 10))
        
        # 开始处理按钮
        self.process_btn = ttk.Button(
            button_frame,
            text="▶️ 开始 AI 剪辑",
            command=self._start_processing,
            style='Accent.TButton',
            state=tk.DISABLED
        )
        self.process_btn.pack(fill=tk.X)
        
        # 剪辑视频预览区域
        edited_preview_frame = ttk.LabelFrame(left_frame, text=" 剪辑视频预览 ", padding=15)
        edited_preview_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 剪辑视频播放器组件
        self.edited_video_player = VideoPlayerWidget(
            edited_preview_frame,
            width=320,
            height=180
        )
        self.edited_video_player.pack()
        
        # 剧情内容输入框
        story_content_frame = ttk.LabelFrame(left_frame, text=" 剧情内容（可选） ", padding=15)
        story_content_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.story_content_text = tk.Text(
            story_content_frame,
            font=("微软雅黑", 10),
            wrap=tk.WORD,
            bg=self.COLORS['input_bg'],
            fg=self.COLORS['fg'],
            insertbackground=self.COLORS['fg'],
            selectbackground=self.COLORS['accent'],
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.story_content_text.pack(fill=tk.BOTH, expand=True)
        
        # ========== 右侧：视频预览 + 处理日志 ==========
        right_frame = ttk.Frame(content_frame)
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 0), pady=0)
        right_frame.grid_rowconfigure(1, weight=1)  # 日志区域可扩展
        right_frame.grid_columnconfigure(0, weight=1)
        
        # 视频预览标签框
        preview_label_frame = ttk.LabelFrame(right_frame, text=" 视频预览 ", padding=15)
        preview_label_frame.grid(row=0, column=0, sticky='ew', padx=0, pady=(0, 10))
        
        # 视频预览组件容器（用于居中）
        preview_container = ttk.Frame(preview_label_frame)
        preview_container.pack(pady=10)
        
        # 视频预览组件
        self.video_preview = VideoPreviewWidget(
            preview_container,
            width=280,
            height=160
        )
        self.video_preview.pack()
        
        # 结果显示标签框
        result_label_frame = ttk.LabelFrame(right_frame, text=" 处理日志 ", padding=15)
        result_label_frame.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)
        
        # 结果文本框
        result_frame = tk.Frame(result_label_frame, bg=self.COLORS['text_bg'])
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = tk.Text(
            result_frame,
            font=("Consolas", 9),
            wrap=tk.WORD,
            bg=self.COLORS['text_bg'],
            fg=self.COLORS['fg'],
            insertbackground=self.COLORS['fg'],
            selectbackground=self.COLORS['accent'],
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(result_frame, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        
        # 初始提示
        self._log_result("💡 请选择要处理的视频文件...\n", 'info')
    
    def _select_video(self):
        """选择视频文件"""
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            self.video_path = file_path
            
            # 加载视频预览
            self.video_preview.load_video(file_path)
            
            # 更新剪辑视频预览状态为"请等待剪辑完成..."
            self.edited_video_player._show_placeholder("请等待剪辑完成...")
            
            # 启用处理按钮
            self.process_btn.config(state=tk.NORMAL)
            
            # 记录日志
            self._log_result(f"\n✅ 已选择视频文件\n", 'success')
            self._log_result(f"   路径: {file_path}\n", 'info')
            self._log_result(f"   大小: {self._get_file_size(file_path)}\n\n", 'info')
    
    def _get_file_size(self, file_path: str) -> str:
        """获取文件大小"""
        try:
            size = Path(file_path).stat().st_size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.2f} KB"
            elif size < 1024 * 1024 * 1024:
                return f"{size / (1024 * 1024):.2f} MB"
            else:
                return f"{size / (1024 * 1024 * 1024):.2f} GB"
        except:
            return "未知"
    
    def _start_processing(self):
        """开始处理"""
        if not self.video_path:
            show_error_message(self.winfo_toplevel(), "请先选择视频文件")
            return
        
        self._log_result("\n" + "="*60 + "\n", 'info')
        self._log_result("🚀 开始执行 AI 智能剪辑流程...\n", 'header')
        self._log_result("="*60 + "\n\n", 'info')
        
        # 更新剪辑视频预览状态为"请等待剪辑完成..."
        if self.edited_video_player:
            self.edited_video_player._show_placeholder("请等待剪辑完成...")
        
        # 重置进度行标记
        self.progress_line_start = None
        
        # 禁用按钮
        self.process_btn.config(state=tk.DISABLED)
        
        # 在后台线程执行
        def run_pipeline():
            story_content = self.story_content_text.get("1.0", tk.END).strip()
            # 如果用户没有输入剧情内容，传递 None
            story_content = story_content if story_content else None
            return self.pipeline_service.run_editing_only(
                self.video_path,
                story_content=story_content,
                progress_callback=self._update_progress
            )
        
        ThreadExecutor.execute(run_pipeline, self._on_complete)
    
    def _update_progress(self, message: str, percent: int):
        """更新进度"""
        if percent >= 0:
            # 创建文本进度条
            bar_length = 30
            filled = int(bar_length * percent / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            progress_text = f"[{percent:3d}%] {bar} {message}"
            
            # 如果有旧的进度行，删除它
            if self.progress_line_start:
                self.result_text.delete(self.progress_line_start, f"{self.progress_line_start} lineend")
            else:
                # 第一次显示进度，记录起始位置
                self.progress_line_start = self.result_text.index("end-1c linestart")
            
            # 插入新的进度文本
            self.result_text.insert(self.progress_line_start, progress_text)
            self.result_text.see(tk.END)
            self.result_text.update()
            
            # 如果进度完成，换行并重置进度行标记
            if percent >= 100:
                self.result_text.insert(tk.END, "\n")
                self.progress_line_start = None
    
    def _on_complete(self, result: dict):
        """处理完成"""
        # 重置进度行标记
        self.progress_line_start = None
        
        # 启用按钮
        self.process_btn.config(state=tk.NORMAL)
        
        if result.get("success"):
            self._log_result("\n" + "="*60 + "\n", 'info')
            self._log_result("✅ AI 智能剪辑完成！\n\n", 'success')
            self._log_result(f"📹 剪辑视频: {result.get('edited_video', 'N/A')}\n", 'info')
            self._log_result(f"📄 字幕文件: {result.get('clip_srt_file', 'N/A')}\n", 'info')
            self._log_result(f"\n💡 {result.get('message', '处理完成')}\n", 'info')
            self._log_result("="*60 + "\n", 'info')
            
            # 加载剪辑完成的视频到播放器
            edited_video = result.get('edited_video')
            if edited_video and self.edited_video_player:
                # 转换为绝对路径
                from pathlib import Path
                from utils.config_loader import get_config
                config = get_config()
                
                # 处理相对路径和绝对路径
                if Path(edited_video).is_absolute():
                    video_abs_path = edited_video
                else:
                    video_abs_path = config.get_absolute_path(edited_video)
                
                print(f"尝试加载剪辑视频: {video_abs_path}")
                print(f"文件是否存在: {Path(video_abs_path).exists()}")
                
                if Path(video_abs_path).exists():
                    # 在主线程中加载视频（使用默认参数避免闭包问题）
                    def load_video(path=video_abs_path):
                        if self.edited_video_player:
                            self.edited_video_player.load_video(path)
                    self.after(0, load_video)
                else:
                    print(f"视频文件不存在: {video_abs_path}")
                    if self.edited_video_player:
                        self.edited_video_player._show_placeholder("视频文件未找到")
        else:
            error_msg = result.get("error", "未知错误")
            self._log_result(f"\n❌ 处理失败: {error_msg}\n", 'error')
            show_error_message(self.winfo_toplevel(), error_msg)
            
            # 处理失败时，恢复剪辑视频预览状态
            self.edited_video_player._show_placeholder("请等待剪辑完成...")
    
    def _log_result(self, message: str, msg_type: str = 'info'):
        """记录结果到文本框"""
        self.result_text.insert(tk.END, message)
        self.result_text.see(tk.END)
        self.result_text.update()
