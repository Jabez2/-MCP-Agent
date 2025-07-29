"""
智能路径解析器

提供智能的路径解析和项目结构发现功能，用于支持多Agent协作中的文件操作。
"""

import os
import glob
from pathlib import Path
from typing import Dict, List, Any


class IntelligentPathResolver:
    """智能路径解析器 - 用于动态发现和管理项目文件路径"""
    
    def __init__(self, project_config: Dict[str, str], facts: List[str], plan: List[str]):
        """
        初始化智能路径解析器
        
        Args:
            project_config: 项目配置信息
            facts: 已确认的事实列表
            plan: 执行计划列表
        """
        self.project_config = project_config
        self.facts = facts
        self.plan = plan
        self.base_dirs = ['/Users/jabez/output']
        
    def discover_project_structure(self) -> Dict[str, Any]:
        """
        发现项目结构
        
        Returns:
            包含项目结构信息的字典
        """
        structure = {
            'project_root': None,
            'main_files': [],
            'test_files': [],
            'utils_dir': None,
            'python_files': []
        }
        
        for base_dir in self.base_dirs:
            if os.path.exists(base_dir):
                try:
                    path = Path(base_dir)
                    
                    # 查找测试文件
                    for pattern in ['test_*.py', '*_test.py']:
                        structure['test_files'].extend([str(f) for f in path.rglob(pattern)])
                    
                    # 查找主文件
                    for pattern in ['*.py']:
                        matches = list(path.glob(pattern))
                        structure['main_files'].extend([str(f) for f in matches if not f.name.startswith('test_')])
                    
                    # 查找utils目录
                    utils_dirs = list(path.glob('**/utils'))
                    if utils_dirs:
                        structure['utils_dir'] = str(utils_dirs[0])
                    
                    # 统计Python文件
                    structure['python_files'] = [str(f) for f in path.rglob('*.py')]
                    
                    if structure['main_files'] or structure['test_files']:
                        structure['project_root'] = base_dir
                        break
                        
                except Exception as e:
                    print(f"⚠️ 扫描目录 {base_dir} 失败: {e}")
        
        return structure
    
    def get_working_directory_for_agent(self, agent_name: str) -> str:
        """
        为特定Agent获取推荐的工作目录
        
        Args:
            agent_name: Agent名称
            
        Returns:
            推荐的工作目录路径
        """
        structure = self.discover_project_structure()
        
        if structure['project_root']:
            return structure['project_root']
        
        return self.base_dirs[0] if self.base_dirs else '/Users/jabez/output'
    
    def generate_path_report(self) -> str:
        """
        生成路径解析报告
        
        Returns:
            格式化的路径报告字符串
        """
        structure = self.discover_project_structure()
        
        report_lines = [
            "🔍 智能路径解析报告",
            "=" * 40,
            f"项目根目录: {structure.get('project_root', '未检测到')}",
            f"主文件数量: {len(structure.get('main_files', []))}",
            f"测试文件数量: {len(structure.get('test_files', []))}",
            f"Utils目录: {structure.get('utils_dir', '未检测到')}",
            f"Python文件总数: {len(structure.get('python_files', []))}",
            "",
            "📁 发现的主文件:",
        ]
        
        for main_file in structure.get('main_files', [])[:5]:  # 只显示前5个
            report_lines.append(f"  - {main_file}")
        
        report_lines.extend([
            "",
            "🧪 发现的测试文件:",
        ])
        
        for test_file in structure.get('test_files', [])[:5]:  # 只显示前5个
            report_lines.append(f"  - {test_file}")
        
        return "\n".join(report_lines)
