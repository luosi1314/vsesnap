#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VSE Screenshot GUI - 多视频版本帧数对齐 + 预览 + 截图工具
基于 CustomTkinter 的现代化桌面应用
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import List, Dict, Optional

import customtkinter as ctk
from PIL import Image, ImageTk

# 导入项目模块
from project_manager import ProjectManager
from video_utils import detect_scan_type, get_video_info

# 设置 CustomTkinter 主题
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class VideoEntry:
    """视频条目数据类"""
    def __init__(self, filepath: str, name: str = "", offset: int = 0,
                 fps_type: str = "原生PAL (25fps)", use_qtgmc: bool = False,
                 qtgmc_tff: bool = True, tolerance: int = 0,
                 fps_display: str = "未知", screenshot_fps: str = "25.00",
                 alignment_mode: str = "不对齐",
                 video_fps: str = "25.00", scan_type: str = "逐行"):
        self.filepath = filepath
        self.name = name or os.path.basename(filepath)
        self.offset = offset
        self.fps_type = fps_type  # 保留用于兼容性
        self.use_qtgmc = use_qtgmc
        self.qtgmc_tff = qtgmc_tff  # True=TFF(Top Field First), False=BFF(Bottom Field First)
        self.tolerance = tolerance  # 容错帧数（前后各N帧）
        self.fps_display = fps_display  # 视频实际帧率显示（如 25p, 25i, 29.97i）- 保留用于兼容性
        self.screenshot_fps = screenshot_fps  # 截图帧率设置（纯数字，如 "25.00", "29.97"）
        self.alignment_mode = alignment_mode  # 帧率对齐方式
        self.video_fps = video_fps  # 视频实际帧率（纯数字，如 "60.00"）
        self.scan_type = scan_type  # 扫描方式（"逐行", "隔行 TFF", "隔行 BFF"）


