"""
UI 辅助函数和工具类
"""

import tkinter as tk
from tkinter import ttk
import threading
from typing import Callable, Any


class ThreadExecutor:
    """线程执行器，用于在后台执行耗时任务"""
    
    @staticmethod
    def execute(func: Callable, on_complete: Callable[[Any], None] = None):
        """
        在新线程中执行函数
        
        Args:
            func: 要执行的函数
            on_complete: 完成后的回调函数
        """
        def run():
            try:
                result = func()
                if on_complete:
                    on_complete(result)
            except Exception as e:
                if on_complete:
                    on_complete({"success": False, "error": str(e)})
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()


class ProgressDialog:
    """进度对话框"""
    
    def __init__(self, parent, title="处理中..."):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x150")
        self.dialog.resizable(False, False)
        
        # 居中显示
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 进度标签
        self.label = ttk.Label(self.dialog, text="准备开始...", font=("微软雅黑", 10))
        self.label.pack(pady=20)
        
        # 进度条
        self.progress = ttk.Progressbar(
            self.dialog, 
            mode='determinate',
            length=400
        )
        self.progress.pack(pady=10)
        
        # 百分比标签
        self.percent_label = ttk.Label(self.dialog, text="0%", font=("微软雅黑", 9))
        self.percent_label.pack(pady=5)
        
        # 取消按钮（可选）
        self.cancel_button = ttk.Button(
            self.dialog,
            text="后台运行",
            command=self.close
        )
        self.cancel_button.pack(pady=10)
    
    def update_progress(self, message: str, percent: int):
        """
        更新进度
        
        Args:
            message: 进度消息
            percent: 进度百分比（0-100）
        """
        self.label.config(text=message)
        self.progress['value'] = percent
        self.percent_label.config(text=f"{percent}%")
        
        if percent >= 100:
            self.close()
        elif percent < 0:  # 错误情况
            self.label.config(text=message)
            self.cancel_button.config(text="关闭")
    
    def close(self):
        """关闭对话框"""
        self.dialog.destroy()


def show_success_message(parent, message: str):
    """
    显示成功消息
    
    Args:
        parent: 父窗口
        message: 消息内容
    """
    dialog = tk.Toplevel(parent)
    dialog.title("成功")
    dialog.geometry("400x150")
    dialog.resizable(False, False)
    
    # 居中显示
    dialog.transient(parent)
    dialog.grab_set()
    
    # 成功图标和消息
    frame = ttk.Frame(dialog)
    frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
    
    icon_label = ttk.Label(frame, text="✅", font=("微软雅黑", 30))
    icon_label.pack(pady=10)
    
    msg_label = ttk.Label(frame, text=message, font=("微软雅黑", 11), wraplength=350)
    msg_label.pack(pady=10)
    
    # 确定按钮
    ok_button = ttk.Button(dialog, text="确定", command=dialog.destroy)
    ok_button.pack(pady=10)


def show_error_message(parent, message: str):
    """
    显示错误消息（仅记录日志，不弹窗）
    
    Args:
        parent: 父窗口（保留参数以兼容现有调用）
        message: 错误消息
    """
    # 只记录日志，不弹窗
    from utils.loggers import get_app_logger
    logger = get_app_logger()
    logger.error(f"错误: {message}")


def create_labeled_entry(parent, label_text: str, row: int, default_text: str = "") -> ttk.Entry:
    """
    创建带标签的输入框
    
    Args:
        parent: 父容器
        label_text: 标签文本
        row: 行号
        default_text: 默认文本
    
    Returns:
        Entry 控件
    """
    label = ttk.Label(parent, text=label_text, font=("微软雅黑", 10))
    label.grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
    
    entry = ttk.Entry(parent, width=50, font=("微软雅黑", 9))
    entry.grid(row=row, column=1, padx=10, pady=5)
    
    if default_text:
        entry.insert(0, default_text)
    
    return entry


def create_labeled_spinbox(parent, label_text: str, row: int, from_: int, to: int, default: int) -> ttk.Spinbox:
    """
    创建带标签的数字选择框
    
    Args:
        parent: 父容器
        label_text: 标签文本
        row: 行号
        from_: 最小值
        to: 最大值
        default: 默认值
    
    Returns:
        Spinbox 控件
    """
    label = ttk.Label(parent, text=label_text, font=("微软雅黑", 10))
    label.grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
    
    spinbox = ttk.Spinbox(parent, from_=from_, to=to, width=10, font=("微软雅黑", 9))
    spinbox.set(default)
    spinbox.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
    
    return spinbox

