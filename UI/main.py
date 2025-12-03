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

# 添加项目根目录到路径（支持打包环境）
def _get_base_path() -> Path:
    """获取程序基础路径"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent

project_root = _get_base_path()
sys.path.insert(0, str(project_root))

# 初始化日志系统（只打印一次）
from utils.loggers import get_app_logger
get_app_logger()

from UI.components.editing_panel import EditingPanel
from UI.components.full_pipeline_panel import FullPipelinePanel
from UI.components.multi_commentary_panel import MultiCommentaryPanel


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
        # 设置图标（使用动态路径）
        icon_path = project_root / "resources" / "ui" / "icon.ico"
        if icon_path.exists():
            self.root.iconbitmap(str(icon_path))
        
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
        
        # 功能 1：完整处理流程
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
    app = VideoProcessingApp()
    app.run()


if __name__ == "__main__":
    main()
