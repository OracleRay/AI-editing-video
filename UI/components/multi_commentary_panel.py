"""
多次解说面板
功能 3：基于现有剪辑结果，生成多次 AI 解说（步骤 7-10 循环执行）
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import sys
from typing import Dict, Optional
from utils.config_loader import get_config

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from UI.services.pipeline_service import PipelineService
from UI.utils.ui_helpers import (
    ThreadExecutor,
    show_error_message
)
from UI.utils.video_preview import VideoPreviewWidget


config = get_config()

class MultiCommentaryPanel(ttk.Frame):
    """多次解说面板"""
    
    # 配色方案
    COLORS = {
        'bg': '#F5F1EB',
        'panel_bg': '#FFFFFF',
        'text_bg': '#FAF7F2',
        'fg': '#3A3A38',
        'accent': '#7FA1A6',
        'text_gray': '#8B8378'
    }
    
    def __init__(self, parent):
        super().__init__(parent)
        self.pipeline_service = PipelineService()
        self.clip_srt_file = None
        self.edited_video = None
        self.progress_line_start = None  # 记录进度行的起始位置
        self.export_dir_var = tk.StringVar(value="")
        
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
            text="批量生成 AI 解说",
            font=("微软雅黑", 14, "bold"),
            foreground=self.COLORS['fg']
        )
        title.pack(anchor=tk.W)
        
        desc = ttk.Label(
            header_frame,
            text="基于已有的剪辑结果，批量生成多个不同的 AI 解说版本（步骤 7-10）\n每个版本都会自动复制到 JianyingPro Drafts，方便快速试用",
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
        
        # ========== 左侧：文件选择和参数设置（带滚动条）==========
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
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(left_frame, text=" 文件选择 ", padding=15)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 剪辑字幕文件
        srt_frame = ttk.Frame(file_frame)
        srt_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(
            srt_frame,
            text="剪辑字幕:",
            font=("微软雅黑", 9),
            width=10
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.srt_label = ttk.Label(
            srt_frame,
            text="未选择",
            font=("微软雅黑", 8),
            foreground=self.COLORS['text_gray']
        )
        self.srt_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(
            srt_frame,
            text="浏览",
            command=self._select_srt,
            width=8
        ).pack(side=tk.RIGHT)
        
        # 剪辑视频文件
        video_frame = ttk.Frame(file_frame)
        video_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(
            video_frame,
            text="剪辑视频:",
            font=("微软雅黑", 9),
            width=10
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.video_label = ttk.Label(
            video_frame,
            text="未选择",
            font=("微软雅黑", 8),
            foreground=self.COLORS['text_gray']
        )
        self.video_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(
            video_frame,
            text="浏览",
            command=self._select_video,
            width=8
        ).pack(side=tk.RIGHT)
        
        # 在文件选择框下方添加自动检测按钮
        auto_detect_frame = ttk.Frame(file_frame)
        auto_detect_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            auto_detect_frame,
            text="🔍 自动检测（最新一次的剪辑结果）",
            command=self._auto_select_both,
            width=30
        ).pack(side=tk.TOP, pady=5)
        
        # 参数设置区域
        param_frame = ttk.LabelFrame(left_frame, text=" 参数设置 ", padding=15)
        param_frame.pack(fill=tk.X, pady=(0, 15))
        
        count_frame = ttk.Frame(param_frame)
        count_frame.pack(fill=tk.X)
        
        ttk.Label(
            count_frame,
            text="生成次数:",
            font=("微软雅黑", 9)
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.count_spinbox = ttk.Spinbox(
            count_frame,
            from_=1,
            to=10,
            width=10,
            font=("微软雅黑", 9)
        )
        self.count_spinbox.set(3)
        self.count_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            count_frame,
            text="（1-10次）",
            font=("微软雅黑", 8),
            foreground=self.COLORS['text_gray']
        ).pack(side=tk.LEFT, padx=5)

        # 解说参数区域
        commentary_frame = ttk.LabelFrame(left_frame, text=" 解说参数（可选） ", padding=15)
        commentary_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            commentary_frame,
            text="剧情梗概:",
            font=("微软雅黑", 9)
        ).pack(anchor=tk.W, pady=(0, 5))

        self.plot_text = tk.Text(
            commentary_frame,
            height=4,
            wrap=tk.WORD,
            bg=self.COLORS['text_bg'],
            fg=self.COLORS['fg'],
            insertbackground=self.COLORS['fg'],
            relief=tk.FLAT
        )
        self.plot_text.pack(fill=tk.X, pady=(0, 10))
        
        # 导出目录
        export_frame = ttk.LabelFrame(left_frame, text=" 剪映导出目录 ", padding=15)
        export_frame.pack(fill=tk.X, pady=(0, 15))
        
        export_display_frame = ttk.Frame(export_frame)
        export_display_frame.pack(fill=tk.X)
        
        self.export_dir_display = tk.Label(
            export_display_frame,
            text="未选择",
            font=("微软雅黑", 9),
            bg=self.COLORS['text_bg'],
            fg=self.COLORS['fg'],
            anchor=tk.W,
            padx=10,
            pady=6
        )
        self.export_dir_display.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        ttk.Button(
            export_display_frame,
            text="选择目录",
            command=self._select_export_dir
        ).pack(side=tk.RIGHT)
        
        # 操作按钮
        button_frame = ttk.LabelFrame(left_frame, text=" 操作 ", padding=15)
        button_frame.pack(fill=tk.X, pady=(0, 0))
        
        self.process_btn = ttk.Button(
            button_frame,
            text="▶️ 开始批量生成",
            command=self._start_processing,
            style='Accent.TButton',
            state=tk.DISABLED
        )
        self.process_btn.pack(fill=tk.X)
        
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
        self._log_result("💡 请选择剪辑字幕文件和剪辑视频文件...\n")

    def _select_srt(self):
        """选择剪辑字幕文件"""
        file_path = filedialog.askopenfilename(
            title="选择剪辑字幕文件",
            filetypes=[
                ("字幕文件", "*.srt *.txt"),
                ("所有文件", "*.*")
            ],
            initialdir="resources/dst/srt_files/clip" if Path("resources/dst/srt_files/clip").exists() else None
        )
        
        if file_path:
            self.clip_srt_file = file_path
            self.srt_label.config(text=Path(file_path).name, foreground=self.COLORS['fg'])
            self._check_ready()
            self._log_result(f"\n✅ 已选择字幕文件: {Path(file_path).name}\n")
    
    def _select_video(self):
        """选择剪辑视频文件"""
        file_path = filedialog.askopenfilename(
            title="选择剪辑视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.avi *.mov *.mkv"),
                ("所有文件", "*.*")
            ],
            initialdir="resources/dst/videos" if Path("resources/dst/videos").exists() else None
        )
        
        if file_path:
            self.edited_video = file_path
            self.video_label.config(text=Path(file_path).name, foreground=self.COLORS['fg'])
            
            # 加载视频预览
            self.video_preview.load_video(file_path)
            
            self._check_ready()
            self._log_result(f"✅ 已选择视频文件: {Path(file_path).name}\n")
    
    def _check_ready(self):
        """检查是否可以开始处理"""
        if self.clip_srt_file and self.edited_video:
            self.process_btn.config(state=tk.NORMAL)
        else:
            self.process_btn.config(state=tk.DISABLED)
    
    def _start_processing(self):
        """开始处理"""
        if not self.clip_srt_file or not self.edited_video:
            show_error_message(self.winfo_toplevel(), "请先选择所有必需的文件")
            return
        if not self.export_dir_var.get().strip():
            show_error_message(self.winfo_toplevel(), "请先选择剪映导出目录")
            return
        
        try:
            count = int(self.count_spinbox.get())
            if count < 1 or count > 10:
                show_error_message(self.winfo_toplevel(), "生成次数必须在 1-10 之间")
                return
        except ValueError:
            show_error_message(self.winfo_toplevel(), "生成次数必须是数字")
            return
        
        self._log_result("\n" + "="*60 + "\n")
        self._log_result(f"🚀 开始批量生成 {count} 个 AI 解说版本...\n")
        self._log_result("="*60 + "\n\n")
        
        # 重置进度行标记
        self.progress_line_start = None
        
        # 禁用按钮
        self.process_btn.config(state=tk.DISABLED)
        
        # 在后台线程执行
        commentary_params = self._collect_commentary_params()
        def run_pipeline():
            return self.pipeline_service.run_multi_commentary(
                self.clip_srt_file,
                self.edited_video,
                count,
                progress_callback=self._update_progress,
                commentary_params=commentary_params,
                export_target_dir=self.export_dir_var.get().strip()
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
            self._log_result("\n" + "="*60 + "\n")
            self._log_result(f"✅ 批量生成完成！共生成 {result.get('count', 0)} 个版本\n\n")
            
            for item in result.get("results", []):
                self._log_result(f"  📄 版本 {item['iteration']}: {Path(item['commentary_srt_file']).name}\n")
                if item.get("desktop_project_path"):
                    self._log_result(f"     🗂️ 桌面目录: {item['desktop_project_path']}\n")
            
            self._log_result("\n🎬 所有版本已生成并复制到 JianyingPro Drafts\n")
            self._log_result(f"\n💡 {result.get('message', '处理完成')}\n")
            self._log_result("="*60 + "\n")
        else:
            error_msg = result.get("error", "未知错误")
            self._log_result(f"\n❌ 处理失败: {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
    
    def _log_result(self, message: str):
        """记录结果到文本框"""
        self.result_text.insert(tk.END, message)
        self.result_text.see(tk.END)
        self.result_text.update()

    def _collect_commentary_params(self) -> Dict[str, str]:
        """收集解说参数"""
        plot = self.plot_text.get("1.0", tk.END).strip()
        # 如果用户没有输入剧情内容，返回空字典
        if not plot:
            return {}
        return {"plot": plot}

    def _select_export_dir(self):
        """选择导出目录"""
        initial_dir = self.export_dir_var.get().strip() or str((Path.home() / "Desktop"))
        selected = filedialog.askdirectory(
            title="选择剪映导出目录",
            initialdir=initial_dir if Path(initial_dir).exists() else None
        )
        if selected:
            self.export_dir_var.set(selected)
            self.export_dir_display.config(text=selected)
            self._log_result(f"🗂️ 导出目录已设置为: {selected}\n")

    def _find_latest_srt_file(self):
        """自动查找最新的字幕文件"""
        workspace_dir = config.get_workspace_path("srt_files")
        clip_dir = workspace_dir / "clip"
        
        if not clip_dir.exists():
            return None
        
        # 查找所有包含"fresh"的txt文件
        fresh_files = list(clip_dir.glob("*_fresh.txt"))
        if not fresh_files:
            return None
        
        # 按修改时间排序，获取最新的文件
        latest_file = max(fresh_files, key=lambda x: x.stat().st_mtime)
        return str(latest_file)

    def _find_latest_video_file(self):
        """自动查找最新的视频文件"""
        workspace_dir =config.get_workspace_path("videos")
        videos_dir = workspace_dir
        
        if not videos_dir.exists():
            return None
        
        # 查找所有mp4文件
        video_files = list(videos_dir.glob("*.mp4"))
        if not video_files:
            return None
        
        # 按修改时间排序，获取最新的文件
        latest_file = max(video_files, key=lambda x: x.stat().st_mtime)
        return str(latest_file)

    def _auto_select_srt(self):
        """自动选择最新的字幕文件"""
        latest_srt = self._find_latest_srt_file()
        if latest_srt:
            self.clip_srt_file = latest_srt
            self.srt_label.config(text=Path(latest_srt).name, foreground=self.COLORS['fg'])
            self._check_ready()
            self._log_result(f"\n✅ 已自动选择最新字幕: {Path(latest_srt).name}\n")
        else:
            self._log_result("\n❌ 未找到最新的字幕文件\n")

    def _auto_select_video(self):
        """自动选择最新的视频文件"""
        latest_video = self._find_latest_video_file()
        if latest_video:
            self.edited_video = latest_video
            self.video_label.config(text=Path(latest_video).name, foreground=self.COLORS['fg'])
            self.video_preview.load_video(latest_video)
            self._check_ready()
            self._log_result(f"✅ 已自动选择最新视频: {Path(latest_video).name}\n")
        else:
            self._log_result("\n❌ 未找到视频文件\n")

    def _auto_select_both(self):
        """一键自动选择字幕和视频文件"""
        self._auto_select_srt()
        self._auto_select_video()
        self._check_ready()
        self._log_result("\n✅ 已一键自动选择字幕和视频文件\n")