class VSEScreenshotApp(ctk.CTk):
    """主应用程序类"""

    # 帧率类型选项（保留用于兼容性）
    FPS_TYPES = [
        "原生PAL (25fps)",
        "原生NTSC (29.97fps)",
        "PAL插帧到NTSC",
        "NTSC减帧到PAL",
        "PAL 5重1",
        "PAL 6重2"
    ]

    # 截图帧率选项（纯数字格式）
    SCREENSHOT_FPS_OPTIONS = [
        "23.976",
        "24.00",
        "25.00",
        "29.97",
        "30.00",
        "50.00",
        "59.94",
        "60.00"
    ]

    # 视频帧率选项（支持到120fps，可自定义）
    VIDEO_FPS_OPTIONS = [
        "23.976",
        "24.00",
        "25.00",
        "29.97",
        "30.00",
        "50.00",
        "59.94",
        "60.00",
        "100.00",
        "119.88",
        "120.00",
        "自定义..."
    ]

    # 扫描方式选项
    SCAN_TYPE_OPTIONS = [
        "逐行",
        "隔行 TFF",
        "隔行 BFF"
    ]

    # 帧率对齐方式选项
    ALIGNMENT_MODES = [
        "不对齐",           # 不进行帧率对齐
        "减帧对齐",         # 使用 VDecimate 去除重复帧
        "重复帧对齐",       # 重复帧以匹配目标帧率
        "反胶卷过带",       # 使用 VIVTC 反胶卷过带（3:2 pulldown）
        "速度调整",         # 使用 AssumeFPS 调整速度
        "插值对齐"          # 使用 MVTools 插值
    ]
    
    def __init__(self):
        super().__init__()

        # 窗口配置
        self.title("VSE Screenshot - 视频对齐截图工具")
        self.geometry("1600x900")

        # 创建必要的目录
        self.setup_directories()

        # 项目管理器
        self.project_manager = ProjectManager()
        self.current_project = None  # 当前项目名称

        # 数据
        self.videos: List[VideoEntry] = []
        self.config_path = "config.json"
        self.reference_image_path: Optional[str] = None
        self.reference_note: str = ""
        self.program_name: str = "视频对比项目"

        # 截图配置
        self.screenshot_count = 10
        self.screenshot_mode = "random"  # random 或 specific
        self.screenshot_frames = ""
        self.tolerance_frames = 3  # 容错帧数（前后各N帧）
        self.screenshot_history = []  # 历史截图帧数记录
        self.frame_range_start = 0  # 随机帧数区间起始
        self.frame_range_end = 0  # 随机帧数区间结束（0表示视频结尾）

        # 预览窗口管理
        self.preview_process = None  # 当前预览进程

        # 创建UI
        self.create_widgets()

        # 显示项目选择对话框
        self.show_project_selector()

        # 日志
        self.log("应用程序已启动")

    def setup_directories(self):
        """创建必要的目录"""
        # 创建缓存目录
        cache_dir = ".cache"
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        # 创建.gitignore
        gitignore_path = ".gitignore"
        gitignore_content = """# 缓存文件
.cache/
*.lwi

# 截图目录
screenshots_*/

# Python缓存
__pycache__/
*.pyc
*.pyo

# 配置文件（可选）
# config.json

# IDE
.vscode/
.idea/
*.swp
*.swo
"""
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write(gitignore_content)

    def show_project_selector(self):
        """显示项目选择对话框"""
        dialog = ProjectSelectorDialog(self, self.project_manager)
        self.wait_window(dialog)

        if dialog.selected_project:
            # 切换项目时清空当前配置
            self.clear_current_project()

            self.current_project = dialog.selected_project
            self.load_project(dialog.selected_project)
            # 更新项目标签
            if hasattr(self, 'project_label'):
                self.project_label.configure(text=f"项目: {self.current_project}")
        else:
            # 如果没有选择项目且是首次启动
            if not self.current_project:
                # 创建默认项目
                self.current_project = "默认项目"
                self.project_manager.create_project(self.current_project)
                self.log(f"创建默认项目: {self.current_project}")
                if hasattr(self, 'project_label'):
                    self.project_label.configure(text=f"项目: {self.current_project}")

    def clear_current_project(self):
        """清空当前项目的配置和视频列表"""
        # 清空视频列表
        self.videos = []

        # 清空参考图
        self.reference_image_path = None
        if hasattr(self, 'image_label'):
            self.image_label.configure(image='', text="未上传图片\n(点击查看大图)")

        # 清空备注
        self.reference_note = ""
        if hasattr(self, 'note_text'):
            self.note_text.delete("1.0", "end")

        # 重置截图数量
        self.screenshot_count = 10
        if hasattr(self, 'screenshot_count_entry'):
            self.screenshot_count_entry.delete(0, 'end')
            self.screenshot_count_entry.insert(0, "10")

        # 清空历史帧数
        self.screenshot_history = []
        self.update_history_combo()

        # 刷新视频列表
        if hasattr(self, 'video_scroll'):
            self.refresh_video_list()

    def load_project(self, project_name: str):
        """加载项目"""
        config = self.project_manager.load_project(project_name)
        if config:
            self.program_name = config.get('program_name', project_name)
            self.reference_note = config.get('reference_note', '')
            self.screenshot_count = config.get('screenshot_count', 10)

            # 加载历史帧数
            self.screenshot_history = config.get('screenshot_history', [])

            # 扫描截图文件夹，提取历史帧数
            self.scan_screenshot_folders()

            self.update_history_combo()

            # 加载视频列表
            self.videos = []
            for video_data in config.get('videos', []):
                # 兼容旧格式的截图帧率
                old_screenshot_fps = video_data.get("screenshot_fps", "25.00")
                if "按" in old_screenshot_fps:
                    # 旧格式：按25帧截图 -> 25.00
                    import re
                    match = re.search(r'(\d+\.?\d*)', old_screenshot_fps)
                    screenshot_fps = match.group(1) if match else "25.00"
                    # 格式化为两位小数
                    try:
                        fps_val = float(screenshot_fps)
                        screenshot_fps = f"{fps_val:.2f}" if fps_val < 100 else f"{fps_val:.0f}"
                    except:
                        screenshot_fps = "25.00"
                else:
                    screenshot_fps = old_screenshot_fps

                video = VideoEntry(
                    filepath=video_data['filepath'],
                    name=video_data.get('name', ''),
                    offset=video_data.get('offset', 0),
                    tolerance=video_data.get('tolerance', 0),
                    fps_type=video_data.get('fps_type', '原生PAL (25fps)'),
                    fps_display=video_data.get('fps_display', '未知'),
                    screenshot_fps=screenshot_fps,
                    alignment_mode=video_data.get('alignment_mode', '不对齐'),
                    use_qtgmc=video_data.get('use_qtgmc', False),
                    qtgmc_tff=video_data.get('qtgmc_tff', True)
                )
                self.videos.append(video)

            # 加载参考图
            ref_image = config.get('reference_image', '')
            if ref_image:
                # 检查是否是相对路径
                if not os.path.isabs(ref_image):
                    project_path = config.get('_project_path', '')
                    ref_image = os.path.join(project_path, 'references', ref_image)

                if os.path.exists(ref_image):
                    self.reference_image_path = ref_image

            self.log(f"已加载项目: {project_name}")
            self.update_ui_from_data()
        else:
            self.log(f"加载项目失败: {project_name}")

    def save_current_project(self):
        """保存当前项目"""
        if not self.current_project:
            return

        config = {
            'program_name': self.current_project,
            'reference_note': self.note_text.get("1.0", "end-1c") if hasattr(self, 'note_text') else self.reference_note,
            'screenshot_count': self.screenshot_count,
            'screenshot_history': self.screenshot_history,  # 保存历史帧数
            'videos': []
        }

        # 保存视频列表
        for video in self.videos:
            config['videos'].append({
                'filepath': video.filepath,
                'name': video.name,
                'offset': video.offset,
                'tolerance': video.tolerance,
                'fps_type': video.fps_type,  # 保留用于兼容性
                'fps_display': video.fps_display,
                'screenshot_fps': video.screenshot_fps,
                'alignment_mode': getattr(video, 'alignment_mode', '不对齐'),
                'use_qtgmc': video.use_qtgmc,
                'qtgmc_tff': video.qtgmc_tff
            })

        # 保存参考图（复制到项目references目录）
        if self.reference_image_path and os.path.exists(self.reference_image_path):
            try:
                # 获取项目references目录
                project_path = os.path.join(self.project_manager.projects_dir, self.current_project)
                ref_dir = os.path.join(project_path, 'references')
                os.makedirs(ref_dir, exist_ok=True)

                # 复制参考图到项目目录
                ref_filename = os.path.basename(self.reference_image_path)
                ref_dest = os.path.join(ref_dir, ref_filename)

                # 如果源文件不在项目目录，则复制
                if os.path.abspath(self.reference_image_path) != os.path.abspath(ref_dest):
                    import shutil
                    shutil.copy2(self.reference_image_path, ref_dest)

                # 保存相对路径
                config['reference_image'] = ref_filename
            except Exception as e:
                self.log(f"保存参考图失败: {e}")

        if self.project_manager.save_project(self.current_project, config):
            self.log(f"项目已保存: {self.current_project}")
        else:
            self.log(f"项目保存失败: {self.current_project}")

    def update_ui_from_data(self):
        """从数据更新UI"""
        if hasattr(self, 'note_text'):
            self.note_text.delete("1.0", "end")
            self.note_text.insert("1.0", self.reference_note)

        if hasattr(self, 'screenshot_count_entry'):
            self.screenshot_count_entry.delete(0, 'end')
            self.screenshot_count_entry.insert(0, str(self.screenshot_count))

        # 更新参考图显示
        if self.reference_image_path and hasattr(self, 'image_label'):
            self.display_reference_image(self.reference_image_path)

        # 刷新视频列表
        if hasattr(self, 'video_scroll'):
            self.refresh_video_list()

    def create_widgets(self):
        """创建UI组件"""
        # 主容器 - 使用grid布局
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 左侧面板 - 对齐参考图
        self.create_left_panel()
        
        # 右侧面板 - 主要内容
        self.create_right_panel()
    
    def create_left_panel(self):
        """创建左侧面板"""
        left_frame = ctk.CTkFrame(self, width=300)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_frame.grid_propagate(False)
        
        # 项目信息和切换按钮
        project_frame = ctk.CTkFrame(left_frame)
        project_frame.pack(pady=(10, 5), padx=10, fill="x")

        self.project_label = ctk.CTkLabel(project_frame, text=f"项目: {self.current_project or '未选择'}",
                                          font=("Arial", 12))
        self.project_label.pack(side="left", padx=5)

        # 保存配置按钮
        save_btn = ctk.CTkButton(project_frame, text="保存", width=60,
                                  command=self.save_config,
                                  fg_color="#4caf50", hover_color="#45a049")
        save_btn.pack(side="right", padx=2)

        # 切换项目按钮
        switch_btn = ctk.CTkButton(project_frame, text="切换", width=60,
                                    command=self.show_project_selector,
                                    fg_color="#2196f3", hover_color="#1976d2")
        switch_btn.pack(side="right", padx=2)

        # 标题
        title = ctk.CTkLabel(left_frame, text="对齐参考图", font=("Arial", 16, "bold"))
        title.pack(pady=(10, 5))
        
        # 图片预览区域
        self.image_label = ctk.CTkLabel(left_frame, text="未上传图片\n(点击查看大图)",
                                        width=260, height=200,
                                        fg_color=("gray85", "gray25"),
                                        cursor="hand2")
        self.image_label.pack(pady=10, padx=10)
        self.image_label.bind("<Button-1>", self.show_image_viewer)
        
        # 上传按钮
        upload_btn = ctk.CTkButton(left_frame, text="上传/更换图片", 
                                   command=self.upload_reference_image)
        upload_btn.pack(pady=5)
        
        # 备注区域
        note_label = ctk.CTkLabel(left_frame, text="备注:")
        note_label.pack(pady=(10, 5))

        self.note_text = ctk.CTkTextbox(left_frame, height=80)
        self.note_text.pack(pady=5, padx=10, fill="x")

        # 日志区域（移到这里）
        log_label = ctk.CTkLabel(left_frame, text="日志输出:", font=("Arial", 12, "bold"))
        log_label.pack(pady=(10, 5), padx=5, anchor="w")

        self.log_text = ctk.CTkTextbox(left_frame, height=150)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)
    
    def create_right_panel(self):
        """创建右侧面板"""
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        right_frame.grid_rowconfigure(2, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # 顶部操作栏
        self.create_top_bar(right_frame)

        # 视频列表
        self.create_video_list(right_frame)

        # 底部操作按钮
        self.create_bottom_buttons(right_frame)
    
    def create_top_bar(self, parent):
        """创建顶部操作栏"""
        top_bar = ctk.CTkFrame(parent, height=50)
        top_bar.grid(row=0, column=0, pady=(0, 10), sticky="ew")

        # 添加视频按钮
        add_btn = ctk.CTkButton(top_bar, text="➕ 添加视频", command=self.add_videos)
        add_btn.pack(side="left", padx=5, pady=5)

        # 全选按钮
        select_all_btn = ctk.CTkButton(top_bar, text="☑ 全选", command=self.select_all_videos,
                                        width=80, fg_color="#2196f3", hover_color="#1976d2")
        select_all_btn.pack(side="left", padx=5, pady=5)

        # 取消全选按钮
        deselect_all_btn = ctk.CTkButton(top_bar, text="☐ 取消", command=self.deselect_all_videos,
                                          width=80, fg_color="#757575", hover_color="#616161")
        deselect_all_btn.pack(side="left", padx=5, pady=5)

        # 批量删除按钮
        delete_btn = ctk.CTkButton(top_bar, text="🗑 批量删除", command=self.batch_delete_videos,
                                    fg_color="#f44336", hover_color="#d32f2f")
        delete_btn.pack(side="left", padx=5, pady=5)
    

    def create_video_list(self, parent):
        """创建视频列表"""
        list_frame = ctk.CTkFrame(parent)
        list_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # 表头
        header_frame = ctk.CTkFrame(list_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        headers = ["截图", "序号", "视频名称", "对齐帧数", "视频帧率", "扫描方式", "截图帧率", "对齐方式", "反交错", "容错帧数", "操作"]
        widths = [50, 50, 200, 80, 100, 100, 100, 100, 70, 80, 150]

        for i, (header, width) in enumerate(zip(headers, widths)):
            label = ctk.CTkLabel(header_frame, text=header, width=width, font=("Arial", 12, "bold"))
            label.grid(row=0, column=i, padx=2)

        # 滚动区域
        self.video_scroll = ctk.CTkScrollableFrame(list_frame, height=300)
        self.video_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.video_scroll.grid_columnconfigure(0, weight=1)

        self.video_rows = []
    
    def create_bottom_buttons(self, parent):
        """创建底部操作按钮"""
        button_frame = ctk.CTkFrame(parent)
        button_frame.grid(row=3, column=0, pady=(0, 10), sticky="ew")
        
        # 预览按钮
        preview_btn = ctk.CTkButton(button_frame, text="👁 初始预览",
                                    command=self.preview_videos,
                                    fg_color="#1976d2", hover_color="#1565c0")
        preview_btn.pack(side="left", padx=5, pady=5)
        
        # 对齐按钮
        align_btn = ctk.CTkButton(button_frame, text="🎯 对齐预览", 
                                  command=self.align_videos,
                                  fg_color="#4caf50", hover_color="#388e3c")
        align_btn.pack(side="left", padx=5, pady=5)
        
        # 截图按钮
        screenshot_btn = ctk.CTkButton(button_frame, text="📸 开始截图", 
                                       command=self.start_screenshot,
                                       fg_color="#ff9800", hover_color="#f57c00")
        screenshot_btn.pack(side="left", padx=5, pady=5)
        
        # 截图配置
        ctk.CTkLabel(button_frame, text="截图数量:").pack(side="left", padx=(20, 5))
        self.screenshot_count_entry = ctk.CTkEntry(button_frame, width=60)
        self.screenshot_count_entry.insert(0, str(self.screenshot_count))
        self.screenshot_count_entry.pack(side="left", padx=5)

        # 历史帧数选择
        ctk.CTkLabel(button_frame, text="使用历史帧数:").pack(side="left", padx=(20, 5))
        self.history_combo = ctk.CTkComboBox(button_frame, values=["新建"], width=150, state="readonly")
        self.history_combo.set("新建")
        self.history_combo.pack(side="left", padx=5)

        # 帧数区间设置
        ctk.CTkLabel(button_frame, text="帧数区间:").pack(side="left", padx=(20, 5))
        self.frame_range_start_entry = ctk.CTkEntry(button_frame, width=60, placeholder_text="起始")
        self.frame_range_start_entry.insert(0, "0")
        self.frame_range_start_entry.pack(side="left", padx=2)

        ctk.CTkLabel(button_frame, text="-").pack(side="left", padx=2)

        self.frame_range_end_entry = ctk.CTkEntry(button_frame, width=60, placeholder_text="结束")
        self.frame_range_end_entry.insert(0, "0")
        self.frame_range_end_entry.pack(side="left", padx=2)

        ctk.CTkLabel(button_frame, text="(0=结尾)").pack(side="left", padx=2)
    

    def log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")
        print(log_entry.strip())

    def scan_screenshot_folders(self):
        """扫描截图文件夹，从文件名提取历史帧数"""
        if not self.current_project:
            return

        try:
            # 获取项目的screenshots目录
            screenshots_dir = self.project_manager.get_project_screenshots_dir(self.current_project)

            if not os.path.exists(screenshots_dir):
                return

            # 遍历所有子文件夹
            for folder_name in os.listdir(screenshots_dir):
                folder_path = os.path.join(screenshots_dir, folder_name)

                if not os.path.isdir(folder_path):
                    continue

                # 检查是否已经在历史记录中
                already_exists = any(h.get('folder') == folder_name for h in self.screenshot_history)
                if already_exists:
                    continue

                # 从文件夹中的图片文件名提取帧数
                frame_numbers = set()
                for filename in os.listdir(folder_path):
                    if filename.endswith('.png'):
                        # 文件名格式: {对齐帧数}_{原始帧数}_{版本名}.png
                        parts = filename.split('_')
                        if len(parts) >= 2:
                            try:
                                aligned_frame = int(parts[0])
                                frame_numbers.add(aligned_frame)
                            except ValueError:
                                continue

                if frame_numbers:
                    # 排序帧数
                    sorted_frames = sorted(list(frame_numbers))

                    # 添加到历史记录
                    history_name = f"{folder_name} ({len(sorted_frames)}张)"
                    self.screenshot_history.append({
                        'name': history_name,
                        'frames': sorted_frames,
                        'timestamp': folder_name,
                        'folder': folder_name,
                        'source': 'folder'  # 标记来源是文件夹
                    })
                    self.log(f"从文件夹提取历史帧数: {history_name}")

        except Exception as e:
            self.log(f"扫描截图文件夹失败: {e}")

    def update_history_combo(self):
        """更新历史帧数下拉框"""
        if hasattr(self, 'history_combo'):
            history_names = ["新建"] + [h['name'] for h in self.screenshot_history]
            self.history_combo.configure(values=history_names)
    
    def add_videos(self):
        """添加视频文件"""
        filepaths = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mkv *.avi *.mov *.ts *.m2ts *.webm"),
                ("所有文件", "*.*")
            ]
        )

        if filepaths:
            from video_utils import get_video_info

            # 收集所有视频的帧率信息
            fps_list = []

            for filepath in filepaths:
                # 自动检测视频信息
                self.log(f"正在检测视频: {os.path.basename(filepath)}")
                video_info = get_video_info(filepath)

                scan_info = video_info['scan_info']
                use_qtgmc = scan_info['is_interlaced']
                qtgmc_tff = scan_info['tff']

                # 确定扫描方式
                if use_qtgmc:
                    if qtgmc_tff:
                        scan_type = "隔行 TFF"
                        field_order = "TFF"
                    else:
                        scan_type = "隔行 BFF"
                        field_order = "BFF"
                    self.log(f"  检测到隔行扫描 ({field_order})，已自动启用反交错")
                else:
                    scan_type = "逐行"
                    self.log(f"  检测到逐行扫描")

                # 获取帧率信息
                fps = video_info.get('fps')
                fps_display = video_info.get('fps_display', '未知')

                # 提取视频帧率（纯数字）
                video_fps = self._extract_fps_from_display(fps_display)

                self.log(f"  帧率: {video_fps} fps, 扫描方式: {scan_type}")

                if fps:
                    fps_list.append(fps)

                video = VideoEntry(
                    filepath=filepath,
                    use_qtgmc=use_qtgmc,
                    qtgmc_tff=qtgmc_tff,
                    fps_display=fps_display,
                    screenshot_fps="25.00",  # 临时默认值，稍后会更新
                    video_fps=video_fps,
                    scan_type=scan_type
                )
                self.videos.append(video)
                self.add_video_row(video)

            # 根据大多数视频的帧率自动设置截图帧率
            if fps_list:
                self.auto_set_screenshot_fps(fps_list)

            self.log(f"已添加 {len(filepaths)} 个视频文件")

    def _build_fps_display(self, video_fps: str, scan_type: str) -> str:
        """
        从帧率和扫描方式构建 fps_display（用于兼容性）

        示例: ("60.00", "逐行") -> "60p"
              ("25.00", "隔行 TFF") -> "25i"
        """
        try:
            fps_val = float(video_fps)
            # 简化帧率显示
            if abs(fps_val - int(fps_val)) < 0.01:
                fps_str = str(int(fps_val))
            else:
                fps_str = video_fps
        except:
            fps_str = video_fps

        # 扫描类型
        if "隔行" in scan_type:
            scan_char = 'i'
        else:
            scan_char = 'p'

        return f"{fps_str}{scan_char}"

    def _extract_fps_from_display(self, fps_display: str) -> str:
        """
        从 fps_display 提取帧率数字

        示例: "25p" -> "25.00", "60p" -> "60.00", "29.97i" -> "29.97"
        """
        if not fps_display or fps_display == "未知":
            return "25.00"

        import re
        match = re.match(r'([\d.]+)', fps_display)
        if match:
            fps_str = match.group(1)
            try:
                fps_val = float(fps_str)
                # 格式化为标准格式
                if abs(fps_val - 23.976) < 0.01:
                    return "23.976"
                elif abs(fps_val - 29.97) < 0.01:
                    return "29.97"
                elif abs(fps_val - 59.94) < 0.01:
                    return "59.94"
                elif abs(fps_val - 119.88) < 0.01:
                    return "119.88"
                else:
                    return f"{fps_val:.2f}"
            except:
                pass

        return "25.00"

    def _extract_scan_type_from_display(self, fps_display: str) -> str:
        """
        从 fps_display 提取扫描类型

        示例: "25p" -> "逐行", "25i" -> "隔行 TFF", "60p" -> "逐行"
        """
        if not fps_display or fps_display == "未知":
            return "逐行"

        # 检查是否包含 'i' (interlaced)
        if 'i' in fps_display.lower():
            return "隔行 TFF"  # 默认 TFF
        else:
            return "逐行"

    def _on_fps_change(self, idx: int, choice: str):
        """处理帧率选择变化，支持自定义帧率"""
        if choice == "自定义...":
            from tkinter import simpledialog
            custom_fps = simpledialog.askstring(
                "自定义帧率",
                "请输入帧率值（例如: 48.00, 72.00, 90.00）:",
                parent=self
            )
            if custom_fps:
                try:
                    # 验证输入
                    fps_val = float(custom_fps)
                    if 1.0 <= fps_val <= 240.0:
                        formatted_fps = f"{fps_val:.2f}"
                        # 更新下拉框显示
                        if idx < len(self.video_rows):
                            self.video_rows[idx]['video_fps'].set(formatted_fps)
                    else:
                        messagebox.showerror("错误", "帧率必须在 1.0 到 240.0 之间")
                        self.video_rows[idx]['video_fps'].set("25.00")
                except ValueError:
                    messagebox.showerror("错误", "无效的帧率值")
                    self.video_rows[idx]['video_fps'].set("25.00")
            else:
                # 用户取消，恢复默认值
                self.video_rows[idx]['video_fps'].set("25.00")

    def _convert_fps_display_to_new_format(self, old_fps_display: str) -> str:
        """
        将旧的 fps_display 格式转换为新格式

        旧格式: "25p", "25i", "60p", "29.97i" 等
        新格式: "25.00 progressive", "25.00 interlaced" 等
        """
        if not old_fps_display or old_fps_display == "未知":
            return "25.00 progressive"

        # 提取帧率数字和扫描类型
        import re
        match = re.match(r'([\d.]+)([pi]?)', old_fps_display.lower())
        if match:
            fps_str = match.group(1)
            scan_type = match.group(2)

            # 格式化帧率
            try:
                fps_val = float(fps_str)
                if abs(fps_val - 23.976) < 0.01:
                    fps_formatted = "23.976"
                elif abs(fps_val - 29.97) < 0.01:
                    fps_formatted = "29.97"
                elif abs(fps_val - 59.94) < 0.01:
                    fps_formatted = "59.94"
                else:
                    fps_formatted = f"{fps_val:.2f}"
            except:
                fps_formatted = "25.00"

            # 确定扫描类型
            if scan_type == 'i':
                scan_name = "interlaced"
            else:
                scan_name = "progressive"

            return f"{fps_formatted} {scan_name}"

        return "25.00 progressive"

    def _convert_fps_display_to_old_format(self, new_fps_display: str) -> str:
        """
        将新的 fps_display 格式转换为旧格式（用于兼容性）

        新格式: "25.00 progressive", "25.00 interlaced" 等
        旧格式: "25p", "25i" 等
        """
        parts = new_fps_display.split()
        if len(parts) >= 2:
            fps_str = parts[0]
            scan_type = parts[1]

            # 简化帧率显示
            try:
                fps_val = float(fps_str)
                if abs(fps_val - int(fps_val)) < 0.01:
                    fps_display = str(int(fps_val))
                else:
                    fps_display = fps_str
            except:
                fps_display = fps_str

            # 扫描类型
            scan_char = 'i' if 'interlaced' in scan_type.lower() else 'p'

            return f"{fps_display}{scan_char}"

        return new_fps_display

    def auto_set_screenshot_fps(self, fps_list):
        """
        根据大多数视频的帧率自动设置统一的截图帧率（基准帧率）

        注意：截图帧率是对齐帧数的基准，不是视频的实际帧率
        公式：实际帧数 = int(对齐帧数 × (视频帧率/截图帧率)) + 偏移量

        Args:
            fps_list: 帧率列表（与 self.videos 对应）
        """
        from collections import Counter

        def normalize_fps(fps):
            """将帧率归类到标准值"""
            if abs(fps - 23.976) < 0.01:
                return "23.976"
            elif abs(fps - 24.0) < 0.01:
                return "24.00"
            elif abs(fps - 25.0) < 0.01:
                return "25.00"
            elif abs(fps - 29.97) < 0.01:
                return "29.97"
            elif abs(fps - 30.0) < 0.01:
                return "30.00"
            elif abs(fps - 50.0) < 0.01:
                return "50.00"
            elif abs(fps - 59.94) < 0.01:
                return "59.94"
            elif abs(fps - 60.0) < 0.01:
                return "60.00"
            else:
                return f"{fps:.2f}"

        # 统计帧率出现次数
        fps_counter = Counter()
        for fps in fps_list:
            normalized = normalize_fps(fps)
            fps_counter[normalized] += 1

        # 找出最常见的帧率作为截图帧率（基准帧率）
        if fps_counter:
            most_common_fps = fps_counter.most_common(1)[0][0]
            self.log(f"自动设置截图帧率（基准帧率）为: {most_common_fps}")

            # 所有视频使用相同的截图帧率（基准帧率）
            for i, video in enumerate(self.videos):
                video.screenshot_fps = most_common_fps

                # 更新UI
                if i < len(self.video_rows):
                    self.video_rows[i]['screenshot_fps'].set(most_common_fps)

    def add_video_row(self, video: VideoEntry):
        """添加视频行到列表"""
        row_frame = ctk.CTkFrame(self.video_scroll)
        row_frame.pack(fill="x", pady=2)

        idx = len(self.video_rows)

        # 截图复选框（默认选中）
        screenshot_check = ctk.CTkCheckBox(row_frame, text="", width=50)
        screenshot_check.select()  # 默认选中
        screenshot_check.grid(row=0, column=0, padx=2)

        # 序号
        num_label = ctk.CTkLabel(row_frame, text=str(idx + 1), width=50)
        num_label.grid(row=0, column=1, padx=2)

        # 视频名称
        name_entry = ctk.CTkEntry(row_frame, width=200)
        name_entry.insert(0, video.name)
        name_entry.grid(row=0, column=2, padx=2)

        # 对齐帧数
        offset_entry = ctk.CTkEntry(row_frame, width=80)
        offset_entry.insert(0, str(video.offset))
        offset_entry.grid(row=0, column=3, padx=2)

        # 帧率（下拉选择，支持自定义）
        video_fps_combo = ctk.CTkComboBox(row_frame, values=self.VIDEO_FPS_OPTIONS, width=100)
        video_fps_value = getattr(video, 'video_fps', self._extract_fps_from_display(video.fps_display))
        video_fps_combo.set(video_fps_value)
        video_fps_combo.configure(command=lambda choice: self._on_fps_change(idx, choice))
        video_fps_combo.grid(row=0, column=4, padx=2)

        # 扫描方式（下拉选择）
        scan_type_combo = ctk.CTkComboBox(row_frame, values=self.SCAN_TYPE_OPTIONS, width=100)
        scan_type_value = getattr(video, 'scan_type', self._extract_scan_type_from_display(video.fps_display))
        scan_type_combo.set(scan_type_value)
        scan_type_combo.grid(row=0, column=5, padx=2)

        # 截图帧率（下拉选择）
        screenshot_fps_combo = ctk.CTkComboBox(row_frame, values=self.SCREENSHOT_FPS_OPTIONS, width=100)
        screenshot_fps_combo.set(video.screenshot_fps)
        screenshot_fps_combo.grid(row=0, column=6, padx=2)

        # 对齐方式（下拉选择）
        alignment_combo = ctk.CTkComboBox(row_frame, values=self.ALIGNMENT_MODES, width=100)
        alignment_combo.set(getattr(video, 'alignment_mode', '不对齐'))
        alignment_combo.grid(row=0, column=7, padx=2)

        # QTGMC（反交错）
        qtgmc_check = ctk.CTkCheckBox(row_frame, text="", width=70)
        if video.use_qtgmc:
            qtgmc_check.select()
        qtgmc_check.grid(row=0, column=8, padx=2)

        # 容错帧数
        tolerance_entry = ctk.CTkEntry(row_frame, width=80)
        tolerance_entry.insert(0, str(video.tolerance))
        tolerance_entry.grid(row=0, column=9, padx=2)

        # 操作按钮
        btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=10, padx=2)

        up_btn = ctk.CTkButton(btn_frame, text="↑", width=40, command=lambda: self.move_video_up(idx))
        up_btn.pack(side="left", padx=2)

        down_btn = ctk.CTkButton(btn_frame, text="↓", width=40, command=lambda: self.move_video_down(idx))
        down_btn.pack(side="left", padx=2)

        del_btn = ctk.CTkButton(btn_frame, text="🗑", width=40, command=lambda: self.delete_video(idx),
                               fg_color="#d32f2f", hover_color="#b71c1c")
        del_btn.pack(side="left", padx=2)

        self.video_rows.append({
            'frame': row_frame,
            'screenshot': screenshot_check,
            'name': name_entry,
            'offset': offset_entry,
            'video_fps': video_fps_combo,
            'scan_type': scan_type_combo,
            'screenshot_fps': screenshot_fps_combo,
            'alignment_mode': alignment_combo,
            'qtgmc': qtgmc_check,
            'tolerance': tolerance_entry
        })

    def move_video_up(self, idx: int):
        """上移视频"""
        if idx > 0:
            self.videos[idx], self.videos[idx-1] = self.videos[idx-1], self.videos[idx]
            self.refresh_video_list()
            self.log(f"已上移视频: {self.videos[idx].name}")

    def move_video_down(self, idx: int):
        """下移视频"""
        if idx < len(self.videos) - 1:
            self.videos[idx], self.videos[idx+1] = self.videos[idx+1], self.videos[idx]
            self.refresh_video_list()
            self.log(f"已下移视频: {self.videos[idx].name}")

    def delete_video(self, idx: int):
        """删除视频"""
        video = self.videos[idx]
        self.videos.pop(idx)
        self.refresh_video_list()
        self.log(f"已删除视频: {video.name}")

    def select_all_videos(self):
        """全选所有视频"""
        for row in self.video_rows:
            row['screenshot'].select()
        self.log("已全选所有视频")

    def deselect_all_videos(self):
        """取消全选所有视频"""
        for row in self.video_rows:
            row['screenshot'].deselect()
        self.log("已取消全选所有视频")

    def batch_delete_videos(self):
        """批量删除选中的视频"""
        if not self.videos:
            messagebox.showinfo("提示", "当前没有视频")
            return

        # 获取选中的视频索引
        selected_indices = []
        for i, row in enumerate(self.video_rows):
            if row['screenshot'].get():  # 检查复选框是否选中
                selected_indices.append(i)

        if not selected_indices:
            messagebox.showinfo("提示", "请至少选择一个视频")
            return

        # 确认删除
        result = messagebox.askyesno("确认删除",
                                      f"确定要删除选中的 {len(selected_indices)} 个视频吗？")
        if not result:
            return

        # 从后往前删除，避免索引变化
        for idx in sorted(selected_indices, reverse=True):
            self.videos.pop(idx)

        self.refresh_video_list()
        self.log(f"已批量删除 {len(selected_indices)} 个视频")

    def refresh_video_list(self):
        """刷新视频列表显示（优化版）"""
        # 禁用更新以提高性能
        self.video_scroll.update_idletasks()

        # 清空现有行
        for row in self.video_rows:
            row['frame'].destroy()
        self.video_rows.clear()

        # 批量添加所有视频
        for video in self.videos:
            self.add_video_row(video)

        # 强制更新显示
        self.video_scroll.update_idletasks()

    def update_videos_from_ui(self):
        """从UI更新视频数据"""
        for i, row in enumerate(self.video_rows):
            if i < len(self.videos):
                self.videos[i].name = row['name'].get()
                try:
                    self.videos[i].offset = int(row['offset'].get())
                except ValueError:
                    self.videos[i].offset = 0
                try:
                    self.videos[i].tolerance = int(row['tolerance'].get())
                except ValueError:
                    self.videos[i].tolerance = 0
                # 更新视频帧率
                self.videos[i].video_fps = row['video_fps'].get()
                # 更新扫描方式
                self.videos[i].scan_type = row['scan_type'].get()
                # 更新截图帧率
                self.videos[i].screenshot_fps = row['screenshot_fps'].get()
                # 更新对齐方式
                self.videos[i].alignment_mode = row['alignment_mode'].get()
                # 更新 fps_display（用于兼容性）
                self.videos[i].fps_display = self._build_fps_display(
                    self.videos[i].video_fps,
                    self.videos[i].scan_type
                )
                # 更新反交错设置
                self.videos[i].use_qtgmc = row['qtgmc'].get() == 1

    def upload_reference_image(self):
        """上传对齐参考图"""
        filepath = filedialog.askopenfilename(
            title="选择对齐参考图",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp"), ("所有文件", "*.*")]
        )

        if filepath:
            self.reference_image_path = filepath
            self.display_reference_image()

            # 读取文件名（不含扩展名）作为初始备注
            filename = os.path.basename(filepath)
            name_without_ext = os.path.splitext(filename)[0]

            # 设置到备注框
            if hasattr(self, 'note_text'):
                current_note = self.note_text.get("1.0", "end-1c").strip()
                if not current_note:  # 只在备注为空时设置
                    self.note_text.delete("1.0", "end")
                    self.note_text.insert("1.0", name_without_ext)
                    self.reference_note = name_without_ext
                    self.log(f"已设置备注: {name_without_ext}")

            self.log(f"已上传参考图: {os.path.basename(filepath)}")

    def display_reference_image(self, image_path=None):
        """显示参考图预览"""
        if image_path:
            self.reference_image_path = image_path

        if self.reference_image_path and os.path.exists(self.reference_image_path):
            try:
                img = Image.open(self.reference_image_path)
                img.thumbnail((260, 200))
                photo = ImageTk.PhotoImage(img)
                self.image_label.configure(image=photo, text="")
                self.image_label.image = photo  # 保持引用
            except Exception as e:
                self.log(f"显示图片失败: {e}")

    def save_config(self):
        """保存配置"""
        self.update_videos_from_ui()

        # 使用项目管理器保存
        if self.current_project:
            self.save_current_project()
        else:
            # 兼容旧的保存方式
            config = {
                "program_name": self.current_project or "视频对比项目",
                "reference_image": self.reference_image_path,
                "reference_note": self.note_text.get("1.0", "end-1c") if hasattr(self, 'note_text') else "",
                "screenshot_count": int(self.screenshot_count_entry.get()) if hasattr(self, 'screenshot_count_entry') else 10,
                "videos": [
                    {
                        "filepath": v.filepath,
                        "name": v.name,
                        "offset": v.offset,
                        "tolerance": v.tolerance,
                        "fps_type": v.fps_type,  # 保留用于兼容性
                        "fps_display": v.fps_display,
                        "screenshot_fps": v.screenshot_fps,
                        "use_qtgmc": v.use_qtgmc,
                        "qtgmc_tff": v.qtgmc_tff
                    }
                    for v in self.videos
                ]
            }

            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                self.log(f"配置已保存到: {self.config_path}")
                messagebox.showinfo("成功", "配置已保存")
            except Exception as e:
                self.log(f"保存配置失败: {e}")
                messagebox.showerror("错误", f"保存配置失败: {e}")

    def load_config(self):
        """从JSON加载配置"""
        if not os.path.exists(self.config_path):
            self.log("配置文件不存在，使用默认配置")
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 加载基本信息
            self.program_name = config.get("program_name", "视频对比项目")

            self.reference_image_path = config.get("reference_image")
            if self.reference_image_path:
                self.display_reference_image()

            note = config.get("reference_note", "")
            if hasattr(self, 'note_text'):
                self.note_text.delete("1.0", "end")
                self.note_text.insert("1.0", note)

            self.screenshot_count = config.get("screenshot_count", 10)
            if hasattr(self, 'screenshot_count_entry'):
                self.screenshot_count_entry.delete(0, "end")
                self.screenshot_count_entry.insert(0, str(self.screenshot_count))

            # 加载视频列表
            self.videos.clear()
            for row in self.video_rows:
                row['frame'].destroy()
            self.video_rows.clear()

            for v_data in config.get("videos", []):
                # 兼容旧格式的截图帧率
                old_screenshot_fps = v_data.get("screenshot_fps", "25.00")
                if "按" in old_screenshot_fps:
                    # 旧格式：按25帧截图 -> 25.00
                    import re
                    match = re.search(r'(\d+\.?\d*)', old_screenshot_fps)
                    screenshot_fps = match.group(1) if match else "25.00"
                    # 格式化为两位小数
                    try:
                        fps_val = float(screenshot_fps)
                        screenshot_fps = f"{fps_val:.2f}" if fps_val < 100 else f"{fps_val:.0f}"
                    except:
                        screenshot_fps = "25.00"
                else:
                    screenshot_fps = old_screenshot_fps

                video = VideoEntry(
                    filepath=v_data["filepath"],
                    name=v_data.get("name", ""),
                    offset=v_data.get("offset", 0),
                    tolerance=v_data.get("tolerance", 0),
                    fps_type=v_data.get("fps_type", "原生PAL (25fps)"),
                    fps_display=v_data.get("fps_display", "未知"),
                    screenshot_fps=screenshot_fps,
                    use_qtgmc=v_data.get("use_qtgmc", False)
                )
                self.videos.append(video)
                self.add_video_row(video)

            self.log(f"配置已加载: {len(self.videos)} 个视频")
        except Exception as e:
            self.log(f"加载配置失败: {e}")
            messagebox.showerror("错误", f"加载配置失败: {e}")

    def export_config_package(self):
        """导出配置包"""
        self.update_videos_from_ui()
        self.save_config()

        # 创建导出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        program_name = self.program_name_entry.get() or "视频对比项目"
        export_dir = f"{program_name}_{timestamp}"

        try:
            os.makedirs(export_dir, exist_ok=True)

            # 复制配置文件
            shutil.copy(self.config_path, os.path.join(export_dir, "config.json"))

            # 复制参考图
            if self.reference_image_path and os.path.exists(self.reference_image_path):
                ext = os.path.splitext(self.reference_image_path)[1]
                shutil.copy(self.reference_image_path,
                           os.path.join(export_dir, f"reference{ext}"))

            self.log(f"配置包已导出到: {export_dir}")
            messagebox.showinfo("成功", f"配置包已导出到:\n{export_dir}")
        except Exception as e:
            self.log(f"导出配置包失败: {e}")
            messagebox.showerror("错误", f"导出配置包失败: {e}")

    def close_preview_window(self):
        """关闭上一个预览窗口"""
        if self.preview_process:
            try:
                self.preview_process.terminate()
                self.log("已关闭上一个预览窗口")
            except:
                pass
            self.preview_process = None

    def preview_videos(self):
        """预览视频（偏移=0）"""
        self.update_videos_from_ui()

        if not self.videos:
            messagebox.showwarning("警告", "请先添加视频文件")
            return

        try:
            # 关闭上一个预览窗口
            self.close_preview_window()

            from vpy_generator import generate_preview_script
            script_path = "preview.vpy"
            generate_preview_script(self.videos, script_path)
            self.log(f"预览脚本已生成: {script_path}")
            self.launch_vspreview(script_path)
        except Exception as e:
            self.log(f"生成预览脚本失败: {e}")
            messagebox.showerror("错误", f"生成预览脚本失败: {e}")

    def align_videos(self):
        """对齐预览视频"""
        self.update_videos_from_ui()

        if not self.videos:
            messagebox.showwarning("警告", "请先添加视频文件")
            return

        try:
            # 关闭上一个预览窗口
            self.close_preview_window()

            from vpy_generator import generate_align_script
            script_path = "align.vpy"
            generate_align_script(self.videos, script_path)
            self.log(f"对齐脚本已生成: {script_path}")
            self.launch_vspreview(script_path)
        except Exception as e:
            self.log(f"生成对齐脚本失败: {e}")
            messagebox.showerror("错误", f"生成对齐脚本失败: {e}")

    def start_screenshot(self):
        """开始截图"""
        self.update_videos_from_ui()

        if not self.videos:
            messagebox.showwarning("警告", "请先添加视频文件")
            return

        # 获取选中的视频
        selected_videos = []
        for i, row in enumerate(self.video_rows):
            if row['screenshot'].get():  # 检查复选框是否选中
                if i < len(self.videos):
                    selected_videos.append(self.videos[i])

        if not selected_videos:
            messagebox.showwarning("警告", "请至少选择一个视频进行截图")
            return

        try:
            from screenshot_engine import take_screenshots_enhanced_with_frames

            # 检查是否使用历史帧数
            use_history = self.history_combo.get() if hasattr(self, 'history_combo') else "新建"
            frame_numbers = None

            if use_history != "新建":
                # 从历史记录中获取帧数
                for history in self.screenshot_history:
                    if history['name'] == use_history:
                        frame_numbers = history['frames']
                        self.log(f"使用历史帧数: {use_history} ({len(frame_numbers)} 帧)")
                        break

            # 使用项目的screenshots目录
            if self.current_project:
                base_dir = self.project_manager.get_project_screenshots_dir(self.current_project)
            else:
                base_dir = "screenshots"
                os.makedirs(base_dir, exist_ok=True)

            # 创建时间戳子目录
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(base_dir, timestamp)
            os.makedirs(output_dir, exist_ok=True)

            # 显示每个视频的容错帧数
            tolerance_info = ", ".join([f"{v.name}: {v.tolerance}" for v in selected_videos if v.tolerance > 0])
            if tolerance_info:
                self.log(f"开始截图，选中视频: {len(selected_videos)}/{len(self.videos)}，容错帧数: {tolerance_info}")
            else:
                self.log(f"开始截图，选中视频: {len(selected_videos)}/{len(self.videos)}")

            # 获取帧数区间
            frame_range_start = 0
            frame_range_end = 0
            if hasattr(self, 'frame_range_start_entry') and hasattr(self, 'frame_range_end_entry'):
                try:
                    frame_range_start = int(self.frame_range_start_entry.get())
                    frame_range_end = int(self.frame_range_end_entry.get())
                    if frame_range_start > 0 or frame_range_end > 0:
                        self.log(f"使用帧数区间: {frame_range_start} - {frame_range_end if frame_range_end > 0 else '结尾'}")
                except ValueError:
                    frame_range_start = 0
                    frame_range_end = 0

            # 调用截图函数（tolerance参数已废弃，使用video.tolerance）
            if frame_numbers is None:
                # 新建截图，生成随机帧数
                count = int(self.screenshot_count_entry.get())
                actual_frames = take_screenshots_enhanced_with_frames(
                    selected_videos, count, output_dir, self.log, 0, None,
                    frame_range_start, frame_range_end
                )

                # 保存到历史记录
                history_name = f"{timestamp} ({count}张)"
                self.screenshot_history.append({
                    'name': history_name,
                    'frames': actual_frames,
                    'timestamp': timestamp
                })
                self.update_history_combo()
                self.log(f"已保存帧数到历史: {history_name}")
            else:
                # 使用历史帧数
                take_screenshots_enhanced_with_frames(
                    selected_videos, len(frame_numbers), output_dir, self.log, 0, frame_numbers,
                    frame_range_start, frame_range_end
                )

            self.log(f"截图完成！保存在: {output_dir}")

            # 自动打开文件夹（不弹框）
            try:
                subprocess.Popen(f'explorer "{os.path.abspath(output_dir)}"')
                self.log("已自动打开截图文件夹")
            except Exception as e:
                self.log(f"打开文件夹失败: {e}")
        except Exception as e:
            self.log(f"截图失败: {e}")
            messagebox.showerror("错误", f"截图失败: {e}")

    def launch_vspreview(self, script_path: str):
        """启动VSPreview"""
        import subprocess

        # 检查是否存在旧的存储文件，如果有则自动删除
        script_dir = os.path.dirname(os.path.abspath(script_path))
        storage_dir = os.path.join(script_dir, '.vsjet', 'vspreview')

        if os.path.exists(storage_dir):
            try:
                # 查找并删除旧的 .yml 文件
                yml_files = [f for f in os.listdir(storage_dir) if f.endswith('.yml')]
                if yml_files:
                    # 创建备份目录
                    backup_dir = os.path.join(storage_dir, 'backup')
                    os.makedirs(backup_dir, exist_ok=True)

                    # 备份并删除 .yml 文件
                    for f in yml_files:
                        src = os.path.join(storage_dir, f)
                        dst = os.path.join(backup_dir, f)
                        shutil.copy2(src, dst)
                        os.remove(src)

                    self.log(f"已自动删除 {len(yml_files)} 个旧存储文件（已备份）")
            except Exception as e:
                self.log(f"删除旧存储文件失败: {e}")

        # 尝试直接调用 vspreview
        try:
            self.preview_process = subprocess.Popen(["vspreview", script_path])
            self.log(f"已启动 VSPreview: {script_path}")
        except FileNotFoundError:
            # 回退到 python -m vspreview
            try:
                self.preview_process = subprocess.Popen([sys.executable, "-m", "vspreview", script_path])
                self.log(f"已启动 VSPreview (python -m): {script_path}")
            except Exception as e:
                self.log(f"启动 VSPreview 失败: {e}")
                messagebox.showerror("错误",
                    f"无法启动 VSPreview。\n请确保已安装: pip install vspreview\n错误: {e}")

    def show_image_viewer(self, event=None):
        """显示图片查看器"""
        if self.reference_image_path and os.path.exists(self.reference_image_path):
            ImageViewerWindow(self, self.reference_image_path)
        else:
            messagebox.showinfo("提示", "请先上传参考图")


