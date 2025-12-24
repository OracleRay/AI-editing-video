"""
完整流程面板
功能 2：上传视频，生成 AI 剪辑 + AI 解说到草稿（步骤 1-10）
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import sys
import shutil
import random
from typing import Optional, List

# 添加项目根目录到路径（支持打包环境）
def _get_base_path() -> Path:
    """获取程序基础路径"""
    if getattr(sys, 'frozen', False):
        # 单文件模式：资源在 sys._MEIPASS 临时目录（PyInstaller）
        # 对于 Nuitka，使用 sys.executable 的父目录
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        else:
            # Nuitka 单文件模式
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
from utils.config_loader import get_workspace_path


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
    
    # 文件扩展名常量
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.flac', '.aac']
    
    def __init__(self, parent):
        super().__init__(parent)
        self.pipeline_service = PipelineService()
        self.video_path = None
        self.video_paths = []  # 存储多个视频路径（文件夹模式）
        self.progress_line_start = None  # 记录进度行的起始位置
        self.export_dir_var = tk.StringVar(value="")
        self.clone_audio_path = None  # 克隆声音文件路径
        # BGM功能已改为从workspace/bgm文件夹随机选择，不再需要存储路径
        
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
        
        # 选择视频按钮（支持文件和文件夹）
        select_btn = ttk.Button(
            button_frame,
            text="🎬 选择视频（文件/文件夹）",
            command=self._select_video_or_folder,
            style='TButton'
        )
        select_btn.pack(fill=tk.X, pady=(0, 10))
        
        # 克隆声音选择区域
        clone_audio_frame = ttk.Frame(button_frame)
        clone_audio_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 克隆声音选择按钮
        clone_audio_btn = ttk.Button(
            clone_audio_frame,
            text="🎤 选择克隆声音",
            command=self._select_clone_audio,
            style='TButton'
        )
        clone_audio_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # 倍速和音量选择框
        params_frame = ttk.Frame(clone_audio_frame)
        params_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 倍速选择
        speed_frame = ttk.Frame(params_frame)
        speed_frame.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(
            speed_frame,
            text="倍速:",
            font=("微软雅黑", 9)
        ).pack(side=tk.LEFT, padx=(0, 3))
        
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_spinbox = ttk.Spinbox(
            speed_frame,
            from_=0.5,
            to=2.0,
            increment=0.1,
            textvariable=self.speed_var,
            width=6,
            font=("微软雅黑", 9)
        )
        self.speed_spinbox.pack(side=tk.LEFT)
        
        # 音量选择
        volume_frame = ttk.Frame(params_frame)
        volume_frame.pack(side=tk.LEFT)
        
        ttk.Label(
            volume_frame,
            text="音量:",
            font=("微软雅黑", 9)
        ).pack(side=tk.LEFT, padx=(0, 3))
        
        self.volume_var = tk.DoubleVar(value=1.0)
        self.volume_spinbox = ttk.Spinbox(
            volume_frame,
            from_=0.1,
            to=2.0,
            increment=0.1,
            textvariable=self.volume_var,
            width=6,
            font=("微软雅黑", 9)
        )
        self.volume_spinbox.pack(side=tk.LEFT)
        
        # BGM选择区域
        bgm_frame = ttk.Frame(button_frame)
        bgm_frame.pack(fill=tk.X, pady=(0, 10))
        
        # BGM添加按钮
        bgm_btn = ttk.Button(
            bgm_frame,
            text="🎵 添加bgm（可选）",
            command=self._add_bgm,
            style='TButton'
        )
        bgm_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # BGM音量选择
        bgm_volume_frame = ttk.Frame(bgm_frame)
        bgm_volume_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(
            bgm_volume_frame,
            text="bgm音量:",
            font=("微软雅黑", 9)
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.bgm_volume_var = tk.DoubleVar(value=0.5)
        self.bgm_volume_spinbox = ttk.Spinbox(
            bgm_volume_frame,
            from_=0.0,
            to=2.0,
            increment=0.1,
            textvariable=self.bgm_volume_var,
            width=6,
            font=("微软雅黑", 9)
        )
        self.bgm_volume_spinbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 开始处理按钮
        self.process_btn = ttk.Button(
            button_frame,
            text="▶️ 开始单次处理",
            command=self._start_processing,
            style='Accent.TButton',
            state=tk.DISABLED
        )
        self.process_btn.pack(fill=tk.X, pady=(0, 10))
        
        # 循环处理区域
        loop_control_frame = ttk.Frame(button_frame)
        loop_control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            loop_control_frame,
            text="循环次数:",
            font=("微软雅黑", 9)
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        # 循环次数变量
        self.loop_count_var = tk.IntVar(value=3)
        
        # 次数选择器（使用 Spinbox）
        self.loop_spinbox = ttk.Spinbox(
            loop_control_frame,
            from_=2,
            to=10,
            textvariable=self.loop_count_var,
            width=8,
            font=("微软雅黑", 9)
        )
        self.loop_spinbox.pack(side=tk.LEFT, padx=(0, 8))
        
        # 循环处理按钮
        self.loop_process_btn = ttk.Button(
            loop_control_frame,
            text="🔄 开始循环处理",
            command=self._start_loop_processing,
            style='Accent.TButton',
            state=tk.DISABLED
        )
        self.loop_process_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

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
        
        # 解说参数区域
        commentary_frame = ttk.LabelFrame(left_frame, text=" 解说参数（可选） ", padding=15)
        commentary_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            commentary_frame,
            text="剧情梗概:",
            font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=(0, 5))

        self.plot_text = tk.Text(
            commentary_frame,
            height=20,
            wrap=tk.WORD,
            font=("宋体", 11),
            bg=self.COLORS['text_bg'],
            fg=self.COLORS['fg'],
            insertbackground=self.COLORS['fg'],
            relief=tk.FLAT,
        )
        self.plot_text.pack(fill=tk.X, pady=(0, 40))
        
        # 绑定文本变化事件
        self.plot_text.bind('<<Modified>>', self._on_plot_text_modified)
        
        # ========== 右侧：任务清单 + 处理日志 ==========
        right_frame = ttk.Frame(content_frame)
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 0), pady=0)
        right_frame.grid_rowconfigure(1, weight=1)  # 日志区域可扩展
        right_frame.grid_columnconfigure(0, weight=1)
        
        # 任务清单标签框
        checklist_label_frame = ttk.LabelFrame(right_frame, text=" 任务清单 ", padding=15)
        checklist_label_frame.grid(row=0, column=0, sticky='ew', padx=0, pady=(0, 10))
        
        # 创建任务清单项目
        self.checklist_items = {}
        
        # 定义任务项
        tasks = [
            ("video", "选择视频", True),  # (key, 标题, 是否必须)
            ("audio", "选择克隆声音", True),
            ("bgm", "添加bgm", False),
            ("export", "选择剪映目录", True),
            ("plot", "填写剧情", False)
        ]
        
        for key, title, required in tasks:
            task_frame = ttk.Frame(checklist_label_frame)
            task_frame.pack(fill=tk.X, pady=5)
            
            # 状态图标
            status_label = tk.Label(
                task_frame,
                text="×",
                font=("微软雅黑", 14, "bold"),
                fg="#999999" if not required else "#E74C3C",
                bg=self.COLORS['panel_bg'],
                width=2
            )
            status_label.pack(side=tk.LEFT, padx=(0, 8))
            
            # 任务名称
            title_label = ttk.Label(
                task_frame,
                text=title,
                font=("微软雅黑", 9, "bold"),
                foreground=self.COLORS['fg']
            )
            title_label.pack(side=tk.LEFT, padx=(0, 10))
            
            # 文件名显示
            filename_label = ttk.Label(
                task_frame,
                text="",
                font=("微软雅黑", 8),
                foreground=self.COLORS['text_gray']
            )
            filename_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 保存引用
            self.checklist_items[key] = {
                'status': status_label,
                'filename': filename_label,
                'required': required
            }
        
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
        self._log_result("💡 请选择要处理的视频文件...\n")
        
        # 初始化时检查BGM库状态
        bgm_count = self._get_bgm_count()
        if bgm_count > 0:
            self._update_checklist('bgm', f"BGM库 ({bgm_count} 个文件)")
    
    def _find_files_by_extensions(self, folder: Path, extensions: List[str]) -> List[Path]:
        """
        在文件夹中查找指定扩展名的文件（不区分大小写）
        
        Args:
            folder: 要搜索的文件夹路径
            extensions: 文件扩展名列表（如 ['.mp3', '.wav']）
        
        Returns:
            找到的文件路径列表（已去重）
        """
        files = []
        for ext in extensions:
            files.extend(folder.glob(f'*{ext}'))
            files.extend(folder.glob(f'*{ext.upper()}'))
        return list(set(files))
    
    def _copy_file_with_rename(self, source_file: Path, target_dir: Path) -> Path:
        """
        复制文件到目标目录，如果文件已存在则自动重命名
        
        Args:
            source_file: 源文件路径
            target_dir: 目标目录路径
        
        Returns:
            实际保存的文件路径
        """
        filename = source_file.name
        target_path = target_dir / filename
        
        # 如果目标文件已存在，添加序号避免覆盖
        if target_path.exists():
            base_name = source_file.stem
            extension = source_file.suffix
            counter = 1
            while target_path.exists():
                new_filename = f"{base_name}_{counter}{extension}"
                target_path = target_dir / new_filename
                counter += 1
        
        # 复制文件
        shutil.copy2(str(source_file), target_path)
        return target_path
    
    def _show_file_or_folder_choice(self, prompt_text, file_button_text, folder_button_text, 
                                     file_callback, folder_callback):
        """
        显示文件或文件夹选择对话框（通用方法）
        
        Args:
            prompt_text: 提示文本
            file_button_text: 文件按钮文本
            folder_button_text: 文件夹按钮文本
            file_callback: 选择文件后的回调函数（无参数）
            folder_callback: 选择文件夹后的回调函数（无参数）
        """
        # 创建一个顶层窗口用于选择
        choice_window = tk.Toplevel(self.winfo_toplevel())
        choice_window.title("选择方式")
        choice_window.geometry("300x150")
        choice_window.resizable(False, False)
        
        # 居中显示
        choice_window.transient(self.winfo_toplevel())
        choice_window.grab_set()
        
        # 设置窗口位置居中
        choice_window.update_idletasks()
        x = (choice_window.winfo_screenwidth() - choice_window.winfo_width()) // 2
        y = (choice_window.winfo_screenheight() - choice_window.winfo_height()) // 2
        choice_window.geometry(f"+{x}+{y}")
        
        # 提示文本
        label = ttk.Label(
            choice_window,
            text=prompt_text,
            font=("微软雅黑", 11),
            justify=tk.CENTER
        )
        label.pack(pady=20)
        
        # 按钮容器
        button_frame = ttk.Frame(choice_window)
        button_frame.pack(pady=10)
        
        def select_file():
            choice_window.destroy()
            file_callback()
        
        def select_folder():
            choice_window.destroy()
            folder_callback()
        
        # 选择文件按钮
        file_btn = ttk.Button(
            button_frame,
            text=file_button_text,
            command=select_file,
            width=15
        )
        file_btn.pack(side=tk.LEFT, padx=5)
        
        # 选择文件夹按钮
        folder_btn = ttk.Button(
            button_frame,
            text=folder_button_text,
            command=select_folder,
            width=15
        )
        folder_btn.pack(side=tk.LEFT, padx=5)
        
        # 等待窗口关闭
        choice_window.wait_window()
    
    def _select_video_or_folder(self):
        """选择视频文件或文件夹（弹出选择对话框）"""
        self._show_file_or_folder_choice(
            prompt_text="请选择您要处理的视频：",
            file_button_text="🎬 选择单个文件",
            folder_button_text="📁 选择文件夹",
            file_callback=self._select_video,
            folder_callback=self._select_folder
        )
    
    def _select_video(self):
        """选择单个视频文件"""
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            self.video_path = file_path
            self.video_paths = [file_path]  # 单文件模式
            
            # 更新任务清单
            filename = Path(file_path).name
            self._update_checklist('video', filename)
            
            # 启用处理按钮
            self.process_btn.config(state=tk.NORMAL)
            self.loop_process_btn.config(state=tk.NORMAL)
            
            # 记录日志
            self._log_result(f"\n✅ 已选择视频文件\n")
            self._log_result(f"   路径: {file_path}\n")
            self._log_result(f"   大小: {self._get_file_size(file_path)}\n\n")
    
    def _select_folder(self):
        """选择视频文件夹"""
        folder_path = filedialog.askdirectory(title="选择视频文件夹")
        
        if folder_path:
            folder = Path(folder_path)
            # 查找所有视频文件
            video_files = self._find_files_by_extensions(folder, self.VIDEO_EXTENSIONS)
            
            # 排序
            video_files = sorted(video_files, key=lambda x: x.name)
            
            if video_files:
                self.video_paths = [str(f) for f in video_files]
                self.video_path = self.video_paths[0]  # 兼容单文件处理
                
                # 更新任务清单（显示文件夹名和文件数）
                folder_name = Path(folder_path).name
                self._update_checklist('video', f"{folder_name} ({len(video_files)} 个视频)")
                
                # 启用处理按钮
                self.process_btn.config(state=tk.NORMAL)
                self.loop_process_btn.config(state=tk.NORMAL)
                
                # 记录日志
                self._log_result(f"\n✅ 已选择视频文件夹\n")
                self._log_result(f"   路径: {folder_path}\n")
                self._log_result(f"   共找到 {len(self.video_paths)} 个视频文件:\n")
                for i, vp in enumerate(self.video_paths, 1):
                    self._log_result(f"   {i}. {Path(vp).name}\n")
                self._log_result("\n")
            else:
                self._log_result(f"\n⚠️ 文件夹中未找到视频文件: {folder_path}\n\n")
    
    def _select_clone_audio(self):
        """选择克隆声音文件"""
        file_path = filedialog.askopenfilename(
            title="选择克隆声音文件",
            filetypes=[
                ("音频文件", "*.mp3 *.wav *.m4a *.flac *.aac"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            self.clone_audio_path = file_path
            # 显示文件名
            filename = Path(file_path).name
            # 更新任务清单
            self._update_checklist('audio', filename)
            self._log_result(f"\n✅ 已选择克隆声音: {filename}\n")
            self._log_result(f"   路径: {file_path}\n\n")
    
    def _add_bgm(self):
        """添加BGM文件或文件夹到workspace/bgm文件夹（弹出选择对话框）"""
        self._show_file_or_folder_choice(
            prompt_text="请选择要添加的BGM：",
            file_button_text="🎵 选择单个文件",
            folder_button_text="📁 选择文件夹",
            file_callback=self._add_bgm_file,
            folder_callback=self._add_bgm_folder
        )
    
    def _add_bgm_file(self):
        """选择单个BGM文件并添加到库"""
        file_path = filedialog.askopenfilename(
            title="选择要添加的BGM音频文件",
            filetypes=[
                ("音频文件", "*.mp3 *.wav *.m4a *.flac *.aac"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            source_file = Path(file_path)
            if not source_file.exists():
                return
            
            # 获取workspace/bgm文件夹路径
            bgm_dir = get_workspace_path("bgm")
            bgm_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制文件（自动处理重命名）
            target_path = self._copy_file_with_rename(source_file, bgm_dir)
            
            # 更新任务清单（显示BGM库中的文件数量）
            bgm_count = self._get_bgm_count()
            self._update_checklist('bgm', f"BGM库 ({bgm_count} 个文件)")
            
            # 记录日志
            self._log_result(f"\n✅ 已添加BGM到库: {target_path.name}\n")
            self._log_result(f"   保存路径: {target_path}\n")
            self._log_result(f"   BGM库中共有 {bgm_count} 个文件\n\n")
        except Exception as e:
            error_msg = f"添加BGM失败: {str(e)}"
            self._log_result(f"\n❌ {error_msg}\n\n")
            show_error_message(self.winfo_toplevel(), error_msg)
    
    def _add_bgm_folder(self):
        """选择BGM文件夹并添加所有音频文件到库"""
        folder_path = filedialog.askdirectory(
            title="选择包含BGM音频文件的文件夹"
        )
        
        if not folder_path:
            return
        
        try:
            folder = Path(folder_path)
            # 查找所有音频文件
            audio_files = self._find_files_by_extensions(folder, self.AUDIO_EXTENSIONS)
            
            if not audio_files:
                self._log_result(f"\n⚠️  文件夹中未找到音频文件\n\n")
                return
            
            # 获取workspace/bgm文件夹路径
            bgm_dir = get_workspace_path("bgm")
            bgm_dir.mkdir(parents=True, exist_ok=True)
            
            # 处理每个音频文件
            added_count = 0
            for source_file in audio_files:
                if source_file.exists():
                    self._copy_file_with_rename(source_file, bgm_dir)
                    added_count += 1
            
            # 更新任务清单（显示BGM库中的文件数量）
            bgm_count = self._get_bgm_count()
            self._update_checklist('bgm', f"BGM库 ({bgm_count} 个文件)")
            
            # 记录日志
            self._log_result(f"\n✅ 已添加 {added_count} 个BGM文件到库\n")
            self._log_result(f"   来源: {folder_path}\n")
            self._log_result(f"   BGM库中共有 {bgm_count} 个文件\n\n")
        except Exception as e:
            error_msg = f"添加BGM失败: {str(e)}"
            self._log_result(f"\n❌ {error_msg}\n\n")
            show_error_message(self.winfo_toplevel(), error_msg)
    
    def _get_bgm_count(self) -> int:
        """获取BGM库中的文件数量"""
        try:
            bgm_dir = get_workspace_path("bgm")
            if not bgm_dir.exists():
                return 0
            
            audio_files = self._find_files_by_extensions(bgm_dir, self.AUDIO_EXTENSIONS)
            return len(audio_files)
        except:
            return 0
    
    def _get_current_bgm(self) -> Optional[str]:
        """
        从workspace/bgm文件夹中随机选择一个BGM文件
        
        Returns:
            BGM文件路径，如果BGM库为空则返回None
        """
        try:
            bgm_dir = get_workspace_path("bgm")
            if not bgm_dir.exists():
                return None
            
            # 查找所有音频文件
            audio_files = self._find_files_by_extensions(bgm_dir, self.AUDIO_EXTENSIONS)
            
            if audio_files:
                selected = random.choice(audio_files)
                self._log_result(f"   🎲 随机选择BGM: {selected.name}\n")
                return str(selected)
            
            return None
        except Exception as e:
            self._log_result(f"   ⚠️ 获取BGM失败: {str(e)}\n")
            return None
    
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
        if not self.video_paths:
            error_msg = "请先选择视频文件或文件夹"
            self._log_result(f"❌ 错误: {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
            return
        if not self.export_dir_var.get().strip():
            error_msg = "请先选择剪映导出目录"
            self._log_result(f"❌ 错误: {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
            return
        if not self.clone_audio_path:
            error_msg = "请先选择克隆声音文件"
            self._log_result(f"❌ 错误: {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
            return
        
        # 重置进度行标记
        self.progress_line_start = None
        
        # 禁用按钮
        self.process_btn.config(state=tk.DISABLED)
        self.loop_process_btn.config(state=tk.DISABLED)
        
        # 在后台线程执行批量处理
        plot_params = self._collect_plot_params()
        
        def run_batch_pipeline():
            """批量处理所有视频"""
            total = len(self.video_paths)
            results = []
            
            for idx, video_path in enumerate(self.video_paths, 1):
                video_name = Path(video_path).name
                
                # 更新主进度
                self._log_batch_header(idx, total, video_name)
                
                # 处理单个视频（使用闭包捕获 idx）
                def make_callback(current_idx):
                    def single_progress_callback(msg, pct):
                        if pct >= 0:
                            overall = int(((current_idx - 1) / total + pct / 100 / total) * 100)
                            self._update_progress(f"[{current_idx}/{total}] {msg}", overall)
                    return single_progress_callback
                
                # 使用 try-except 包装，确保单个视频失败不会中断整体流程
                try:
                    # 从BGM库中随机选择一个BGM
                    current_bgm = self._get_current_bgm()
                    
                    result = self.pipeline_service.run_full_pipeline(
                        video_path,
                        progress_callback=make_callback(idx),
                        plot_params=plot_params,
                        export_target_dir=self.export_dir_var.get().strip(),
                        reference_audio=self.clone_audio_path,
                        tts_speed=self.speed_var.get(),
                        tts_volume=self.volume_var.get(),
                        bgm_path=current_bgm,
                        bgm_volume=self.bgm_volume_var.get() if current_bgm else None
                    )
                except Exception as e:
                    # 捕获未预期的异常，记录错误并继续
                    result = {
                        'success': False,
                        'error': f"未预期的错误: {str(e)}"
                    }
                
                result['video_name'] = video_name
                result['video_index'] = idx
                results.append(result)
                
                # 如果当前视频处理失败，记录日志并继续下一个
                if not result.get('success'):
                    error_msg = result.get('error', '未知错误')
                    self.result_text.after(0, lambda msg=error_msg, name=video_name: 
                        self._log_result(f"\n❌ [{name}] 处理失败: {msg}\n⏭️ 继续处理下一个视频...\n"))
            
            return {
                'success': all(r.get('success') for r in results),
                'results': results,
                'total': total,
                'success_count': sum(1 for r in results if r.get('success')),
                'message': f"批量处理完成: {sum(1 for r in results if r.get('success'))}/{total} 成功"
            }
        
        ThreadExecutor.execute(run_batch_pipeline, self._on_batch_complete)
    
    def _log_batch_header(self, current: int, total: int, video_name: str):
        """记录批量处理的分隔日志"""
        self.result_text.after(0, lambda: self._log_result(
            f"\n{'='*60}\n"
            f"🎬 [{current}/{total}] 正在处理: {video_name}\n"
            f"{'='*60}\n\n"
        ))
    
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
        """单个视频处理完成"""
        # 重置进度行标记
        self.progress_line_start = None
        
        # 启用按钮
        self.process_btn.config(state=tk.NORMAL)
        self.loop_process_btn.config(state=tk.NORMAL)
        
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
    
    def _on_batch_complete(self, result: dict):
        """批量处理完成"""
        # 重置进度行标记
        self.progress_line_start = None
        
        # 启用按钮
        self.process_btn.config(state=tk.NORMAL)
        self.loop_process_btn.config(state=tk.NORMAL)
        
        results = result.get('results', [])
        total = result.get('total', 0)
        success_count = result.get('success_count', 0)
        failed_results = [r for r in results if not r.get('success')]
        
        self._log_result("\n" + "="*60 + "\n")
        self._log_result("📊 批量处理汇总\n")
        self._log_result("="*60 + "\n\n")
        
        # 输出成功的视频
        self._log_result(f"✅ 成功 ({success_count}/{total}):\n")
        for r in results:
            if r.get('success'):
                video_name = r.get('video_name', '未知')
                idx = r.get('video_index', 0)
                self._log_result(f"  [{idx}] {video_name}\n")
                self._log_result(f"      剪辑视频: {r.get('edited_video', 'N/A')}\n")
                desktop_project = r.get('desktop_project_path')
                if desktop_project:
                    self._log_result(f"      导出目录: {desktop_project}\n")
        
        # 输出失败的视频及详细错误信息
        if failed_results:
            self._log_result(f"\n❌ 失败 ({len(failed_results)}/{total}):\n")
            self._log_result("-" * 50 + "\n")
            for r in failed_results:
                video_name = r.get('video_name', '未知')
                idx = r.get('video_index', 0)
                error_msg = r.get('error', '未知错误')
                self._log_result(f"  [{idx}] {video_name}\n")
                self._log_result(f"      错误详情: {error_msg}\n\n")
            self._log_result("-" * 50 + "\n")
        
        # 最终统计
        self._log_result(f"\n🎉 处理完成: {success_count}/{total} 成功")
        if failed_results:
            self._log_result(f", {len(failed_results)} 失败")
        self._log_result("\n")
        self._log_result("="*60 + "\n")
        
        # 只有全部失败时才记录错误（已在日志中显示，不再弹窗）
        if success_count == 0 and total > 0:
            error_msg = "所有视频处理失败，请查看日志了解详情"
            self._log_result(f"\n❌ {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
    
    def _on_plot_text_modified(self, event):
        """剧情文本修改事件处理"""
        # 重置修改标志（避免重复触发）
        self.plot_text.edit_modified(False)
        
        # 获取文本内容
        plot_content = self.plot_text.get("1.0", tk.END).strip()
        
        # 更新任务清单
        if plot_content:
            # 显示前30个字符作为预览
            preview = plot_content[:30] + "..." if len(plot_content) > 30 else plot_content
            self._update_checklist('plot', preview)
        else:
            self._update_checklist('plot', None)
    
    def _update_checklist(self, key: str, filename: str = None):
        """
        更新任务清单状态
        
        Args:
            key: 任务键名 ('video', 'audio', 'bgm', 'export', 'plot')
            filename: 文件名（如果为None则表示未选择）
        """
        if key not in self.checklist_items:
            return
        
        item = self.checklist_items[key]
        
        if filename:
            # 已选择 - 显示绿色√
            item['status'].config(text="✓", fg="#27AE60")
            item['filename'].config(text=filename)
        else:
            # 未选择 - 根据是否必须显示红色或灰色×
            item['status'].config(
                text="×",
                fg="#E74C3C" if item['required'] else "#999999"
            )
            item['filename'].config(text="")
    
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
            # 更新任务清单
            folder_name = Path(selected).name
            self._update_checklist('export', folder_name)
            self._log_result(f"🗂️ 导出目录已设置为: {selected}\n")
    
    def _start_loop_processing(self):
        """开始循环处理"""
        if not self.video_paths:
            error_msg = "请先选择视频文件或文件夹"
            self._log_result(f"❌ 错误: {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
            return
        if not self.export_dir_var.get().strip():
            error_msg = "请先选择剪映导出目录"
            self._log_result(f"❌ 错误: {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
            return
        if not self.clone_audio_path:
            error_msg = "请先选择克隆声音文件"
            self._log_result(f"❌ 错误: {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
            return
        
        # 获取循环次数
        loop_count = self.loop_count_var.get()
        if loop_count < 2:
            error_msg = "循环次数至少为 2 次"
            self._log_result(f"❌ 错误: {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
            return
        
        # 重置进度行标记
        self.progress_line_start = None
        
        # 禁用按钮
        self.process_btn.config(state=tk.DISABLED)
        self.loop_process_btn.config(state=tk.DISABLED)
        
        # 在后台线程执行循环批量处理
        plot_params = self._collect_plot_params()
        
        def run_loop_batch_pipeline():
            """循环批量处理所有视频"""
            total_videos = len(self.video_paths)
            all_loop_results = []  # 存储所有循环的结果
            
            # 记录循环开始
            self.result_text.after(0, lambda: self._log_result(
                f"\n{'='*60}\n"
                f"🔄 开始循环处理：共 {loop_count} 轮，每轮 {total_videos} 个视频\n"
                f"{'='*60}\n\n"
            ))
            
            # 执行多轮循环
            for loop_idx in range(1, loop_count + 1):
                loop_results = []
                
                # 处理当前轮次的所有视频
                for video_idx, video_path in enumerate(self.video_paths, 1):
                    video_name = Path(video_path).name
                    
                    # 更新主进度（考虑循环）
                    overall_idx = (loop_idx - 1) * total_videos + video_idx
                    overall_total = loop_count * total_videos
                    
                    self.result_text.after(0, lambda lidx=loop_idx, lc=loop_count, vidx=video_idx, vt=total_videos, vn=video_name: 
                        self._log_result(
                            f"\n{'='*60}\n"
                            f"🎬 [轮次 {lidx}/{lc}] [视频 {vidx}/{vt}] 正在处理: {vn}\n"
                            f"{'='*60}\n\n"
                        ))
                    
                    # 处理单个视频（使用闭包捕获 overall_idx 和 overall_total）
                    def make_loop_callback(current_idx, total):
                        def single_progress_callback(msg, pct):
                            if pct >= 0:
                                overall = int(((current_idx - 1) / total + pct / 100 / total) * 100)
                                self._update_progress(
                                    f"[{current_idx}/{total}] {msg}", 
                                    overall
                                )
                        return single_progress_callback
                    
                    # 使用 try-except 包装，确保单个视频失败不会中断整体流程
                    try:
                        # 从BGM库中随机选择一个BGM
                        current_bgm = self._get_current_bgm()
                        
                        result = self.pipeline_service.run_full_pipeline(
                            video_path,
                            progress_callback=make_loop_callback(overall_idx, overall_total),
                            plot_params=plot_params,
                            export_target_dir=self.export_dir_var.get().strip(),
                            reference_audio=self.clone_audio_path,
                            tts_speed=self.speed_var.get(),
                            tts_volume=self.volume_var.get(),
                            bgm_path=current_bgm,
                            bgm_volume=self.bgm_volume_var.get() if current_bgm else None
                        )
                    except Exception as e:
                        # 捕获未预期的异常，记录错误并继续
                        result = {
                            'success': False,
                            'error': f"未预期的错误: {str(e)}"
                        }
                    
                    result['video_name'] = video_name
                    result['video_index'] = video_idx
                    result['loop_index'] = loop_idx
                    loop_results.append(result)
                    
                    # 如果当前视频处理失败，记录日志并继续下一个
                    if not result.get('success'):
                        error_msg = result.get('error', '未知错误')
                        self.result_text.after(0, lambda msg=error_msg, name=video_name, lidx=loop_idx: 
                            self._log_result(f"\n❌ [轮次 {lidx}] [{name}] 处理失败: {msg}\n⏭️ 继续处理下一个视频...\n"))
                
                all_loop_results.extend(loop_results)
                
                # 轮次完成提示
                loop_success = sum(1 for r in loop_results if r.get('success'))
                self.result_text.after(0, lambda lidx=loop_idx, ls=loop_success, vt=total_videos: 
                    self._log_result(
                        f"\n✅ 第 {lidx} 轮循环完成: {ls}/{vt} 成功\n"
                    ))
            
            # 所有循环完成
            return {
                'success': all(r.get('success') for r in all_loop_results),
                'results': all_loop_results,
                'loop_count': loop_count,
                'total_videos': total_videos,
                'total_processed': len(all_loop_results),
                'success_count': sum(1 for r in all_loop_results if r.get('success')),
                'message': f"循环处理完成: {loop_count} 轮 × {total_videos} 视频 = {len(all_loop_results)} 次处理，{sum(1 for r in all_loop_results if r.get('success'))} 次成功"
            }
        
        ThreadExecutor.execute(run_loop_batch_pipeline, self._on_loop_complete)
    
    def _on_loop_complete(self, result: dict):
        """循环处理完成"""
        # 重置进度行标记
        self.progress_line_start = None
        
        # 启用按钮
        self.process_btn.config(state=tk.NORMAL)
        self.loop_process_btn.config(state=tk.NORMAL)
        
        results = result.get('results', [])
        loop_count = result.get('loop_count', 0)
        total_videos = result.get('total_videos', 0)
        total_processed = result.get('total_processed', 0)
        success_count = result.get('success_count', 0)
        failed_results = [r for r in results if not r.get('success')]
        
        self._log_result("\n" + "="*60 + "\n")
        self._log_result("📊 循环处理汇总\n")
        self._log_result("="*60 + "\n\n")
        
        # 统计信息
        self._log_result(f"🔄 循环轮次: {loop_count}\n")
        self._log_result(f"📹 视频数量: {total_videos}\n")
        self._log_result(f"📝 总处理次数: {total_processed}\n")
        self._log_result(f"✅ 成功次数: {success_count}\n")
        self._log_result(f"❌ 失败次数: {len(failed_results)}\n")
        self._log_result(f"📈 成功率: {success_count/total_processed*100:.1f}%\n\n")
        
        # 按轮次输出结果
        for loop_idx in range(1, loop_count + 1):
            loop_results = [r for r in results if r.get('loop_index') == loop_idx]
            loop_success = sum(1 for r in loop_results if r.get('success'))
            
            self._log_result(f"🔁 第 {loop_idx} 轮: {loop_success}/{len(loop_results)} 成功\n")
            
            for r in loop_results:
                video_name = r.get('video_name', '未知')
                status_icon = "✅" if r.get('success') else "❌"
                self._log_result(f"  {status_icon} {video_name}")
                if not r.get('success'):
                    error_msg = r.get('error', '未知错误')
                    self._log_result(f" - {error_msg}")
                self._log_result("\n")
            self._log_result("\n")
        
        # 输出详细失败信息
        if failed_results:
            self._log_result(f"❌ 失败详情:\n")
            self._log_result("-" * 50 + "\n")
            for r in failed_results:
                video_name = r.get('video_name', '未知')
                loop_idx = r.get('loop_index', 0)
                video_idx = r.get('video_index', 0)
                error_msg = r.get('error', '未知错误')
                self._log_result(f"  [轮次 {loop_idx}] [视频 {video_idx}] {video_name}\n")
                self._log_result(f"      错误: {error_msg}\n\n")
            self._log_result("-" * 50 + "\n\n")
        
        # 最终统计
        self._log_result(f"🎉 循环处理完成!\n")
        self._log_result(f"   {loop_count} 轮 × {total_videos} 视频 = {total_processed} 次处理\n")
        self._log_result(f"   成功 {success_count} 次，失败 {len(failed_results)} 次\n")
        self._log_result("="*60 + "\n")
        
        # 只有全部失败时才记录错误（已在日志中显示，不再弹窗）
        if success_count == 0 and total_processed > 0:
            error_msg = "所有循环处理均失败，请查看日志了解详情"
            self._log_result(f"\n❌ {error_msg}\n")
            show_error_message(self.winfo_toplevel(), error_msg)
