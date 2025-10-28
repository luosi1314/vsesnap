#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
截图引擎模块
使用VapourSynth进行视频截图，支持YUV到RGB的正确转换
"""

import os
import random
from typing import List, Callable
from pathlib import Path

try:
    import vapoursynth as vs
    from vapoursynth import core
    HAS_VAPOURSYNTH = True
except ImportError:
    HAS_VAPOURSYNTH = False
    print("警告: VapourSynth 未安装")

try:
    from PIL import Image
    import numpy as np
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("警告: Pillow 未安装")


def take_screenshots(videos: List, count: int, output_dir: str, 
                     log_callback: Callable[[str], None] = None):
    """
    对多个视频进行截图
    
    Args:
        videos: 视频列表
        count: 截图数量
        output_dir: 输出目录
        log_callback: 日志回调函数
    """
    if not HAS_VAPOURSYNTH:
        raise ImportError("VapourSynth 未安装，无法进行截图")
    
    if not HAS_PIL:
        raise ImportError("Pillow 未安装，无法保存图片")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)
    
    # 为每个视频创建子目录
    for i, video in enumerate(videos):
        video_dir = os.path.join(output_dir, sanitize_filename(video.name))
        os.makedirs(video_dir, exist_ok=True)
        
        log(f"正在处理视频 {i+1}/{len(videos)}: {video.name}")
        
        try:
            # 加载视频
            clip = load_video_clip(video)
            
            # 获取视频信息
            total_frames = clip.num_frames
            log(f"  总帧数: {total_frames}")
            
            # 生成随机帧号
            frame_numbers = generate_frame_numbers(total_frames, count, video.offset)
            log(f"  截图帧号: {frame_numbers}")
            
            # 截图
            for j, frame_num in enumerate(frame_numbers):
                try:
                    # 调整帧号（应用偏移）
                    actual_frame = frame_num + video.offset
                    
                    if actual_frame >= total_frames:
                        log(f"  警告: 帧号 {actual_frame} 超出范围，跳过")
                        continue
                    
                    # 获取帧
                    frame = clip.get_frame(actual_frame)
                    
                    # 转换为RGB并保存
                    img = frame_to_image(frame)
                    
                    # 保存图片
                    filename = f"frame_{frame_num:06d}.png"
                    filepath = os.path.join(video_dir, filename)
                    img.save(filepath, "PNG")
                    
                    log(f"  已保存: {filename}")
                    
                except Exception as e:
                    log(f"  错误: 截图帧 {frame_num} 失败: {e}")
            
            log(f"视频 {video.name} 截图完成")
            
        except Exception as e:
            log(f"处理视频 {video.name} 失败: {e}")
    
    log(f"所有截图已完成，保存在: {output_dir}")


def load_video_clip(video, add_frameinfo=False, skip_fps_conversion=False):
    """
    加载视频片段

    Args:
        video: 视频对象
        add_frameinfo: 是否添加帧信息显示
        skip_fps_conversion: 是否跳过帧率转换（用于PAL转NTSC截图）

    Returns:
        VapourSynth clip
    """
    # 创建缓存目录
    import os
    cache_dir = os.path.join(os.getcwd(), '.cache')
    os.makedirs(cache_dir, exist_ok=True)

    # 加载视频，指定缓存目录（根据可用插件选择）
    try:
        if hasattr(core, 'lsmas'):
            clip = core.lsmas.LWLibavSource(video.filepath, cachedir=cache_dir)
        elif hasattr(core, 'bs'):
            clip = core.bs.VideoSource(source=video.filepath)
        elif hasattr(core, 'ffms2'):
            clip = core.ffms2.Source(video.filepath)
        else:
            raise RuntimeError('未找到视频源插件: 需要 LSMASHSource/BestSource/FFMS2')
    except Exception as e:
        print(f"错误: 加载视频源失败: {e}")
        raise

    # 保存原始clip用于FrameInfo
    original_clip = clip

    # 应用QTGMC去隔行
    if video.use_qtgmc:
        try:
            import havsfunc as haf
            clip = haf.QTGMC(clip, Preset="Slower", TFF=True, FPSDivisor=2)
        except ImportError:
            print("警告: havsfunc 未安装，无法应用QTGMC")

    # 应用帧率转换（除非跳过）
    if not skip_fps_conversion:
        clip = apply_fps_conversion(clip, video.fps_type)

    # 添加帧信息（在转换为RGB之前）
    if add_frameinfo:
        try:
            import awsmfunc as awf
            # 显示版本名和原始帧号
            clip = awf.FrameInfo(clip, video.name)
        except ImportError:
            print("警告: awsmfunc 未安装，无法添加帧信息")

    # 确保是RGB格式（用于截图）
    if clip.format.color_family != vs.RGB:
        clip = core.resize.Bicubic(clip, format=vs.RGB24, matrix_in_s="709")

    return clip


def apply_fps_conversion(clip, fps_type: str):
    """
    应用帧率转换
    
    Args:
        clip: VapourSynth clip
        fps_type: 帧率类型
        
    Returns:
        转换后的clip
    """
    if fps_type == "PAL插帧到NTSC":
        # 29.97 -> 25 使用 SelectEvery
        clip = core.std.SelectEvery(clip, cycle=5, offsets=[0, 1, 2, 3])
    elif fps_type == "NTSC减帧到PAL":
        # 25 -> 29.97 使用 FlowFPS
        try:
            clip = core.mv.FlowFPS(clip, num=30000, den=1001)
        except:
            print("警告: mvtools 未安装，无法应用FlowFPS")
    elif fps_type == "PAL 5重1" or fps_type == "PAL 6重2":
        # 去重
        try:
            import havsfunc as haf
            clip = core.vivtc.VDecimate(clip)
        except:
            print("警告: VIVTC 未安装，无法去重")
    
    return clip


def frame_to_image(frame):
    """
    将VapourSynth帧转换为PIL Image

    Args:
        frame: VapourSynth frame

    Returns:
        PIL Image
    """
    # 获取帧数据
    width = frame.width
    height = frame.height

    # 读取RGB平面 - 使用正确的API
    # VapourSynth R65+ 使用 frame[plane] 访问平面数据
    r_plane = np.asarray(frame[0])
    g_plane = np.asarray(frame[1])
    b_plane = np.asarray(frame[2])

    # 合并为RGB图像
    rgb_array = np.stack([r_plane, g_plane, b_plane], axis=2)

    # 创建PIL图像
    img = Image.fromarray(rgb_array, mode='RGB')

    return img


def generate_frame_numbers(total_frames: int, count: int, offset: int = 0) -> List[int]:
    """
    生成截图帧号列表
    
    Args:
        total_frames: 总帧数
        count: 截图数量
        offset: 偏移量
        
    Returns:
        帧号列表
    """
    # 可用帧范围
    available_frames = total_frames - offset
    
    if available_frames <= 0:
        return []
    
    if count >= available_frames:
        # 如果截图数量大于可用帧数，返回所有帧
        return list(range(available_frames))
    
    # 随机生成帧号
    frame_numbers = sorted(random.sample(range(available_frames), count))
    
    return frame_numbers


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符和扩展名

    Args:
        filename: 原始文件名

    Returns:
        清理后的文件名（不含扩展名）
    """
    # 移除扩展名
    name_without_ext = os.path.splitext(filename)[0]

    # 移除或替换非法字符
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        name_without_ext = name_without_ext.replace(char, '_')

    return name_without_ext


