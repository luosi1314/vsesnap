#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目管理模块
用于管理多个对比配置项目
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class ProjectManager:
    """项目管理器"""

    def __init__(self, projects_dir: str = "projects", screenshots_dir: str = "screenshots"):
        """
        初始化项目管理器

        Args:
            projects_dir: 项目配置目录路径
            screenshots_dir: 截图存储目录路径（独立于项目配置）
        """
        self.projects_dir = projects_dir
        self.screenshots_dir = screenshots_dir
        os.makedirs(projects_dir, exist_ok=True)
        os.makedirs(screenshots_dir, exist_ok=True)
    
    def list_projects(self) -> List[Dict]:
        """
        列出所有项目
        
        Returns:
            项目列表
        """
        projects = []
        
        if not os.path.exists(self.projects_dir):
            return projects
        
        for item in os.listdir(self.projects_dir):
            project_path = os.path.join(self.projects_dir, item)
            if os.path.isdir(project_path):
                config_file = os.path.join(project_path, "config.json")
                if os.path.exists(config_file):
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        
                        projects.append({
                            'name': item,
                            'path': project_path,
                            'config': config,
                            'modified': datetime.fromtimestamp(
                                os.path.getmtime(config_file)
                            ).strftime('%Y-%m-%d %H:%M:%S')
                        })
                    except Exception as e:
                        print(f"读取项目配置失败 {item}: {e}")
        
        # 按修改时间排序
        projects.sort(key=lambda x: x['modified'], reverse=True)
        
        return projects
    
    def create_project(self, project_name: str) -> str:
        """
        创建新项目
        
        Args:
            project_name: 项目名称
            
        Returns:
            项目路径
        """
        # 清理项目名称
        safe_name = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in project_name)
        safe_name = safe_name.strip()
        
        if not safe_name:
            safe_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        project_path = os.path.join(self.projects_dir, safe_name)
        
        # 如果项目已存在，添加时间戳
        if os.path.exists(project_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_name = f"{safe_name}_{timestamp}"
            project_path = os.path.join(self.projects_dir, safe_name)
        
        # 创建项目目录
        os.makedirs(project_path, exist_ok=True)

        # 创建子目录
        os.makedirs(os.path.join(project_path, "references"), exist_ok=True)

        # 在全局截图目录中创建项目专属子目录
        project_screenshots_dir = os.path.join(self.screenshots_dir, safe_name)
        os.makedirs(project_screenshots_dir, exist_ok=True)
        
        # 创建默认配置
        default_config = {
            'program_name': project_name,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'videos': [],
            'reference_image': '',
            'reference_note': '',
            'screenshot_count': 10
        }
        
        config_file = os.path.join(project_path, "config.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        return project_path
    
    def load_project(self, project_name: str) -> Optional[Dict]:
        """
        加载项目配置
        
        Args:
            project_name: 项目名称
            
        Returns:
            项目配置
        """
        project_path = os.path.join(self.projects_dir, project_name)
        config_file = os.path.join(project_path, "config.json")
        
        if not os.path.exists(config_file):
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            config['_project_name'] = project_name
            config['_project_path'] = project_path
            
            return config
        except Exception as e:
            print(f"加载项目配置失败: {e}")
            return None
    
    def save_project(self, project_name: str, config: Dict) -> bool:
        """
        保存项目配置
        
        Args:
            project_name: 项目名称
            config: 项目配置
            
        Returns:
            是否成功
        """
        project_path = os.path.join(self.projects_dir, project_name)
        
        if not os.path.exists(project_path):
            project_path = self.create_project(project_name)
        
        config_file = os.path.join(project_path, "config.json")
        
        try:
            # 移除内部属性
            save_config = {k: v for k, v in config.items() if not k.startswith('_')}
            save_config['modified'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(save_config, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"保存项目配置失败: {e}")
            return False
    
    def delete_project(self, project_name: str, delete_screenshots: bool = False) -> bool:
        """
        删除项目

        Args:
            project_name: 项目名称
            delete_screenshots: 是否同时删除截图（默认保留）

        Returns:
            是否成功
        """
        project_path = os.path.join(self.projects_dir, project_name)

        if not os.path.exists(project_path):
            return False

        try:
            # 删除项目配置目录
            shutil.rmtree(project_path)

            # 如果选择删除截图，则删除截图目录
            if delete_screenshots:
                screenshots_path = os.path.join(self.screenshots_dir, project_name)
                if os.path.exists(screenshots_path):
                    shutil.rmtree(screenshots_path)

            return True
        except Exception as e:
            print(f"删除项目失败: {e}")
            return False
    
    def rename_project(self, old_name: str, new_name: str) -> bool:
        """
        重命名项目
        
        Args:
            old_name: 旧项目名称
            new_name: 新项目名称
            
        Returns:
            是否成功
        """
        old_path = os.path.join(self.projects_dir, old_name)
        
        if not os.path.exists(old_path):
            return False
        
        # 清理新名称
        safe_name = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in new_name)
        safe_name = safe_name.strip()
        
        new_path = os.path.join(self.projects_dir, safe_name)
        
        if os.path.exists(new_path):
            return False
        
        try:
            os.rename(old_path, new_path)
            
            # 更新配置中的项目名称
            config_file = os.path.join(new_path, "config.json")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                config['program_name'] = new_name
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"重命名项目失败: {e}")
            return False
    
    def get_project_screenshots_dir(self, project_name: str) -> str:
        """
        获取项目的截图目录（在全局截图目录中）

        Args:
            project_name: 项目名称

        Returns:
            截图目录路径
        """
        screenshots_dir = os.path.join(self.screenshots_dir, project_name)
        os.makedirs(screenshots_dir, exist_ok=True)
        return screenshots_dir
    
    def get_project_references_dir(self, project_name: str) -> str:
        """
        获取项目的参考图目录
        
        Args:
            project_name: 项目名称
            
        Returns:
            参考图目录路径
        """
        project_path = os.path.join(self.projects_dir, project_name)
        references_dir = os.path.join(project_path, "references")
        os.makedirs(references_dir, exist_ok=True)
        return references_dir


if __name__ == "__main__":
    # 测试代码
    pm = ProjectManager()
    
    # 创建测试项目
    project_path = pm.create_project("测试项目")
    print(f"创建项目: {project_path}")
    
    # 列出所有项目
    projects = pm.list_projects()
    print(f"\n所有项目 ({len(projects)}):")
    for p in projects:
        print(f"  - {p['name']} (修改于: {p['modified']})")