class BatchDeleteDialog(ctk.CTkToplevel):
    """批量删除对话框"""

    def __init__(self, parent, videos: List):
        super().__init__(parent)

        self.videos = videos
        self.deleted_indices = []
        self.checkboxes = []

        # 窗口配置
        self.title("批量删除视频")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        # 创建UI
        self.create_widgets()

        # 居中显示
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def create_widgets(self):
        """创建UI组件"""
        # 标题
        title = ctk.CTkLabel(self, text="选择要删除的视频", font=("Arial", 16, "bold"))
        title.pack(pady=15)

        # 视频列表
        list_frame = ctk.CTkScrollableFrame(self, height=250)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 添加复选框
        for i, video in enumerate(self.videos):
            var = ctk.IntVar()
            cb = ctk.CTkCheckBox(list_frame, text=f"{i+1}. {video.name}",
                                 variable=var, font=("Arial", 12))
            cb.pack(anchor="w", padx=10, pady=5)
            self.checkboxes.append((i, var))

        # 按钮区域
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=10)

        # 全选按钮
        select_all_btn = ctk.CTkButton(button_frame, text="全选",
                                        command=self.select_all, width=80)
        select_all_btn.pack(side="left", padx=5)

        # 取消全选按钮
        deselect_all_btn = ctk.CTkButton(button_frame, text="取消全选",
                                          command=self.deselect_all, width=80)
        deselect_all_btn.pack(side="left", padx=5)

        # 确认删除按钮
        delete_btn = ctk.CTkButton(button_frame, text="确认删除",
                                    command=self.confirm_delete,
                                    fg_color="#f44336", hover_color="#d32f2f", width=100)
        delete_btn.pack(side="right", padx=5)

        # 取消按钮
        cancel_btn = ctk.CTkButton(button_frame, text="取消",
                                    command=self.cancel, width=80)
        cancel_btn.pack(side="right", padx=5)

    def select_all(self):
        """全选"""
        for _, var in self.checkboxes:
            var.set(1)

    def deselect_all(self):
        """取消全选"""
        for _, var in self.checkboxes:
            var.set(0)

    def confirm_delete(self):
        """确认删除"""
        # 获取选中的索引
        self.deleted_indices = [idx for idx, var in self.checkboxes if var.get() == 1]

        if not self.deleted_indices:
            messagebox.showinfo("提示", "请至少选择一个视频")
            return

        # 确认
        if messagebox.askyesno("确认", f"确定要删除选中的 {len(self.deleted_indices)} 个视频吗？"):
            self.destroy()
        else:
            self.deleted_indices = []

    def cancel(self):
        """取消"""
        self.deleted_indices = []
        self.destroy()