def take_specific_screenshots(videos: List, frame_numbers: List[int], 
                              output_dir: str, log_callback: Callable[[str], None] = None):
    """
    对指定帧号进行截图
    
    Args:
        videos: 视频列表
        frame_numbers: 指定的帧号列表
        output_dir: 输出目录
        log_callback: 日志回调函数
    """
    if not HAS_VAPOURSYNTH:
        raise ImportError("VapourSynth 未安装，无法进行截图")
    
    if not HAS_PIL:
        raise ImportError("Pillow 未安装，无法保存图片")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)
    
    # 为每个视频创建子目录
    for i, video in enumerate(videos):
        video_dir = os.path.join(output_dir, sanitize_filename(video.name))
        os.makedirs(video_dir, exist_ok=True)
        
        log(f"正在处理视频 {i+1}/{len(videos)}: {video.name}")
        
        try:
            # 加载视频
            clip = load_video_clip(video)
            
            # 获取视频信息
            total_frames = clip.num_frames
            log(f"  总帧数: {total_frames}")
            
            # 截图
            for frame_num in frame_numbers:
                try:
                    # 调整帧号（应用偏移）
                    actual_frame = frame_num + video.offset
                    
                    if actual_frame >= total_frames:
                        log(f"  警告: 帧号 {actual_frame} 超出范围，跳过")
                        continue
                    
                    # 获取帧
                    frame = clip.get_frame(actual_frame)
                    
                    # 转换为RGB并保存
                    img = frame_to_image(frame)
                    
                    # 保存图片
                    filename = f"frame_{frame_num:06d}.png"
                    filepath = os.path.join(video_dir, filename)
                    img.save(filepath, "PNG")
                    
                    log(f"  已保存: {filename}")
                    
                except Exception as e:
                    log(f"  错误: 截图帧 {frame_num} 失败: {e}")
            
            log(f"视频 {video.name} 截图完成")
            
        except Exception as e:
            log(f"处理视频 {video.name} 失败: {e}")
    
    log(f"所有截图已完成，保存在: {output_dir}")


