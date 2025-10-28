#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
缓存清理工具
移动lwi文件到.cache目录
"""

import os
import shutil
import glob


def cleanup_lwi_files():
    """移动lwi文件到缓存目录"""
    # 创建缓存目录
    cache_dir = '.cache'
    os.makedirs(cache_dir, exist_ok=True)
    print(f"[信息] 缓存目录: {cache_dir}")
    print()
    
    # 查找所有lwi文件
    lwi_files = glob.glob('*.lwi')
    
    if not lwi_files:
        print("[信息] 未找到lwi文件")
        return
    
    print(f"[信息] 找到 {len(lwi_files)} 个lwi文件")
    print()
    
    # 移动文件
    moved_count = 0
    for lwi_file in lwi_files:
        try:
            dest = os.path.join(cache_dir, lwi_file)
            shutil.move(lwi_file, dest)
            print(f"[移动] {lwi_file} -> {dest}")
            moved_count += 1
        except Exception as e:
            print(f"[错误] 移动 {lwi_file} 失败: {e}")
    
    print()
    print(f"[完成] 已移动 {moved_count} 个文件到缓存目录")


def cleanup_screenshots():
    """清理旧的截图目录"""
    screenshot_dirs = glob.glob('screenshots_*')
    
    if not screenshot_dirs:
        print("[信息] 未找到截图目录")
        return
    
    print(f"[信息] 找到 {len(screenshot_dirs)} 个截图目录")
    print()
    
    response = input("[提示] 是否删除这些截图目录？(y/N): ")
    
    if response.lower() == 'y':
        deleted_count = 0
        for screenshot_dir in screenshot_dirs:
            try:
                shutil.rmtree(screenshot_dir)
                print(f"[删除] {screenshot_dir}")
                deleted_count += 1
            except Exception as e:
                print(f"[错误] 删除 {screenshot_dir} 失败: {e}")
        
        print()
        print(f"[完成] 已删除 {deleted_count} 个截图目录")
    else:
        print("[取消] 保留截图目录")


def main():
    """主函数"""
    print("=" * 60)
    print("VSE Screenshot - 缓存清理工具")
    print("=" * 60)
    print()
    
    # 清理lwi文件
    cleanup_lwi_files()
    
    print()
    print("-" * 60)
    print()
    
    # 清理截图目录
    cleanup_screenshots()
    
    print()
    print("=" * 60)
    print("清理完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

