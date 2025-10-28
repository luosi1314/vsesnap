#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VPY脚本生成模块
用于生成预览、对齐、截图的VapourSynth脚本
"""

import os
from typing import List


def apply_alignment_mode(var_name: str, video, script_lines: List[str]):
    """
    应用帧率对齐方式

    Args:
        var_name: 变量名
        video: 视频对象
        script_lines: 脚本行列表（会被修改）
    """
    alignment_mode = getattr(video, 'alignment_mode', '不对齐')

    if alignment_mode == "不对齐":
        # 不做任何处理
        pass

    elif alignment_mode == "减帧对齐":
        # 使用 VDecimate 去除重复帧
        script_lines.append(f"# 减帧对齐：使用 VDecimate 去除重复帧")
        script_lines.append(f"try:")
        script_lines.append(f"    {var_name} = core.vivtc.VDecimate({var_name})")
        script_lines.append(f"except:")
        script_lines.append(f"    print('警告: VIVTC 未安装，无法应用减帧对齐')")

    elif alignment_mode == "重复帧对齐":
        # 重复帧以匹配目标帧率（例如 25fps -> 30fps）
        script_lines.append(f"# 重复帧对齐：25fps -> 30fps")
        script_lines.append(f"{var_name} = core.std.AssumeFPS({var_name}, fpsnum=30000, fpsden=1001)")

    elif alignment_mode == "反胶卷过带":
        # 使用 VIVTC 反胶卷过带（3:2 pulldown）
        script_lines.append(f"# 反胶卷过带：使用 VIVTC 处理 3:2 pulldown")
        script_lines.append(f"try:")
        script_lines.append(f"    {var_name} = core.vivtc.VFM({var_name}, order=1)")
        script_lines.append(f"    {var_name} = core.vivtc.VDecimate({var_name})")
        script_lines.append(f"except:")
        script_lines.append(f"    print('警告: VIVTC 未安装，无法应用反胶卷过带')")

    elif alignment_mode == "速度调整":
        # 使用 AssumeFPS 调整速度（不插值）
        script_lines.append(f"# 速度调整：直接改变帧率（不插值）")
        script_lines.append(f"{var_name} = core.std.AssumeFPS({var_name}, fpsnum=25, fpsden=1)")

    elif alignment_mode == "插值对齐":
        # 使用 MVTools 插值
        script_lines.append(f"# 插值对齐：使用 MVTools 进行帧率转换")
        script_lines.append(f"try:")
        script_lines.append(f"    super_clip = core.mv.Super({var_name}, pel=2)")
        script_lines.append(f"    backward = core.mv.Analyse(super_clip, isb=True, blksize=16, overlap=8)")
        script_lines.append(f"    forward = core.mv.Analyse(super_clip, isb=False, blksize=16, overlap=8)")
        script_lines.append(f"    {var_name} = core.mv.FlowFPS({var_name}, super_clip, backward, forward, num=30000, den=1001)")
        script_lines.append(f"except:")
        script_lines.append(f"    print('警告: MVTools 未安装，无法应用插值对齐')")


def generate_preview_script(videos: List, output_path: str = "preview.vpy"):
    """
    生成预览脚本（偏移量为0）

    Args:
        videos: 视频列表
        output_path: 输出脚本路径
    """
    # 是否需要 QTGMC（仅当至少一个视频勾选时才尝试导入 havsfunc）
    needs_qtgmc = any(getattr(v, 'use_qtgmc', False) for v in videos)

    script_lines = [
        "import vapoursynth as vs",
        "core = vs.core",
        "import os",
        "",
        "# 预览脚本 - 偏移量为0",
        "",
        "# 设置缓存目录",
        "cache_dir = os.path.join(os.getcwd(), '.cache')",
        "os.makedirs(cache_dir, exist_ok=True)",
        ""
    ]

    # 可选导入 havsfunc
    if needs_qtgmc:
        script_lines.append("try:")
        script_lines.append("    import havsfunc as haf")
        script_lines.append("    HAF_AVAILABLE = True")
        script_lines.append("except ImportError:")
        script_lines.append("    HAF_AVAILABLE = False")
        script_lines.append("    print('警告: havsfunc 未安装，QTGMC 将被跳过')")
        script_lines.append("")
    else:
        script_lines.append("HAF_AVAILABLE = False")
        script_lines.append("")
    
    # 尝试导入 awsmfunc
    script_lines.append("try:")
    script_lines.append("    import awsmfunc as awf")
    script_lines.append("    HAS_AWSMFUNC = True")
    script_lines.append("except ImportError:")
    script_lines.append("    HAS_AWSMFUNC = False")
    script_lines.append("    print('警告: awsmfunc 未安装，将不显示帧信息')")
    script_lines.append("")

    # 检测可用的视频源插件，并提供统一的加载函数
    script_lines.append("HAS_LSMASH = hasattr(core, 'lsmas')")
    script_lines.append("HAS_BS = hasattr(core, 'bs')")
    script_lines.append("HAS_FFMS2 = hasattr(core, 'ffms2')")
    script_lines.append("def load_source(path):")
    script_lines.append("    if HAS_LSMASH:")
    script_lines.append("        return core.lsmas.LWLibavSource(path, cachedir=cache_dir)")
    script_lines.append("    elif HAS_BS:")
    script_lines.append("        return core.bs.VideoSource(source=path)")
    script_lines.append("    elif HAS_FFMS2:")
    script_lines.append("        return core.ffms2.Source(path)")
    script_lines.append("    else:")
    script_lines.append("        raise RuntimeError('未找到视频源插件: 需要 LSMASHSource/BestSource/FFMS2')")
    script_lines.append("")
    
    # 生成每个视频的加载代码
    var_names = []
    for i, video in enumerate(videos):
        # 使用安全的变量名（基于版本名）
        safe_name = ''.join(c if c.isalnum() or c in '_' else '_' for c in video.name)
        safe_name = safe_name.strip('_')  # 移除首尾下划线
        if not safe_name or safe_name[0].isdigit():  # 如果为空或以数字开头
            safe_name = f"video_{i}"
        var_name = safe_name
        var_names.append(var_name)

        filepath = video.filepath.replace("\\", "\\\\")

        script_lines.append(f"# {video.name} - {video.fps_type}")
        script_lines.append(f'{var_name} = load_source(r"{filepath}")')

        # 应用QTGMC（仅在 havsfunc 可用时）
        if video.use_qtgmc:
            tff_value = "True" if getattr(video, 'qtgmc_tff', True) else "False"
            script_lines.append("if HAF_AVAILABLE:")
            script_lines.append(f"    {var_name} = haf.QTGMC({var_name}, Preset=\"Slower\", TFF={tff_value}, FPSDivisor=2)")
            script_lines.append("else:")
            script_lines.append("    print('警告: havsfunc 未安装，跳过 QTGMC')")

        # 应用帧率对齐
        apply_alignment_mode(var_name, video, script_lines)

        # 添加帧信息
        script_lines.append(f"if HAS_AWSMFUNC:")
        script_lines.append(f"    {var_name} = awf.FrameInfo({var_name}, '{video.name}')")

        script_lines.append("")

    # 设置输出
    for i, (var_name, video) in enumerate(zip(var_names, videos)):
        script_lines.append(f"{var_name}.set_output({i})")

    script_lines.append("")

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(script_lines))

    # 生成 VSPreview 配置文件
    generate_vspreview_config(videos, output_path)

    return output_path


def generate_align_script(videos: List, output_path: str = "align.vpy"):
    """
    生成对齐脚本（应用偏移量）

    Args:
        videos: 视频列表
        output_path: 输出脚本路径
    """
    script_lines = [
        "import vapoursynth as vs",
        "core = vs.core",
        "import havsfunc as haf",
        "import os",
        "",
        "# 对齐脚本 - 应用偏移量",
        "",
        "# 设置缓存目录",
        "cache_dir = os.path.join(os.getcwd(), '.cache')",
        "os.makedirs(cache_dir, exist_ok=True)",
        ""
    ]
    
    # 尝试导入 awsmfunc
    script_lines.append("try:")
    script_lines.append("    import awsmfunc as awf")
    script_lines.append("    HAS_AWSMFUNC = True")
    script_lines.append("except ImportError:")
    script_lines.append("    HAS_AWSMFUNC = False")
    script_lines.append("    print('警告: awsmfunc 未安装，将不显示帧信息')")
    script_lines.append("")
    
    # 帧率情况说明
    script_lines.append("# 帧率情况说明：")
    for video in videos:
        script_lines.append(f"# - {video.name}: {video.fps_type}")
    script_lines.append("")
    
    # 生成每个视频的加载代码
    var_names = []
    for i, video in enumerate(videos):
        # 使用安全的变量名（基于版本名）
        safe_name = ''.join(c if c.isalnum() or c in '_' else '_' for c in video.name)
        safe_name = safe_name.strip('_')
        if not safe_name or safe_name[0].isdigit():
            safe_name = f"video_{i}"
        var_name = safe_name
        var_names.append(var_name)

        filepath = video.filepath.replace("\\", "\\\\")

        script_lines.append(f"# {video.name} - {video.fps_type}")
        script_lines.append(f'{var_name} = core.lsmas.LWLibavSource(r"{filepath}", cachedir=cache_dir)')

        # 应用QTGMC
        if video.use_qtgmc:
            tff_value = "True" if getattr(video, 'qtgmc_tff', True) else "False"
            script_lines.append(f'{var_name} = haf.QTGMC({var_name}, Preset="Slower", TFF={tff_value}, FPSDivisor=2)')

        # 应用帧率对齐
        apply_alignment_mode(var_name, video, script_lines)

        # 应用帧率转换（如果需要，保留用于兼容性）
        fps_conversion = get_fps_conversion(video.fps_type)
        if fps_conversion:
            script_lines.append(fps_conversion.format(var=var_name))

        # 添加帧信息
        script_lines.append(f"if HAS_AWSMFUNC:")
        script_lines.append(f"    {var_name} = awf.FrameInfo({var_name}, '{video.name}')")

        script_lines.append("")

    # 设置输出（应用偏移）
    for i, (video, var_name) in enumerate(zip(videos, var_names)):
        offset = video.offset

        if offset > 0:
            script_lines.append(f"{var_name}[{offset}:].set_output({i})")
        else:
            script_lines.append(f"{var_name}.set_output({i})")

    script_lines.append("")

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(script_lines))

    # 生成 VSPreview 配置文件
    generate_vspreview_config(videos, output_path)

    return output_path


def generate_screenshot_script(videos: List, frame_numbers: List[int],
                               output_path: str = "screenshot.vpy"):
    """
    生成截图脚本

    Args:
        videos: 视频列表
        frame_numbers: 要截图的帧号列表
        output_path: 输出脚本路径
    """
    # 是否需要 QTGMC（仅当至少一个视频勾选时才尝试导入 havsfunc）
    needs_qtgmc = any(getattr(v, 'use_qtgmc', False) for v in videos)

    script_lines = [
        "import vapoursynth as vs",
        "core = vs.core",
        "import os",
        "",
        "# 截图脚本",
        f"# 截图帧号: {frame_numbers}",
        "",
        "# 设置缓存目录",
        "cache_dir = os.path.join(os.getcwd(), '.cache')",
        "os.makedirs(cache_dir, exist_ok=True)",
        ""
    ]

    if needs_qtgmc:
        script_lines.append("try:")
        script_lines.append("    import havsfunc as haf")
        script_lines.append("    HAF_AVAILABLE = True")
        script_lines.append("except ImportError:")
        script_lines.append("    HAF_AVAILABLE = False")
        script_lines.append("    print('警告: havsfunc 未安装，QTGMC 将被跳过')")
        script_lines.append("")
    else:
        script_lines.append("HAF_AVAILABLE = False")
        script_lines.append("")

    # 生成每个视频的加载代码
    var_names = []
    for i, video in enumerate(videos):
        # 使用安全的变量名（基于版本名）
        safe_name = ''.join(c if c.isalnum() or c in '_' else '_' for c in video.name)
        safe_name = safe_name.strip('_')
        if not safe_name or safe_name[0].isdigit():
            safe_name = f"video_{i}"
        var_name = safe_name
        var_names.append(var_name)

        filepath = video.filepath.replace("\\", "\\\\")

        script_lines.append(f"# {video.name} - {video.fps_type}")
        script_lines.append(f'{var_name} = load_source(r"{filepath}")')

        # 应用QTGMC（仅在 havsfunc 可用时）
        if video.use_qtgmc:
            tff_value = "True" if getattr(video, 'qtgmc_tff', True) else "False"
            script_lines.append("if HAF_AVAILABLE:")
            script_lines.append(f"    {var_name} = haf.QTGMC({var_name}, Preset=\"Slower\", TFF={tff_value}, FPSDivisor=2)")
            script_lines.append("else:")
            script_lines.append("    print('警告: havsfunc 未安装，跳过 QTGMC')")

        # 应用帧率对齐
        apply_alignment_mode(var_name, video, script_lines)

        # 应用帧率转换（如果需要，保留用于兼容性）
        fps_conversion = get_fps_conversion(video.fps_type)
        if fps_conversion:
            script_lines.append(fps_conversion.format(var=var_name))

        script_lines.append("")

    # 设置输出（应用偏移）
    for i, (video, var_name) in enumerate(zip(videos, var_names)):
        offset = video.offset

        if offset > 0:
            script_lines.append(f"{var_name}_aligned = {var_name}[{offset}:]")
        else:
            script_lines.append(f"{var_name}_aligned = {var_name}")
        
        script_lines.append(f"{var_name}_aligned.set_output({i})")
    
    script_lines.append("")
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(script_lines))
    
    return output_path


def get_fps_conversion(fps_type: str) -> str:
    """
    获取帧率转换代码
    
    Args:
        fps_type: 帧率类型
        
    Returns:
        转换代码字符串，如果不需要转换则返回空字符串
    """
    conversions = {
        "原生PAL (25fps)": "",
        "原生NTSC (29.97fps)": "",
        "PAL插帧到NTSC": "{var} = core.std.SelectEvery({var}, cycle=5, offsets=[0, 1, 2, 3])  # 29.97->25",
        "NTSC减帧到PAL": "{var} = core.mv.FlowFPS({var}, num=30000, den=1001)  # 25->29.97",
        "PAL 5重1": "{var} = core.vivtc.VDecimate({var})  # 去除5重1",
        "PAL 6重2": "{var} = core.vivtc.VDecimate({var})  # 去除6重2"
    }
    
    return conversions.get(fps_type, "")


def calculate_native_frame(align_frame: int, fps_type: str) -> int:
    """
    根据帧率类型计算原生帧号
    
    Args:
        align_frame: 对齐帧号
        fps_type: 帧率类型
        
    Returns:
        原生帧号
    """
    if fps_type == "原生PAL (25fps)" or fps_type == "原生NTSC (29.97fps)":
        return align_frame
    elif fps_type == "PAL插帧到NTSC":
        # 29.97/25 比例
        return int(align_frame * 29.97 / 25)
    elif fps_type == "NTSC减帧到PAL":
        # 原生 = 对齐 × 5/6
        return int(align_frame * 5 / 6)
    elif fps_type == "PAL 5重1":
        # 原生 = 对齐 × 25/24
        return int(align_frame * 25 / 24)
    elif fps_type == "PAL 6重2":
        # 原生 = 对齐 × 25/23.976
        return int(align_frame * 25 / 23.976)
    else:
        return align_frame


def generate_vspreview_config(videos: List, vpy_path: str):
    """
    生成 VSPreview 配置文件，使用中文版本名作为节点名（去除扩展名）

    Args:
        videos: 视频列表
        vpy_path: VPY脚本路径
    """
    import yaml

    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(vpy_path))
    config_dir = os.path.join(script_dir, '.vsjet', 'vspreview')
    os.makedirs(config_dir, exist_ok=True)

    # 生成配置
    config = {
        'outputs': []
    }

    for i, video in enumerate(videos):
        # 去除文件扩展名
        name_without_ext = os.path.splitext(video.name)[0]
        config['outputs'].append({
            'index': i,
            'name': name_without_ext  # 使用中文版本名（不含扩展名）
        })

    # 写入配置文件
    config_path = os.path.join(config_dir, 'preview.yml')
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        print(f"已生成 VSPreview 配置: {config_path}")
    except ImportError:
        # 如果没有 yaml 模块，手动写入
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write("outputs:\n")
            for i, video in enumerate(videos):
                name_without_ext = os.path.splitext(video.name)[0]
                f.write(f"  - index: {i}\n")
                f.write(f"    name: {name_without_ext}\n")
        print(f"已生成 VSPreview 配置（手动格式）: {config_path}")


if __name__ == "__main__":
    # 测试代码
    print("VPY脚本生成模块已加载")

    # 源插件检测与加载函数
    script_lines.append("HAS_LSMASH = hasattr(core, 'lsmas')")
    script_lines.append("HAS_BS = hasattr(core, 'bs')")
    script_lines.append("HAS_FFMS2 = hasattr(core, 'ffms2')")
    script_lines.append("def load_source(path):")
    script_lines.append("    if HAS_LSMASH:")
    script_lines.append("        return core.lsmas.LWLibavSource(path, cachedir=cache_dir)")
    script_lines.append("    elif HAS_BS:")
    script_lines.append("        return core.bs.VideoSource(source=path)")
    script_lines.append("    elif HAS_FFMS2:")
    script_lines.append("        return core.ffms2.Source(path)")
    script_lines.append("    else:")
    script_lines.append("        raise RuntimeError('未找到视频源插件: 需要 LSMASHSource/BestSource/FFMS2')")
    script_lines.append("")

