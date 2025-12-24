"""
使用 Nuitka 打包 - 避免 PyInstaller 的权限问题
Nuitka 编译为原生代码，不依赖文件复制，可以避免权限问题
"""

import subprocess
import sys
import os
import shutil
import time
from pathlib import Path
import multiprocessing


def main():
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # 检查 Nuitka
    try:
        import nuitka
    except ImportError:
        print("正在安装 Nuitka...")
        subprocess.run([sys.executable, "-m", "pip", "install", "nuitka"], check=True)
    
    # 清理 - 直接覆盖
    dist_dir = project_root / "dist"

    if dist_dir.exists():
        try:
            shutil.rmtree(dist_dir, ignore_errors=True)
            print(f"✓ 已清理旧 dist 目录")
        except Exception as e:
            print(f"⚠ 清理 dist 目录时遇到问题: {e}")
    
    main_file = project_root / "UI" / "main.py"
    if not main_file.exists():
        print(f"✗ 找不到主文件: {main_file}")
        return 1
    
    # Nuitka 命令
    icon_path = project_root / "resources" / "ui" / "icon.png"
    
    # 获取 CPU 核心数，用于多线程编译
    cpu_count = multiprocessing.cpu_count()
    jobs = min(cpu_count, 8)  # 最多使用 8 个线程，避免过度占用资源
    print(f"✓ 使用 {jobs} 个线程进行编译（CPU 核心数: {cpu_count}）")
    
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",  # 独立模式
        "--onefile",     # 单文件模式
        "--windows-disable-console",  # 无控制台窗口
        "--enable-plugin=tk-inter",   # 启用 tkinter 插件
        "--enable-plugin=numpy",      # 启用 numpy 插件
        f"--jobs={jobs}",  # 多线程编译
        "--include-data-dir=" + str(project_root / "configs") + "=configs",
        "--include-data-dir=" + str(project_root / "resources") + "=resources",
        "--output-dir=" + str(dist_dir),
        "--output-filename=AI剪辑工具.exe",
        # 添加版本信息，有助于减少杀毒软件误报
        "--windows-company-name=AI视频处理工具",
        "--windows-product-name=AI剪辑工具",
        "--windows-file-version=1.0.0.0",
        "--windows-product-version=1.0.0.0",
        "--windows-file-description=AI智能视频剪辑工具",
    ]
    
    if icon_path.exists():
        cmd.append(f"--windows-icon-from-ico={icon_path}")
    
    # 添加主文件
    cmd.append(str(main_file))
    
    print("\n开始编译（这可能需要较长时间，请耐心等待）...")
    
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode == 0:
        output_exe = dist_dir / "AI剪辑工具.exe"
        if output_exe.exists():
            size_mb = output_exe.stat().st_size / (1024 * 1024)
            
            print("\n" + "=" * 60)
            print("✓ 打包成功！")
            print("=" * 60)
            print(f"\n输出: {output_exe}")
            print(f"大小: {size_mb:.1f} MB")
            
            # 复制到桌面
            try:
                desktop_path = Path.home() / "Desktop"
                if not desktop_path.exists():
                    # 尝试中文路径
                    desktop_path = Path.home() / "桌面"
                
                if desktop_path.exists():
                    target_dir = desktop_path / "ai_editing_tool"
                    target_dir.mkdir(exist_ok=True)
                    
                    # 复制 exe（resources 已打包进 exe，不需要单独复制）
                    target_exe = target_dir / "AI剪辑工具.exe"
                    shutil.copy2(output_exe, target_exe)
                    print(f"\n✓ 已复制 exe 到: {target_exe}")

                else:
                    print(f"⚠ 未找到桌面目录，跳过复制")
            except Exception as e:
                print(f"⚠ 复制到桌面时出错: {e}")
                print("  可以手动复制文件")
            
            return 0
        else:
            print(f"✗ 找不到输出文件: {output_exe}")
            return 1
    else:
        print("\n✗ 打包失败！")
        print("\n如果遇到问题，可以尝试：")
        print("  1. 更新 Nuitka: pip install --upgrade nuitka")
        print("  2. 检查是否有足够的磁盘空间")
        print("  3. 查看上面的错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())

