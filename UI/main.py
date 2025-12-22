"""
视频处理 GUI 主界面
提供三个功能：
1. AI 智能剪辑（步骤 1-6）
2. 完整处理流程（步骤 1-10）
3. 批量生成 AI 解说（步骤 7-10 循环）
"""

import tkinter as tk
from tkinter import ttk
import sys
from pathlib import Path

# 设置 DPI 感知（Windows 高 DPI 支持）
if sys.platform == 'win32':
    try:
        # Windows 10/11 高 DPI 支持
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_PER_MONITOR_DPI_AWARE
    except:
        pass

# 添加项目根目录到路径（支持打包环境）
def _get_base_path() -> Path:
    """获取程序基础路径（打包内部资源）"""
    if getattr(sys, 'frozen', False):
        # 打包后的 exe 环境
        # PyInstaller: 使用 sys._MEIPASS
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        # Nuitka: 使用当前模块所在目录（指向临时解压目录）
        return Path(__file__).resolve().parent.parent
    else:
        return Path(__file__).resolve().parent.parent

project_root = _get_base_path()
sys.path.insert(0, str(project_root))

# 初始化日志系统（只打印一次）
try:
    from utils.loggers import get_app_logger
    logger = get_app_logger()
except Exception as e:
    # 如果日志系统初始化失败，使用基础日志
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('main')
    logger.error(f"日志系统初始化失败: {e}")

try:
    from UI.components.editing_panel import EditingPanel
    from UI.components.full_pipeline_panel import FullPipelinePanel
    from UI.components.multi_commentary_panel import MultiCommentaryPanel
except Exception as e:
    logger.error(f"导入 UI 组件失败: {e}", exc_info=True)
    raise