def take_screenshots_enhanced(videos: List, count: int, output_dir: str,
                              log_callback: Callable[[str], None] = None,
                              tolerance_frames: int = 3):
    """
    增强版截图函数 - 使用新的文件命名格式
    文件命名: {对齐后帧数}_{对齐前帧数}_{版本名}.png

    对于PAL插帧到NTSC格式，会按照29.97/25的比例计算对应帧，并截取前后容错帧

    Args:
        videos: 视频列表
        count: 截图数量
        output_dir: 输出目录
        log_callback: 日志回调函数
        tolerance_frames: 容错帧数（前后各N帧）
    """
    if not HAS_VAPOURSYNTH:
        raise ImportError("VapourSynth 未安装，无法进行截图")

    if not HAS_PIL:
        raise ImportError("Pillow 未安装，无法保存图片")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    # 生成随机帧号（基于第一个视频）
    if not videos:
        log("错误: 没有视频")
        return

    # 加载第一个视频获取总帧数
    first_video = videos[0]
    try:
        clip = load_video_clip(first_video)
        total_frames = clip.num_frames
        log(f"参考视频总帧数: {total_frames}")
    except Exception as e:
        log(f"加载参考视频失败: {e}")
        return

    # 生成随机帧号（对齐后的帧号）
    frame_numbers = generate_frame_numbers(total_frames, count, 0)
    log(f"生成 {len(frame_numbers)} 个随机帧号")

    # 为每个视频截图
    for i, video in enumerate(videos):
        log(f"正在处理视频 {i+1}/{len(videos)}: {video.name}")

        try:
            # 检查是否是PAL插帧到NTSC格式
            is_pal_to_ntsc = video.fps_type == "PAL插帧到NTSC"

            # 加载视频（PAL转NTSC跳过帧率转换）
            clip = load_video_clip(video, add_frameinfo=True, skip_fps_conversion=is_pal_to_ntsc)
            video_total_frames = clip.num_frames
            log(f"  总帧数: {video_total_frames}")

            if is_pal_to_ntsc:
                log(f"  检测到PAL插帧到NTSC格式，使用公式: 对齐帧数 * 29.97/25 + 偏移量")

            # 截图
            screenshot_count = 0
            for aligned_frame in frame_numbers:
                try:
                    if is_pal_to_ntsc:
                        # PAL插帧到NTSC: 对齐帧数 * 29.97/25 + 偏移量
                        # 例如: 52986 * 29.97/25 + 332 = 63851
                        ratio = 29.97 / 25.0
                        calculated_frame = int(aligned_frame * ratio)
                        base_frame = calculated_frame + video.offset

                        # 截取前后容错帧
                        frames_to_capture = []
                        for offset in range(-tolerance_frames, tolerance_frames + 1):
                            frame_num = base_frame + offset
                            if 0 <= frame_num < video_total_frames:
                                frames_to_capture.append(frame_num)

                        log(f"  对齐帧 {aligned_frame} * {ratio:.4f} + {video.offset} = {base_frame} (容错: {frames_to_capture[0]}-{frames_to_capture[-1]})")

                        # 截取所有容错帧
                        for original_frame in frames_to_capture:
                            # 获取帧
                            frame = clip.get_frame(original_frame)

                            # 转换为图片
                            img = frame_to_image(frame)

                            # 生成文件名: {对齐后帧数}_{实际帧数}_{版本名}.png
                            safe_name = sanitize_filename(video.name)
                            filename = f"{aligned_frame:06d}_{original_frame:06d}_{safe_name}.png"
                            filepath = os.path.join(output_dir, filename)

                            # 保存图片
                            img.save(filepath)
                            screenshot_count += 1
                    else:
                        # 普通格式: 使用偏移量对齐
                        original_frame = aligned_frame + video.offset

                        if original_frame >= video_total_frames:
                            log(f"  警告: 帧号 {original_frame} 超出范围，跳过")
                            continue

                        # 获取帧
                        frame = clip.get_frame(original_frame)

                        # 转换为图片
                        img = frame_to_image(frame)

                        # 生成文件名: {对齐后帧数}_{对齐前帧数}_{版本名}.png
                        safe_name = sanitize_filename(video.name)
                        filename = f"{aligned_frame:06d}_{original_frame:06d}_{safe_name}.png"
                        filepath = os.path.join(output_dir, filename)

                        # 保存图片
                        img.save(filepath)
                        screenshot_count += 1

                except Exception as e:
                    log(f"  截图失败 (帧 {aligned_frame}): {e}")
                    continue

            log(f"  截图完成: {screenshot_count} 张")

        except Exception as e:
            log(f"  处理视频失败: {e}")
            continue

    log(f"所有截图完成！保存在: {output_dir}")


