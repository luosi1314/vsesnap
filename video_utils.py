#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
视频工具模块
用于检测视频信息（扫描模式、场序等）
"""

import os
import subprocess
import json


def detect_scan_type(filepath: str):
    """
    检测视频的扫描模式
    
    Args:
        filepath: 视频文件路径
        
    Returns:
        dict: {
            'is_interlaced': bool,  # 是否隔行扫描
            'tff': bool,            # True=TFF, False=BFF
            'scan_type': str        # 'Progressive' 或 'Interlaced'
        }
    """
    result = {
        'is_interlaced': False,
        'tff': True,  # 默认TFF
        'scan_type': 'Progressive'
    }
    
    try:
        # 尝试使用 pymediainfo
        try:
            from pymediainfo import MediaInfo
            media_info = MediaInfo.parse(filepath)
            
            for track in media_info.tracks:
                if track.track_type == "Video":
                    scan_type = track.scan_type
                    scan_order = track.scan_order
                    
                    if scan_type:
                        result['scan_type'] = scan_type
                        result['is_interlaced'] = scan_type.lower() in ['interlaced', 'mbaff']
                    
                    if scan_order:
                        # TFF (Top Field First) 或 BFF (Bottom Field First)
                        result['tff'] = scan_order.upper() in ['TFF', 'TOP FIELD FIRST', '2:3 PULLDOWN']
                    
                    break
            
            return result
            
        except ImportError:
            pass
        
        # 尝试使用 ffprobe
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-select_streams', 'v:0',
                filepath
            ]
            
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            data = json.loads(output)
            
            if 'streams' in data and len(data['streams']) > 0:
                stream = data['streams'][0]
                
                # 检查 field_order
                field_order = stream.get('field_order', 'progressive')
                
                if field_order in ['tt', 'tb']:  # tt=TFF, tb=TFF
                    result['is_interlaced'] = True
                    result['tff'] = True
                    result['scan_type'] = 'Interlaced'
                elif field_order in ['bb', 'bt']:  # bb=BFF, bt=BFF
                    result['is_interlaced'] = True
                    result['tff'] = False
                    result['scan_type'] = 'Interlaced'
                
                # 检查 codec_tag_string (有些文件会标记)
                codec_tag = stream.get('codec_tag_string', '')
                if 'i' in codec_tag.lower():
                    result['is_interlaced'] = True
            
            return result
            
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            pass
        
        # 尝试使用 VapourSynth 检测
        try:
            import vapoursynth as vs
            core = vs.core
            
            # 创建缓存目录
            cache_dir = os.path.join(os.getcwd(), '.cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            # 加载视频
            clip = core.lsmas.LWLibavSource(filepath, cachedir=cache_dir)
            
            # 检查帧属性
            frame = clip.get_frame(0)
            
            # 检查 _FieldBased 属性
            field_based = frame.props.get('_FieldBased', 0)
            
            if field_based == 1:  # BFF
                result['is_interlaced'] = True
                result['tff'] = False
                result['scan_type'] = 'Interlaced'
            elif field_based == 2:  # TFF
                result['is_interlaced'] = True
                result['tff'] = True
                result['scan_type'] = 'Interlaced'
            
            return result
            
        except Exception:
            pass
    
    except Exception as e:
        print(f"检测扫描模式失败: {e}")
    
    return result


def get_video_fps(filepath: str, return_field_rate: bool = False):
    """
    获取视频的帧率

    注意：对于隔行扫描视频，默认返回帧率（frame rate），而不是场频（field rate）
    例如：25i 视频返回 25.0，而不是 50.0

    Args:
        filepath: 视频文件路径
        return_field_rate: 是否返回场频（仅对隔行视频有效）

    Returns:
        float: 帧率（如 25.0, 29.97 等），失败返回 None
    """
    try:
        # 首先检测是否为隔行扫描
        scan_info = detect_scan_type(filepath)
        is_interlaced = scan_info['is_interlaced']

        # 尝试使用 pymediainfo
        try:
            from pymediainfo import MediaInfo
            media_info = MediaInfo.parse(filepath)

            for track in media_info.tracks:
                if track.track_type == "Video":
                    fps = track.frame_rate
                    if fps:
                        fps_value = float(fps)
                        # 如果是隔行扫描且不要求返回场频，则除以2
                        if is_interlaced and not return_field_rate:
                            # 检查是否已经是帧率（通过判断是否接近常见的场频）
                            if abs(fps_value - 50.0) < 0.1 or abs(fps_value - 59.94) < 0.1 or abs(fps_value - 60.0) < 0.1:
                                fps_value = fps_value / 2.0
                        return fps_value
        except ImportError:
            pass

        # 尝试使用 ffprobe
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-select_streams', 'v:0',
                filepath
            ]

            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            data = json.loads(output)

            if 'streams' in data and len(data['streams']) > 0:
                stream = data['streams'][0]

                # 尝试从 r_frame_rate 获取
                r_frame_rate = stream.get('r_frame_rate', '')
                if r_frame_rate and '/' in r_frame_rate:
                    num, den = r_frame_rate.split('/')
                    fps_value = float(num) / float(den)
                    # 如果是隔行扫描且不要求返回场频，则除以2
                    if is_interlaced and not return_field_rate:
                        if abs(fps_value - 50.0) < 0.1 or abs(fps_value - 59.94) < 0.1 or abs(fps_value - 60.0) < 0.1:
                            fps_value = fps_value / 2.0
                    return fps_value

                # 尝试从 avg_frame_rate 获取
                avg_frame_rate = stream.get('avg_frame_rate', '')
                if avg_frame_rate and '/' in avg_frame_rate:
                    num, den = avg_frame_rate.split('/')
                    fps_value = float(num) / float(den)
                    # 如果是隔行扫描且不要求返回场频，则除以2
                    if is_interlaced and not return_field_rate:
                        if abs(fps_value - 50.0) < 0.1 or abs(fps_value - 59.94) < 0.1 or abs(fps_value - 60.0) < 0.1:
                            fps_value = fps_value / 2.0
                    return fps_value
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            pass

        # 尝试使用 VapourSynth
        try:
            import vapoursynth as vs
            core = vs.core

            cache_dir = os.path.join(os.getcwd(), '.cache')
            os.makedirs(cache_dir, exist_ok=True)

            clip = core.lsmas.LWLibavSource(filepath, cachedir=cache_dir)
            fps_num = clip.fps.numerator
            fps_den = clip.fps.denominator
            fps_value = fps_num / fps_den

            # 如果是隔行扫描且不要求返回场频，则除以2
            if is_interlaced and not return_field_rate:
                if abs(fps_value - 50.0) < 0.1 or abs(fps_value - 59.94) < 0.1 or abs(fps_value - 60.0) < 0.1:
                    fps_value = fps_value / 2.0

            return fps_value
        except Exception:
            pass

    except Exception as e:
        print(f"获取视频帧率失败: {e}")

    return None


def format_fps_display(fps: float, is_interlaced: bool = False):
    """
    格式化帧率显示

    Args:
        fps: 帧率
        is_interlaced: 是否隔行扫描

    Returns:
        str: 格式化的帧率字符串（如 "25p", "25i", "29.97i"）
    """
    if fps is None:
        return "未知"

    # 判断是逐行还是隔行
    suffix = 'i' if is_interlaced else 'p'

    # 常见帧率的特殊处理
    if abs(fps - 23.976) < 0.01:
        return f"23.976{suffix}"
    elif abs(fps - 24.0) < 0.01:
        return f"24{suffix}"
    elif abs(fps - 25.0) < 0.01:
        return f"25{suffix}"
    elif abs(fps - 29.97) < 0.01:
        return f"29.97{suffix}"
    elif abs(fps - 30.0) < 0.01:
        return f"30{suffix}"
    elif abs(fps - 50.0) < 0.01:
        return f"50{suffix}"
    elif abs(fps - 59.94) < 0.01:
        return f"59.94{suffix}"
    elif abs(fps - 60.0) < 0.01:
        return f"60{suffix}"
    else:
        # 其他帧率，保留2位小数
        return f"{fps:.2f}{suffix}"


def get_video_info(filepath: str):
    """
    获取视频的详细信息

    Args:
        filepath: 视频文件路径

    Returns:
        dict: 视频信息
    """
    scan_info = detect_scan_type(filepath)
    fps = get_video_fps(filepath)

    info = {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'filesize': os.path.getsize(filepath) if os.path.exists(filepath) else 0,
        'scan_info': scan_info,
        'fps': fps,
        'fps_display': format_fps_display(fps, scan_info['is_interlaced'])
    }

    try:
        from pymediainfo import MediaInfo
        media_info = MediaInfo.parse(filepath)

        for track in media_info.tracks:
            if track.track_type == "Video":
                info['width'] = track.width
                info['height'] = track.height
                info['duration'] = track.duration
                info['codec'] = track.codec
                break
    except:
        pass

    return info


if __name__ == "__main__":
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        info = get_video_info(filepath)
        print(json.dumps(info, indent=2, ensure_ascii=False))