class VideoProcessingApp:
    """视频处理应用主窗口"""
    
    # 现代化配色方案
    COLORS = {
        'bg': '#F5F1EB',            # 柔和米色主背景
        'fg': '#3A3A38',            # 深灰文字
        'accent': '#7FA1A6',        # 低饱和度蓝绿
        'accent_hover': '#6B8B90',  # 悬停色
        'panel_bg': '#FFFFFF',      # 面板背景
        'input_bg': '#F0EAE2',      # 输入框背景
        'border': '#D8D2C8',        # 边框颜色
        'success': '#6BA292',       # 成功色
        'error': '#D97C6B',         # 错误色
        'text_gray': '#8B8378'      # 灰色文本
    }
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI 视频剪辑工具")
        
        # 先隐藏窗口，避免闪烁
        self.root.withdraw()
        
        self.root.geometry("1000x750")
        # 设置图标（resources 已打包进 exe）
        from utils.config_loader import get_resources_path
        from PIL import Image
        resources_path = get_resources_path()
        icon_path = resources_path / "ui" / "icon.png"
        img = Image.open(icon_path)
        img.save(icon_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception as e:
                # 图标加载失败不影响程序运行，只记录错误
                logger.warning(f"⚠️ 图标加载失败: {e}")
                logger.warning(f"   图标路径: {icon_path}")
        else:
            logger.warning(f"⚠️ 图标文件不存在: {icon_path}")
            logger.warning(f"   resources 路径: {resources_path}")
            if resources_path.exists():
                try:
                    if resources_path.is_dir():
                        contents = list(resources_path.iterdir())
                        logger.info(f"   resources 目录内容: {[str(c.name) for c in contents]}")
                except Exception as e:
                    logger.warning(f"   无法列出 resources 目录内容: {e}")
            else:
                logger.warning(f"   resources 目录不存在，可能打包时未包含 resources")
        
        # 设置最小窗口大小（两列布局）
        self.root.minsize(1100, 650)
        
        # 设置背景色
        self.root.config(bg=self.COLORS['bg'])
        
        # 设置主题样式
        self._setup_style()
        
        # 创建界面
        self._create_widgets()
        
        # 居中显示窗口
        self._center_window()
        
        # 显示窗口
        self.root.deiconify()
        
        # 检查 ffmpeg 文件（在界面创建后检查，以便在日志框显示提示）
        self.root.after(200, self._check_ffmpeg_files)
        
        # 强制更新窗口，确保渲染完成（解决打包后显示问题）
        self.root.update_idletasks()
        self.root.update()
        
        # 触发一次重绘（解决打包后初始显示问题）
        self.root.after(100, lambda: self.root.update_idletasks())
    
    def _setup_style(self):
        """设置现代化主题样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置总体颜色
        style.configure('.', 
            background=self.COLORS['bg'],
            foreground=self.COLORS['fg'],
            fieldbackground=self.COLORS['input_bg'],
            bordercolor=self.COLORS['border'],
            darkcolor=self.COLORS['bg'],
            lightcolor=self.COLORS['panel_bg']
        )
        
        # 配置 Notebook（选项卡）
        style.configure('TNotebook',
            background=self.COLORS['bg'],
            borderwidth=0
        )
        
        style.configure('TNotebook.Tab',
            background=self.COLORS['panel_bg'],
            foreground=self.COLORS['fg'],
            padding=[20, 12],
            borderwidth=0,
            font=('微软雅黑', 10)
        )
        
        style.map('TNotebook.Tab',
            background=[('selected', self.COLORS['bg'])],
            foreground=[('selected', self.COLORS['accent'])],
            expand=[('selected', [1, 1, 1, 0])]
        )
        
        # 配置按钮
        style.configure('Accent.TButton',
            background=self.COLORS['accent'],
            foreground='white',
            borderwidth=0,
            focuscolor='none',
            padding=[20, 10],
            font=('微软雅黑', 10, 'bold')
        )
        
        style.map('Accent.TButton',
            background=[('active', self.COLORS['accent_hover']),
                       ('disabled', self.COLORS['border'])]
        )
        
        # 配置普通按钮
        style.configure('TButton',
            background=self.COLORS['panel_bg'],
            foreground=self.COLORS['fg'],
            borderwidth=1,
            relief='flat',
            focuscolor='none',
            padding=[15, 8],
            font=('微软雅黑', 9)
        )
        
        style.map('TButton',
            background=[('active', self.COLORS['input_bg'])],
            bordercolor=[('focus', self.COLORS['accent'])]
        )
        
        # 配置标签框
        style.configure('TLabelframe',
            background=self.COLORS['panel_bg'],
            bordercolor=self.COLORS['border'],
            borderwidth=1,
            relief='solid'
        )
        
        style.configure('TLabelframe.Label',
            background=self.COLORS['panel_bg'],
            foreground=self.COLORS['fg'],
            font=('微软雅黑', 10, 'bold')
        )
        
        # 配置 Frame
        style.configure('TFrame',
            background=self.COLORS['bg']
        )
        
        style.configure('Panel.TFrame',
            background=self.COLORS['panel_bg']
        )
        
        # 配置 Label
        style.configure('TLabel',
            background=self.COLORS['bg'],
            foreground=self.COLORS['fg'],
            font=('微软雅黑', 9)
        )
        
        style.configure('Title.TLabel',
            font=('微软雅黑', 16, 'bold'),
            foreground=self.COLORS['fg']
        )
        
        style.configure('Subtitle.TLabel',
            font=('微软雅黑', 10),
            foreground=self.COLORS['text_gray']
        )
        
        # 配置输入框
        style.configure('TEntry',
            fieldbackground=self.COLORS['input_bg'],
            foreground=self.COLORS['fg'],
            bordercolor=self.COLORS['border'],
            insertcolor=self.COLORS['fg']
        )
        
        # 配置 Spinbox
        style.configure('TSpinbox',
            fieldbackground=self.COLORS['input_bg'],
            foreground=self.COLORS['fg'],
            bordercolor=self.COLORS['border'],
            arrowcolor=self.COLORS['fg']
        )
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 顶部标题栏
        header = ttk.Frame(main_container, style='Panel.TFrame', height=100)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # 标题区域
        title_frame = ttk.Frame(header, style='Panel.TFrame')
        title_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # 图标 + 标题
        icon_title_frame = ttk.Frame(title_frame, style='Panel.TFrame')
        icon_title_frame.pack()
        
        icon_label = ttk.Label(
            icon_title_frame,
            text="🎬",
            font=('Segoe UI Emoji', 24),
            background=self.COLORS['panel_bg']
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        main_title = ttk.Label(
            icon_title_frame,
            text="AI 视频处理工具",
            style='Title.TLabel',
            background=self.COLORS['panel_bg']
        )
        main_title.pack(side=tk.LEFT)
        
        # 副标题
        subtitle = ttk.Label(
            title_frame,
            text="智能剪辑 · 自动解说 · 一键生成草稿",
            style='Subtitle.TLabel',
            background=self.COLORS['panel_bg']
        )
        subtitle.pack(pady=(5, 0))
        
        # 内容区域
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 创建选项卡
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))
        
        # 功能 1：完整处理流程（先创建，用于显示 ffmpeg 检查提示）
        self.full_pipeline_panel = FullPipelinePanel(self.notebook)
        self.notebook.add(self.full_pipeline_panel, text="  🎯 完整处理流程  ")
        
        # 功能 2：AI 智能剪辑
        self.editing_panel = EditingPanel(self.notebook)
        self.notebook.add(self.editing_panel, text="  ✂️ AI 智能剪辑  ")
        
        # 功能 3：批量生成解说
        self.multi_commentary_panel = MultiCommentaryPanel(self.notebook)
        self.notebook.add(self.multi_commentary_panel, text="  🔄 批量生成解说  ")
        
        # 底部状态栏
        footer = ttk.Frame(main_container, style='Panel.TFrame', height=40)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        
        info_label = ttk.Label(
            footer,
            text="💡 提示：选择对应的功能选项卡，上传视频后点击开始处理",
            font=('微软雅黑', 9),
            foreground=self.COLORS['text_gray'],
            background=self.COLORS['panel_bg']
        )
        info_label.pack(pady=10)
    
    def _check_ffmpeg_files(self):
        """检查 workspace/ffmpeg 目录下的 ffmpeg 文件"""
        try:
            from utils.config_loader import get_config
            config = get_config()
            workspace_path = config.get_workspace_path()
            ffmpeg_dir = workspace_path / "ffmpeg"
            
            # 需要检查的三个文件
            required_files = ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]
            missing_files = []
            
            for filename in required_files:
                file_path = ffmpeg_dir / filename
                if not file_path.exists():
                    missing_files.append(filename)
            
            # 如果有缺失的文件，在日志框显示提示
            if missing_files and hasattr(self, 'full_pipeline_panel'):
                try:
                    log_msg = f"\n⚠️ FFmpeg 文件缺失提示\n"
                    log_msg += f"{'='*60}\n"
                    log_msg += f"检测到 workspace/ffmpeg 目录下缺少以下文件：\n"
                    for filename in missing_files:
                        log_msg += f"  - {filename}\n"
                    log_msg += f"\n请将以下文件添加到：{ffmpeg_dir}\n"
                    log_msg += f"  1. ffmpeg.exe\n"
                    log_msg += f"  2. ffprobe.exe\n"
                    log_msg += f"  3. ffplay.exe\n"
                    log_msg += f"\n添加后请重启应用程序。\n"
                    log_msg += f"{'='*60}\n\n"
                    self.full_pipeline_panel._log_result(log_msg)
                except Exception as e:
                    logger.warning(f"无法在日志框显示 ffmpeg 提示: {e}")
            
            # 记录到日志系统
            if missing_files:
                logger.warning(f"FFmpeg 文件缺失: {missing_files}")
                logger.warning(f"请将文件添加到: {ffmpeg_dir}")
            else:
                logger.info(f"✓ FFmpeg 文件检查通过: {ffmpeg_dir}")
        except Exception as e:
            logger.error(f"检查 FFmpeg 文件时出错: {e}", exc_info=True)
    
    def _center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        
        # 获取窗口尺寸
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 设置窗口位置
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """主函数"""
    try:
        app = VideoProcessingApp()
        app.run()
    except Exception as e:
        # 捕获所有异常，避免闪退
        import traceback
        error_msg = f"程序启动失败: {e}\n\n{traceback.format_exc()}"
        print(error_msg)
        # 尝试写入日志文件
        try:
            from utils.loggers import get_app_logger
            logger = get_app_logger()
            logger.critical(error_msg)
        except:
            pass
        # 如果有窗口，显示错误对话框
        try:
            import tkinter.messagebox as messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("程序启动失败", f"程序启动时发生错误：\n\n{str(e)}\n\n详细信息请查看日志文件。")
        except:
            pass
        raise


if __name__ == "__main__":
    main()