def parse_screenshot_fps(screenshot_fps: str) -> float:
    """
    解析截图帧率字符串

    Args:
        screenshot_fps: 截图帧率字符串（纯数字，如 "25.00", "29.97"）

    Returns:
        float: 帧率值
    """
    try:
        return float(screenshot_fps)
    except (ValueError, TypeError):
        # 如果转换失败，尝试提取数字（兼容旧格式）
        import re
        match = re.search(r'(\d+\.?\d*)', str(screenshot_fps))
        if match:
            return float(match.group(1))
        return 25.0  # 默认25帧


def calculate_frame_ratio(screenshot_fps: str, reference_fps: float = 25.0) -> float:
    """
    计算帧率转换比例

    Args:
        screenshot_fps: 截图帧率字符串
        reference_fps: 参考帧率（默认25）

    Returns:
        float: 转换比例
    """
    target_fps = parse_screenshot_fps(screenshot_fps)
    return target_fps / reference_fps


def take_screenshots_enhanced_with_frames(videos: List, count: int, output_dir: str,
                                          log_callback: Callable[[str], None] = None,
                                          tolerance_frames: int = 3,
                                          frame_numbers: List[int] = None,
                                          frame_range_start: int = 0,
                                          frame_range_end: int = 0):
    """
    增强版截图函数 - 支持指定帧数或生成新帧数

    Args:
        videos: 视频列表
        count: 截图数量（仅在frame_numbers为None时使用）
        output_dir: 输出目录
        log_callback: 日志回调函数
        tolerance_frames: 容错帧数（前后各N帧，已废弃，使用video.tolerance）
        frame_numbers: 指定的帧号列表，如果为None则生成新的随机帧号
        frame_range_start: 随机帧数区间起始（0表示从头开始）
        frame_range_end: 随机帧数区间结束（0表示到结尾）

    Returns:
        实际使用的帧号列表
    """
    if not HAS_VAPOURSYNTH:
        raise ImportError("VapourSynth 未安装，无法进行截图")

    if not HAS_PIL:
        raise ImportError("Pillow 未安装，无法保存图片")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    # 生成或使用指定的帧号
    if frame_numbers is None:
        # 生成随机帧号（基于第一个视频）
        if not videos:
            log("错误: 没有视频")
            return []

        # 加载第一个视频获取总帧数
        first_video = videos[0]
        try:
            clip = load_video_clip(first_video)
            total_frames = clip.num_frames
            log(f"参考视频总帧数: {total_frames}")
        except Exception as e:
            log(f"加载参考视频失败: {e}")
            return []

        # 确定帧数区间
        start_frame = max(0, frame_range_start)
        end_frame = frame_range_end if frame_range_end > 0 else total_frames
        end_frame = min(end_frame, total_frames)

        if start_frame >= end_frame:
            log(f"错误: 帧数区间无效 ({start_frame} >= {end_frame})")
            return []

        available_frames = end_frame - start_frame
        if count > available_frames:
            log(f"警告: 截图数量 ({count}) 超过可用帧数 ({available_frames})，调整为 {available_frames}")
            count = available_frames

        # 生成随机帧号（在指定区间内）
        frame_numbers = sorted(random.sample(range(start_frame, end_frame), count))
        log(f"在区间 [{start_frame}, {end_frame}) 生成 {len(frame_numbers)} 个随机帧号")
    else:
        log(f"使用指定的 {len(frame_numbers)} 个帧号")

    # 为每个视频截图
    for i, video in enumerate(videos):
        log(f"正在处理视频 {i+1}/{len(videos)}: {video.name}")

        try:
            # 加载视频
            clip = load_video_clip(video, add_frameinfo=True, skip_fps_conversion=True)
            video_total_frames = clip.num_frames

            # 获取视频实际帧率
            # 优先使用 video.video_fps（用户设置），否则从视频文件检测
            if hasattr(video, 'video_fps') and video.video_fps:
                try:
                    video_fps = float(video.video_fps)
                    log(f"  使用用户设置的视频帧率: {video_fps:.3f} fps")
                except:
                    video_fps = clip.fps_num / clip.fps_den
                    log(f"  从视频文件检测帧率: {video_fps:.3f} fps")
            else:
                video_fps = clip.fps_num / clip.fps_den
                log(f"  从视频文件检测帧率: {video_fps:.3f} fps")

            # 获取截图帧率设置（对齐帧数基于此帧率）
            screenshot_fps_str = getattr(video, 'screenshot_fps', '25.00')
            screenshot_fps = parse_screenshot_fps(screenshot_fps_str)

            # 计算帧率转换比例：视频实际帧率 / 截图帧率
            ratio = video_fps / screenshot_fps

            # 检查是否需要帧率转换
            need_fps_conversion = abs(ratio - 1.0) > 0.01

            # 获取扫描方式信息
            scan_type = getattr(video, 'scan_type', '未知')

            log(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            log(f"  视频信息:")
            log(f"    总帧数:     {video_total_frames}")
            log(f"    视频帧率:   {video_fps:.3f} fps")
            log(f"    扫描方式:   {scan_type}")
            log(f"  截图设置:")
            log(f"    截图帧率:   {screenshot_fps:.3f} fps (基准帧率)")
            log(f"    偏移量:     {video.offset}")
            log(f"  计算参数:")
            log(f"    转换比例:   {ratio:.6f} (= {video_fps:.3f} / {screenshot_fps:.3f})")
            if need_fps_conversion:
                log(f"    需要转换:   是")
            else:
                log(f"    需要转换:   否 (视频帧率与截图帧率相同)")
            log(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            # 获取该视频的容错帧数
            video_tolerance = getattr(video, 'tolerance', 0)
            if video_tolerance > 0:
                log(f"  容错帧数: {video_tolerance}")

            # 截图
            screenshot_count = 0
            for aligned_frame in frame_numbers:
                try:
                    if need_fps_conversion:
                        # 需要帧率转换: 对齐帧数 * 比例 + 偏移量
                        calculated_frame = int(aligned_frame * ratio)
                        base_frame = calculated_frame + video.offset

                        # 截取前后容错帧
                        frames_to_capture = []
                        for offset in range(-video_tolerance, video_tolerance + 1):
                            frame_num = base_frame + offset
                            if 0 <= frame_num < video_total_frames:
                                frames_to_capture.append(frame_num)

                        # 详细的计算过程输出
                        log(f"  ")
                        log(f"  对齐帧 {aligned_frame:06d} 的计算过程:")
                        log(f"    公式: 实际帧数 = int(对齐帧数 × 比例) + 偏移量")
                        log(f"    计算: 实际帧数 = int({aligned_frame} × {ratio:.6f}) + {video.offset}")
                        log(f"         换算帧数 = int({aligned_frame * ratio:.2f}) = {calculated_frame}")
                        log(f"         实际帧数 = {calculated_frame} + {video.offset} = {base_frame}")
                        if video_tolerance > 0:
                            log(f"    容错范围: {frames_to_capture[0]} - {frames_to_capture[-1]} (±{video_tolerance} 帧)")
                            log(f"    截取帧数: {len(frames_to_capture)} 帧")

                        # 截取所有容错帧
                        for original_frame in frames_to_capture:
                            # 获取帧
                            frame = clip.get_frame(original_frame)

                            # 转换为图片
                            img = frame_to_image(frame)

                            # 生成文件名: {对齐后帧数}_{实际帧数}_{版本名}.png
                            safe_name = sanitize_filename(video.name)
                            filename = f"{aligned_frame:06d}_{original_frame:06d}_{safe_name}.png"
                            filepath = os.path.join(output_dir, filename)

                            # 保存图片
                            img.save(filepath)
                            screenshot_count += 1
                    else:
                        # 不需要帧率转换: 使用偏移量对齐
                        base_frame = aligned_frame + video.offset

                        # 截取前后容错帧
                        frames_to_capture = []
                        for offset in range(-video_tolerance, video_tolerance + 1):
                            frame_num = base_frame + offset
                            if 0 <= frame_num < video_total_frames:
                                frames_to_capture.append(frame_num)

                        # 详细的计算过程输出
                        log(f"  ")
                        log(f"  对齐帧 {aligned_frame:06d} 的计算过程:")
                        log(f"    公式: 实际帧数 = 对齐帧数 + 偏移量 (无需转换)")
                        log(f"    计算: 实际帧数 = {aligned_frame} + {video.offset} = {base_frame}")
                        if video_tolerance > 0:
                            log(f"    容错范围: {frames_to_capture[0]} - {frames_to_capture[-1]} (±{video_tolerance} 帧)")
                            log(f"    截取帧数: {len(frames_to_capture)} 帧")

                        # 截取所有容错帧
                        for original_frame in frames_to_capture:
                            if original_frame >= video_total_frames:
                                log(f"  警告: 帧号 {original_frame} 超出范围，跳过")
                                continue

                            # 获取帧
                            frame = clip.get_frame(original_frame)

                            # 转换为图片
                            img = frame_to_image(frame)

                            # 生成文件名: {对齐后帧数}_{实际帧数}_{版本名}.png
                            safe_name = sanitize_filename(video.name)
                            filename = f"{aligned_frame:06d}_{original_frame:06d}_{safe_name}.png"
                            filepath = os.path.join(output_dir, filename)

                            # 保存图片
                            img.save(filepath)
                            screenshot_count += 1

                except Exception as e:
                    log(f"  截图失败 (帧 {aligned_frame}): {e}")
                    continue

            log(f"  截图完成: {screenshot_count} 张")

        except Exception as e:
            log(f"  处理视频失败: {e}")
            continue

    log(f"所有截图完成！保存在: {output_dir}")

    return frame_numbers


if __name__ == "__main__":
    print("截图引擎模块已加载")

