"""
完整流程面板
功能 2：上传视频，生成 AI 剪辑 + AI 解说到草稿（步骤 1-10）
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import sys
from typing import Dict, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from UI.services.pipeline_service import PipelineService
from UI.utils.ui_helpers import (
    ThreadExecutor,
    show_error_message
)
from UI.utils.video_preview import VideoPreviewWidget


class FullPipelinePanel(ttk.Frame):
    """完整流程面板"""
    
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
        self.video_path = None
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
            text="完整处理流程",
            font=("微软雅黑", 14, "bold"),
            foreground=self.COLORS['fg']
        )
        title.pack(anchor=tk.W)
        
        desc = ttk.Label(
            header_frame,
            text="上传视频文件，自动执行完整流程（步骤 1-10）\n生成剪辑视频、AI 解说音频、剪映草稿并复制到 JianyingPro Drafts",
            font=("微软雅黑", 9),
            foreground=self.COLORS['text_gray']
        )
        desc.pack(anchor=tk.W, pady=(5, 0))
        
        # 中间内容区域（三列布局：左-文件选择/按钮，中-视频预览，右-日志）
        content_frame = ttk.Frame(container)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.grid_columnconfigure(0, weight=0, minsize=280)  # 左侧：文件选择和按钮
        content_frame.grid_columnconfigure(1, weight=0, minsize=380)  # 中间：视频预览
        content_frame.grid_columnconfigure(2, weight=1)  # 右侧：日志（自动扩展）
        content_frame.grid_rowconfigure(0, weight=1)
        
        # ========== 左侧：文件选择和按钮（带滚动条）==========
        left_container = ttk.Frame(content_frame)
        left_container.grid(row=0, column=0, sticky='nsew', padx=(0, 10), pady=0)
        
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
        
        # 布局Canvas和Scrollbar
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # 操作按钮区域
        button_frame = ttk.LabelFrame(left_frame, text=" 操作 ", padding=15)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 选择视频按钮
        select_btn = ttk.Button(
            button_frame,
            text="📁 选择视频文件",
            command=self._select_video,
            style='TButton'
        )
        select_btn.pack(fill=tk.X, pady=(0, 10))
        
        # 开始处理按钮
        self.process_btn = ttk.Button(
            button_frame,
            text="▶️ 开始完整处理",
            command=self._start_processing,
            style='Accent.TButton',
            state=tk.DISABLED
        )
        self.process_btn.pack(fill=tk.X)

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
        
        # 流程说明
        info_frame = ttk.LabelFrame(left_frame, text=" 流程说明 ", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 0))
        
        steps = [
            "视频转音频",
            "音频转字幕",
            "AI 智能剪辑",
            "生成剪辑字幕",
            "视频剪辑",
            "刷新时间戳",
            "AI 生成解说",
            "解说转字幕",
            "生成剪映草稿",
            "复制到 JianyingPro Drafts"
        ]
        
        for idx, step in enumerate(steps, start=1):
            row = ttk.Frame(info_frame, style='Panel.TFrame')
            row.pack(fill=tk.X, pady=3)
            
            number_label = tk.Label(
                row,
                text=f"{idx:02d}",
                font=("微软雅黑", 9, "bold"),
                width=3,
                bg=self.COLORS['accent'],
                fg="#FFFFFF",
                padx=4,
                pady=2
            )
            number_label.pack(side=tk.LEFT, padx=(0, 8))
            
            step_label = ttk.Label(
                row,
                text=step,
                font=("微软雅黑", 9),
                foreground=self.COLORS['text_gray']
            )
            step_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # ========== 中间：视频预览 ==========
        middle_frame = ttk.Frame(content_frame)
        middle_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=0)
        middle_frame.grid_rowconfigure(0, weight=1)
        
        # 视频预览标签框
        preview_label_frame = ttk.LabelFrame(middle_frame, text=" 视频预览 ", padding=15)
        preview_label_frame.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        preview_label_frame.grid_rowconfigure(0, weight=1)
        preview_label_frame.grid_columnconfigure(0, weight=1)
        
        # 视频预览组件容器（用于居中）
        preview_container = ttk.Frame(preview_label_frame)
        preview_container.grid(row=0, column=0, sticky='', padx=0, pady=10)
        
        # 视频预览组件
        self.video_preview = VideoPreviewWidget(
            preview_container,
            width=360,
            height=200
        )
        self.video_preview.pack()
        
        # ========== 右侧：处理结果 ==========
        right_frame = ttk.Frame(content_frame)
        right_frame.grid(row=0, column=2, sticky='nsew', padx=(10, 0), pady=0)
        
        # 结果显示标签框
        result_label_frame = ttk.LabelFrame(right_frame, text=" 处理日志 ", padding=15)
        result_label_frame.pack(fill=tk.BOTH, expand=True)
        
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
        self._log_result("💡 请选择要处理的视频文件...\n")
    
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
            
            # 启用处理按钮
            self.process_btn.config(state=tk.NORMAL)
            
            # 记录日志
            self._log_result(f"\n✅ 已选择视频文件\n")
            self._log_result(f"   路径: {file_path}\n")
            self._log_result(f"   大小: {self._get_file_size(file_path)}\n\n")
    
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
        if not self.export_dir_var.get().strip():
            show_error_message(self.winfo_toplevel(), "请先选择剪映导出目录")
            return
        
        self._log_result("\n" + "="*60 + "\n")
        self._log_result("🚀 开始执行完整处理流程...\n")
        self._log_result("="*60 + "\n\n")
        
        # 重置进度行标记
        self.progress_line_start = None
        
        # 禁用按钮
        self.process_btn.config(state=tk.DISABLED)
        
        # 在后台线程执行
        plot_params = self._collect_plot_params()
        def run_pipeline():
            return self.pipeline_service.run_full_pipeline(
                self.video_path,
                progress_callback=self._update_progress,
                plot_params=plot_params,
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
            self._log_result("✅ 完整流程执行完成！\n\n")
            self._log_result(f"📹 剪辑视频: {result.get('edited_video', 'N/A')}\n")
            self._log_result(f"📄 解说字幕: {result.get('commentary_srt_file', 'N/A')}\n")
            self._log_result(f"🎬 已生成剪映草稿项目\n")
            desktop_project = result.get('desktop_project_path')
            if desktop_project:
                self._log_result(f"🗂️ 桌面项目副本: {desktop_project}\n")
            else:
                self._log_result("⚠️ 未复制到 JianyingPro Drafts，请手动检查\n")
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

    def _collect_plot_params(self) -> str:
        """收集剧情梗概参数"""
        plot = self.plot_text.get("1.0", tk.END).strip()
        # 如果用户没有输入剧情内容，返回空字符串
        return plot if plot else ""
    
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