class ProjectSelectorDialog(ctk.CTkToplevel):
    """项目选择对话框"""

    def __init__(self, parent, project_manager: ProjectManager):
        super().__init__(parent)

        self.project_manager = project_manager
        self.selected_project = None

        # 窗口配置
        self.title("选择项目")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        # 创建UI
        self.create_widgets()

        # 居中显示
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def create_widgets(self):
        """创建UI组件"""
        # 标题
        title = ctk.CTkLabel(self, text="项目管理", font=("Arial", 20, "bold"))
        title.pack(pady=20)

        # 项目列表
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 列表标题
        header_frame = ctk.CTkFrame(list_frame)
        header_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(header_frame, text="项目名称", width=200, font=("Arial", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="最后修改", width=150, font=("Arial", 12, "bold")).pack(side="left", padx=5)

        # 滚动列表
        self.project_scroll = ctk.CTkScrollableFrame(list_frame, height=200)
        self.project_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # 加载项目列表
        self.load_projects()

        # 按钮区域
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=10)

        new_btn = ctk.CTkButton(button_frame, text="新建项目", command=self.new_project,
                                fg_color="#4caf50", hover_color="#388e3c")
        new_btn.pack(side="left", padx=5)

        cancel_btn = ctk.CTkButton(button_frame, text="取消", command=self.cancel,
                                    fg_color="#f44336", hover_color="#d32f2f")
        cancel_btn.pack(side="right", padx=5)

    def load_projects(self):
        """加载项目列表"""
        # 清空现有列表
        for widget in self.project_scroll.winfo_children():
            widget.destroy()

        projects = self.project_manager.list_projects()

        if not projects:
            ctk.CTkLabel(self.project_scroll, text="暂无项目，请新建项目").pack(pady=20)
            return

        for project in projects:
            self.create_project_row(project)

    def create_project_row(self, project: Dict):
        """创建项目行"""
        row_frame = ctk.CTkFrame(self.project_scroll)
        row_frame.pack(fill="x", padx=5, pady=2)

        # 项目名称
        name_label = ctk.CTkLabel(row_frame, text=project['name'], width=200, anchor="w")
        name_label.pack(side="left", padx=5)

        # 修改时间
        time_label = ctk.CTkLabel(row_frame, text=project['modified'], width=150, anchor="w")
        time_label.pack(side="left", padx=5)

        # 选择按钮
        select_btn = ctk.CTkButton(row_frame, text="选择", width=80,
                                    command=lambda: self.select_project(project['name']))
        select_btn.pack(side="right", padx=5)

        # 删除按钮
        delete_btn = ctk.CTkButton(row_frame, text="删除", width=80,
                                    fg_color="#f44336", hover_color="#d32f2f",
                                    command=lambda: self.delete_project(project['name']))
        delete_btn.pack(side="right", padx=5)

    def new_project(self):
        """新建项目"""
        dialog = ctk.CTkInputDialog(text="请输入项目名称:", title="新建项目")
        project_name = dialog.get_input()

        if project_name:
            self.project_manager.create_project(project_name)
            self.load_projects()

    def select_project(self, project_name: str):
        """选择项目"""
        self.selected_project = project_name
        self.destroy()

    def delete_project(self, project_name: str):
        """删除项目"""
        # 询问是否删除项目
        response = messagebox.askyesnocancel(
            "确认删除",
            f"确定要删除项目 '{project_name}' 吗？\n\n"
            "选择操作：\n"
            "• 是(Y) - 删除项目配置和截图\n"
            "• 否(N) - 仅删除项目配置，保留截图\n"
            "• 取消 - 不删除"
        )

        if response is None:  # 取消
            return

        delete_screenshots = response  # True=删除截图，False=保留截图

        if self.project_manager.delete_project(project_name, delete_screenshots=delete_screenshots):
            if delete_screenshots:
                messagebox.showinfo("成功", "项目和截图已删除")
            else:
                messagebox.showinfo("成功", "项目已删除，截图已保留")
            self.load_projects()
        else:
            messagebox.showerror("错误", "删除项目失败")

    def cancel(self):
        """取消"""
        self.destroy()


