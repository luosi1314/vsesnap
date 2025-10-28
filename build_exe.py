#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VSE Screenshot 打包脚本
使用 PyInstaller 打包成 exe
"""

import os
import sys
import shutil
import subprocess

def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        import PyInstaller
        print("✓ PyInstaller 已安装")
        return True
    except ImportError:
        print("✗ PyInstaller 未安装")
        print("正在安装 PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller 安装成功")
            return True
        except Exception as e:
            print(f"✗ PyInstaller 安装失败: {e}")
            return False

def clean_build():
    """清理之前的构建文件"""
    print("\n清理之前的构建文件...")
    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['vse_screenshot.spec']
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"✓ 已删除: {dir_name}")
            except Exception as e:
                print(f"✗ 删除失败 {dir_name}: {e}")
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
                print(f"✓ 已删除: {file_name}")
            except Exception as e:
                print(f"✗ 删除失败 {file_name}: {e}")

def find_vapoursynth_path():
    """查找 VapourSynth 安装路径"""
    import winreg

    try:
        # 尝试从注册表读取
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\VapourSynth", 0,
                             winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        path, _ = winreg.QueryValueEx(key, "Path")
        winreg.CloseKey(key)
        print(f"✓ 找到 VapourSynth: {path}")
        return path
    except:
        pass

    # 尝试常见路径
    common_paths = [
        r"E:\MyProjects\vapoursynth\vs\VapourSynth",
        r"C:\Program Files (x86)\VapourSynth",
    ]

    for path in common_paths:
        if os.path.exists(path):
            print(f"✓ 找到 VapourSynth: {path}")
            return path

    print("✗ 未找到 VapourSynth 安装路径")
    return None

def build_exe():
    """构建 exe"""
    print("\n开始构建 exe...")

    # 查找 VapourSynth 路径
    vs_path = find_vapoursynth_path()

    # PyInstaller 命令
    cmd = [
        'pyinstaller',
        '--name=VSE_Screenshot',
        '--onedir',  # 打包成文件夹（包含依赖）
        '--windowed',  # 不显示控制台窗口
        '--icon=NONE',  # 如果有图标文件，可以指定
        '--hidden-import=customtkinter',
        '--hidden-import=PIL',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=vapoursynth',
        '--hidden-import=numpy',
        '--hidden-import=yaml',
        '--collect-all=customtkinter',
        '--collect-all=PIL',
        '--collect-submodules=numpy',
        '--noconfirm',  # 不询问，直接覆盖
    ]

    # 如果找到 VapourSynth，添加其 DLL 和插件
    if vs_path:
        # 添加 VapourSynth 核心 DLL
        vs_core_dll = os.path.join(vs_path, 'vapoursynth64', 'vapoursynth.dll')
        if os.path.exists(vs_core_dll):
            cmd.append(f'--add-binary={vs_core_dll};.')

        # 添加 VapourSynth Python 模块
        vs_python = os.path.join(vs_path, 'vapoursynth64', 'vapoursynth.pyd')
        if os.path.exists(vs_python):
            cmd.append(f'--add-binary={vs_python};.')

        # 添加插件目录
        vs_plugins = os.path.join(vs_path, 'vapoursynth64', 'plugins')
        if os.path.exists(vs_plugins):
            cmd.append(f'--add-data={vs_plugins};vapoursynth64/plugins')

    cmd.append('vse_screenshot_gui.py')

    try:
        print(f"执行命令: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        print("\n✓ 构建成功！")
        return True
    except Exception as e:
        print(f"\n✗ 构建失败: {e}")
        return False

def create_release_package():
    """创建发布包"""
    print("\n创建发布包...")

    release_dir = "VSE_Screenshot_Release"

    # 创建发布目录
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)

    # 复制整个 dist 文件夹（包含所有依赖）
    dist_dir = os.path.join('dist', 'VSE_Screenshot')
    if os.path.exists(dist_dir):
        # 复制整个文件夹
        shutil.copytree(dist_dir, os.path.join(release_dir, 'VSE_Screenshot'))
        print(f"✓ 已复制程序文件夹")
    else:
        print(f"✗ 找不到程序文件夹: {dist_dir}")
        return False
    
    # 复制必要文件
    files_to_copy = [
        'README.md',
        '使用指南.md',
        'requirements.txt',
        'install_dependencies.bat',
        'cleanup_cache.bat'
    ]
    
    for file_name in files_to_copy:
        if os.path.exists(file_name):
            shutil.copy(file_name, release_dir)
            print(f"✓ 已复制: {file_name}")
    
    # 创建启动脚本
    startup_bat = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
cd VSE_Screenshot
start VSE_Screenshot.exe
"""

    with open(os.path.join(release_dir, '启动程序.bat'), 'w', encoding='utf-8') as f:
        f.write(startup_bat)
    print("✓ 已创建: 启动程序.bat")

    # 创建启动说明
    startup_guide = """# VSE Screenshot 使用说明

## 快速启动

双击 `启动程序.bat` 即可运行程序。

## 程序特点

✓ 无需安装 Python
✓ 无需安装 VapourSynth（已内置）
✓ 无需联网安装依赖
✓ 开箱即用

## 功能说明

1. **项目管理**: 创建和管理多个视频对比项目
2. **视频添加**: 支持多种视频格式（MP4, MKV, AVI等）
3. **自动检测**: 自动检测视频扫描模式（逐行/隔行）
4. **帧率转换**: 支持PAL/NTSC等多种帧率格式
5. **批量截图**: 支持随机截图和指定帧号截图
6. **容错截图**: PAL转NTSC格式支持容错帧截图
7. **历史帧数**: 自动记录和重用历史截图帧数

## 使用流程

1. 启动程序
2. 创建或选择项目
3. 添加视频文件
4. 设置对齐帧数和偏移量
5. 开始截图

## 注意事项

- 首次运行可能需要较长时间加载
- 截图保存在项目的 screenshots 文件夹中
- 建议使用SSD存储视频文件以提高性能

## 更多帮助

查看 `使用指南.md` 获取详细使用说明。
"""

    with open(os.path.join(release_dir, '使用说明.txt'), 'w', encoding='utf-8') as f:
        f.write(startup_guide)
    print("✓ 已创建: 使用说明.txt")
    
    print(f"\n✓ 发布包已创建: {release_dir}")
    print(f"  包含文件:")
    for item in os.listdir(release_dir):
        print(f"    - {item}")
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("VSE Screenshot 打包工具")
    print("=" * 60)
    
    # 检查 PyInstaller
    if not check_pyinstaller():
        print("\n请先安装 PyInstaller:")
        print("  pip install pyinstaller")
        return
    
    # 清理构建文件
    clean_build()
    
    # 构建 exe
    if not build_exe():
        print("\n构建失败，请检查错误信息")
        return
    
    # 创建发布包
    if not create_release_package():
        print("\n创建发布包失败")
        return
    
    print("\n" + "=" * 60)
    print("✓ 打包完成！")
    print("=" * 60)
    print("\n发布包位置: VSE_Screenshot_Release/")
    print("启动方式: 双击 VSE_Screenshot_Release/启动程序.bat")
    print("\n特点:")
    print("  ✓ 无需安装 Python")
    print("  ✓ 无需安装 VapourSynth")
    print("  ✓ 无需联网安装依赖")
    print("  ✓ 开箱即用")

if __name__ == '__main__':
    main()

