#!/usr/bin/env python3
"""
修复 VSPreview 存储文件问题
"""
import os
import shutil
from pathlib import Path

def fix_vspreview_storage():
    """修复 VSPreview 存储文件"""
    
    # 获取当前目录
    current_dir = Path.cwd()
    vsjet_dir = current_dir / '.vsjet'
    vspreview_storage_dir = vsjet_dir / 'vspreview'
    
    print("="*60)
    print("VSPreview 存储文件修复工具")
    print("="*60)
    
    # 检查是否存在 .vsjet/vspreview 目录
    if not vspreview_storage_dir.exists():
        print(f"✓ 未发现旧的存储文件目录")
        return
    
    print(f"\n发现存储目录: {vspreview_storage_dir}")
    
    # 列出所有 .yml 文件
    yml_files = list(vspreview_storage_dir.glob('*.yml'))
    
    if not yml_files:
        print("✓ 目录中没有 .yml 文件")
        return
    
    print(f"\n发现 {len(yml_files)} 个存储文件:")
    for yml_file in yml_files:
        print(f"  - {yml_file.name}")
    
    # 询问用户是否删除
    print("\n这些文件是旧版本的 VSPreview 存储文件。")
    print("建议删除它们，VSPreview 会自动创建新版本的存储文件。")
    
    response = input("\n是否删除这些文件? (y/n): ").strip().lower()
    
    if response == 'y':
        # 创建备份目录
        backup_dir = vspreview_storage_dir / 'backup'
        backup_dir.mkdir(exist_ok=True)
        
        print(f"\n正在备份文件到: {backup_dir}")
        
        # 备份并删除文件
        for yml_file in yml_files:
            backup_path = backup_dir / yml_file.name
            shutil.copy2(yml_file, backup_path)
            print(f"  ✓ 已备份: {yml_file.name}")
            
            yml_file.unlink()
            print(f"  ✓ 已删除: {yml_file.name}")
        
        print("\n✓ 所有旧存储文件已删除并备份")
        print("✓ VSPreview 将在下次启动时创建新的存储文件")
    else:
        print("\n已取消操作")
        print("\n如果要手动删除，可以使用以下命令:")
        print(f"  rmdir /s /q \"{vspreview_storage_dir}\"")
        print("\n或者在启动 VSPreview 时添加 --force-storage 参数:")
        print("  vspreview --force-storage preview.vpy")

def fix_avscompat_warning():
    """提供 AvsCompat.dll 重复加载问题的解决方案"""
    
    print("\n" + "="*60)
    print("AvsCompat.dll 重复加载问题")
    print("="*60)
    
    print("\n检测到 AvsCompat.dll 在两个位置被加载:")
    print("  1. C:\\Users\\admin\\AppData\\Roaming\\VapourSynth\\plugins64\\AvsCompat.dll")
    print("  2. E:/MyProjects/vapoursynth/vs/VapourSynth/core/plugins/AvsCompat.dll")
    
    print("\n这是一个警告，不会影响功能，但可能导致冲突。")
    print("\n建议解决方案:")
    print("  1. 删除用户目录中的插件副本:")
    print("     del \"C:\\Users\\admin\\AppData\\Roaming\\VapourSynth\\plugins64\\AvsCompat.dll\"")
    print("\n  2. 或者删除 VapourSynth 安装目录中的副本")
    print("     (不推荐，可能影响其他程序)")
    
    print("\n注意: 这只是警告，如果不影响使用可以忽略")

if __name__ == "__main__":
    try:
        fix_vspreview_storage()
        fix_avscompat_warning()
        
        print("\n" + "="*60)
        print("修复完成!")
        print("="*60)
        print("\n现在可以尝试重新启动 VSPreview")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...")