class ImageViewerWindow(ctk.CTkToplevel):
    """图片查看器窗口"""

    def __init__(self, parent, image_path: str):
        super().__init__(parent)

        self.image_path = image_path
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0

        # 窗口配置
        self.title("图片查看器")
        self.geometry("800x600")

        # 置顶显示
        self.attributes('-topmost', True)
        self.lift()
        self.focus_force()

        # 加载图片
        self.original_image = Image.open(image_path)

        # 创建画布
        self.canvas = ctk.CTkCanvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # 绑定事件
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Configure>", self.on_resize)

        # 显示图片
        self.update_image()

        # 提示文本
        self.after(100, self.show_help)

    def show_help(self):
        """显示帮助信息"""
        help_text = "滚轮缩放 | 拖动移动 | ESC关闭"
        self.canvas.create_text(10, 10, text=help_text, anchor="nw",
                                fill="white", font=("Arial", 12))

    def update_image(self):
        """更新图片显示"""
        # 计算缩放后的尺寸
        width = int(self.original_image.width * self.scale)
        height = int(self.original_image.height * self.scale)

        # 缩放图片
        resized = self.original_image.resize((width, height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)

        # 清空画布
        self.canvas.delete("all")

        # 居中显示
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        x = canvas_width // 2 + self.offset_x
        y = canvas_height // 2 + self.offset_y

        self.canvas.create_image(x, y, image=self.photo, anchor="center")

        # 重新显示帮助
        self.show_help()

    def on_mousewheel(self, event):
        """鼠标滚轮缩放"""
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1

        # 限制缩放范围
        self.scale = max(0.1, min(self.scale, 10.0))

        self.update_image()

    def on_drag_start(self, event):
        """开始拖动"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_motion(self, event):
        """拖动移动"""
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        self.offset_x += dx
        self.offset_y += dy

        self.drag_start_x = event.x
        self.drag_start_y = event.y

        self.update_image()

    def on_resize(self, event):
        """窗口大小改变"""
        self.update_image()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="VSE Screenshot GUI")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--auto-start", choices=["preview", "align", "screenshot"],
                       help="自动执行操作")
    args = parser.parse_args()

    app = VSEScreenshotApp()

    # 如果指定了配置文件
    if args.config:
        app.config_path = args.config
        app.load_config()

    # 自动执行操作
    if args.auto_start:
        app.after(1000, lambda: auto_execute(app, args.auto_start))

    app.mainloop()


def auto_execute(app: VSEScreenshotApp, action: str):
    """自动执行操作"""
    if action == "preview":
        app.preview_videos()
    elif action == "align":
        app.align_videos()
    elif action == "screenshot":
        app.start_screenshot()


if __name__ == "__main__":
    main()

