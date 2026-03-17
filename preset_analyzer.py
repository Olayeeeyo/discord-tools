#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preset Analyzer - 预设文件分析器
提取方法论级别的精华，构建AI素材库
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict
import glob


class PresetAnalyzer:
    """预设文件分析器"""

    # 方法论维度定义
    DIMENSIONS = {
        'thinking_framework': '思维框架',      # CoT、思维链、推理过程
        'character_building': '角色构建',      # 人设塑造、性格刻画
        'writing_style': '文风控制',           # 文风、修辞、叙事
        'scene_construction': '场景构建',      # 场景、环境、氛围
        'dialogue_design': '对话设计',         # 对话、交互、语言风格
        'emotion_expression': '情感表达',      # 情感、心理、描写
        'nsfw_crafting': 'NSFW构建',           # 成人内容处理
        'constraint_mechanism': '约束机制',    # 破限、越狱、限制解除
        'quality_control': '质量控制',         # 自检、审查、修正
        'creative_technique': '创意技法',      # 创意写作技巧
    }

    def __init__(self, downloads_dir: str = "downloads"):
        self.downloads_dir = Path(downloads_dir)
        self.presets_data = []
        self.methodology_db = defaultdict(list)
        self.extracted_patterns = defaultdict(list)

    def collect_presets(self) -> List[Path]:
        """收集所有预设文件"""
        pattern = str(self.downloads_dir / "*/preset/*.json")
        files = glob.glob(pattern)
        return [Path(f) for f in files]

    def analyze_preset(self, filepath: Path) -> Dict[str, Any]:
        """分析单个预设文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load {filepath}: {e}")
            return None

        # 提取基本信息
        preset_info = {
            'filename': filepath.name,
            'source_thread': filepath.parent.parent.name,
            'parameters': self._extract_parameters(data),
            'prompts_analysis': self._analyze_prompts(data.get('prompts', [])),
            'format_templates': self._extract_templates(data),
            'methodology_tags': self._tag_methodology(data),
            'techniques': self._extract_techniques(data),
            'raw_content': self._extract_raw_content(data)
        }

        return preset_info

    def _extract_parameters(self, data: Dict) -> Dict:
        """提取参数设置"""
        params = {}
        param_keys = [
            'temperature', 'top_p', 'top_k', 'frequency_penalty',
            'presence_penalty', 'repetition_penalty', 'min_p'
        ]
        for key in param_keys:
            if key in data:
                params[key] = data[key]
        return params

    def _analyze_prompts(self, prompts: List[Dict]) -> List[Dict]:
        """分析prompts结构"""
        analyzed = []
        for prompt in prompts:
            if not isinstance(prompt, dict):
                continue

            analysis = {
                'name': prompt.get('name', 'Unnamed'),
                'role': prompt.get('role', 'unknown'),
                'position': prompt.get('injection_position', 0),
                'depth': prompt.get('injection_depth', 4),
                'enabled': prompt.get('enabled', True),
                'content_summary': self._summarize_content(prompt.get('content', '')),
                'techniques_found': self._detect_techniques(prompt.get('content', '')),
                'content_length': len(prompt.get('content', ''))
            }
            analyzed.append(analysis)
        return analyzed

    def _summarize_content(self, content: str) -> str:
        """总结内容核心思想"""
        if not content:
            return ""

        # 提取核心指令（通常是前几行或关键句子）
        lines = content.strip().split('\n')

        # 寻找主题句
        summary_lines = []
        for line in lines[:10]:  # 看前10行
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 20:
                summary_lines.append(line[:100] + '...' if len(line) > 100 else line)
                if len(summary_lines) >= 2:
                    break

        return ' | '.join(summary_lines) if summary_lines else "(No summary)"

    def _detect_techniques(self, content: str) -> List[str]:
        """检测使用的技法"""
        techniques = []

        # 技法模式匹配
        patterns = {
            'cot_thinking': r'<thinking>|思维链|CoT|chain of thought',
            'draft_system': r'draft|草稿|<!--|-->|rewrite|修正',
            'persona_override': r'jailbreak|override|越狱|破限|突破限制',
            'nsfw_module': r'nsfw|sex|性爱|色情|erotic',
            'character_anchor': r'人设|性格|personality|character',
            'scene_building': r'场景|氛围|scene|atmosphere',
            'emotion_layer': r'情感|emotion|心理|psychology',
            'self_check': r'自检|审查|check|verify',
            'style_control': r'文风|style|修辞|rhetoric',
            'creative_mode': r'创意|creative|小说|fiction',
            'instruction_hierarchy': r'指令层级|priority|override',
            'tag_system': r'<.*?>|XML|标签系统',
            'example_driven': r'example|示例|例子|sample',
            'step_by_step': r'步骤|step|流程|process',
            'constraint_definition': r'禁止|do not|never|严禁|constraint',
        }

        content_lower = content.lower()
        for tech, pattern in patterns.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                techniques.append(tech)

        return techniques

    def _extract_templates(self, data: Dict) -> Dict[str, str]:
        """提取格式模板"""
        templates = {}
        template_keys = [
            'wi_format', 'scenario_format', 'personality_format',
            'new_chat_prompt', 'new_group_chat_prompt',
            'impersonation_prompt', 'continue_nudge_prompt'
        ]
        for key in template_keys:
            if key in data and data[key]:
                templates[key] = data[key][:200] + '...' if len(data[key]) > 200 else data[key]
        return templates

    def _tag_methodology(self, data: Dict) -> List[str]:
        """标记方法论维度"""
        tags = []
        all_content = json.dumps(data).lower()

        # 思维框架
        if any(kw in all_content for kw in ['cot', '思维链', 'thinking', 'chain of thought', '草稿']):
            tags.append('thinking_framework')

        # 角色构建
        if any(kw in all_content for kw in ['人设', 'personality', 'character', '角色']):
            tags.append('character_building')

        # 文风控制
        if any(kw in all_content for kw in ['文风', 'style', '修辞', '文笔', '文学']):
            tags.append('writing_style')

        # 约束机制
        if any(kw in all_content for kw in ['jailbreak', '破限', 'override', '越狱']):
            tags.append('constraint_mechanism')

        # 质量控制
        if any(kw in all_content for kw in ['自检', '审查', 'check', 'verify', 'draft']):
            tags.append('quality_control')

        # NSFW
        if any(kw in all_content for kw in ['nsfw', 'sex', '性爱', 'erotic']):
            tags.append('nsfw_crafting')

        # 创意技法
        if any(kw in all_content for kw in ['creative', '创意', '小说', 'fiction', 'novel']):
            tags.append('creative_technique')

        return tags

    def _extract_techniques(self, data: Dict) -> List[Dict]:
        """提取具体技法"""
        techniques = []

        prompts = data.get('prompts', [])
        for prompt in prompts:
            if not isinstance(prompt, dict):
                continue

            content = prompt.get('content', '')
            name = prompt.get('name', 'Unnamed')

            # 提取技法描述
            tech_info = {
                'name': name,
                'purpose': self._extract_purpose(content),
                'mechanism': self._extract_mechanism(content),
                'techniques': self._detect_techniques(content)
            }
            techniques.append(tech_info)

        return techniques

    def _extract_purpose(self, content: str) -> str:
        """提取目的/意图"""
        # 查找以"目的"、"目标"、"用于"等开头的句子
        patterns = [
            r'目的[：:]\s*(.+?)(?:\n|$)',
            r'目标[：:]\s*(.+?)(?:\n|$)',
            r'用于(.+?)(?:\n|$)',
            r'实现(.+?)(?:效果|目标|功能)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()[:100]
        return ""

    def _extract_mechanism(self, content: str) -> str:
        """提取机制/原理"""
        # 提取核心机制描述
        lines = content.strip().split('\n')
        mechanisms = []

        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('1. ') or line.startswith('2. '):
                mechanisms.append(line[:80])
            if len(mechanisms) >= 3:
                break

        return ' | '.join(mechanisms) if mechanisms else ""

    def _extract_raw_content(self, data: Dict) -> Dict[str, Any]:
        """提取原始内容供进一步分析"""
        all_prompts = []
        for prompt in data.get('prompts', []):
            if isinstance(prompt, dict):
                all_prompts.append({
                    'name': prompt.get('name', ''),
                    'content': prompt.get('content', '')
                })

        return {
            'prompts': all_prompts,
            'full_data': data  # 保留完整数据
        }

    def run_analysis(self):
        """运行完整分析"""
        print("=" * 60)
        print("预设文件分析器 - 提取方法论精华")
        print("=" * 60)

        # 收集预设文件
        preset_files = self.collect_presets()
        print(f"\n[INFO] 找到 {len(preset_files)} 个预设文件")

        if not preset_files:
            print("[ERROR] 没有找到预设文件，请确保 downloads/ 目录存在")
            return

        # 分析每个预设
        for i, filepath in enumerate(preset_files, 1):
            print(f"\n[{i}/{len(preset_files)}] 分析: {filepath.name}")
            preset_data = self.analyze_preset(filepath)
            if preset_data:
                self.presets_data.append(preset_data)

                # 按方法论维度分类
                for tag in preset_data['methodology_tags']:
                    self.methodology_db[tag].append({
                        'source': preset_data['source_thread'],
                        'filename': preset_data['filename'],
                        'techniques': preset_data['techniques'],
                        'prompts': preset_data['prompts_analysis']
                    })

        print(f"\n[INFO] 成功分析 {len(self.presets_data)} 个预设")

        # 生成报告
        self.generate_report()

    def generate_report(self):
        """生成分析报告"""
        output_dir = Path("analysis_output")
        output_dir.mkdir(exist_ok=True)

        # 1. 方法论数据库
        self._save_methodology_db(output_dir)

        # 2. 技法汇总
        self._save_techniques_summary(output_dir)

        # 3. AI素材库
        self._save_ai_materials(output_dir)

        # 4. 统计报告
        self._save_statistics(output_dir)

        print(f"\n[DONE] 分析报告已保存到: {output_dir.absolute()}")

    def _save_methodology_db(self, output_dir: Path):
        """保存方法论数据库"""
        db = {}
        for dimension_key, dimension_name in self.DIMENSIONS.items():
            entries = self.methodology_db.get(dimension_key, [])

            db[dimension_key] = {
                'name': dimension_name,
                'count': len(entries),
                'presets': []
            }

            for entry in entries[:5]:  # 每个维度最多5个示例
                db[dimension_key]['presets'].append({
                    'source': entry['source'],
                    'techniques': [t['name'] for t in entry['techniques'][:3]]
                })

        with open(output_dir / "methodology_database.json", 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

    def _save_techniques_summary(self, output_dir: Path):
        """保存技法汇总"""
        all_techniques = defaultdict(list)

        for preset in self.presets_data:
            for tech in preset['techniques']:
                for tech_type in tech['techniques']:
                    all_techniques[tech_type].append({
                        'preset': preset['filename'],
                        'prompt_name': tech['name'],
                        'purpose': tech['purpose'],
                        'mechanism': tech['mechanism']
                    })

        # 排序并保存
        summary = {
            'total_technique_types': len(all_techniques),
            'techniques_by_type': dict(all_techniques)
        }

        with open(output_dir / "techniques_summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    def _save_ai_materials(self, output_dir: Path):
        """保存AI可用的素材库"""
        materials = {
            'metadata': {
                'total_presets_analyzed': len(self.presets_data),
                'generated_at': str(Path().stat().st_mtime),
                'purpose': '方法论级别精华集成'
            },
            'thinking_frameworks': self._extract_thinking_frameworks(),
            'writing_techniques': self._extract_writing_techniques(),
            'character_methods': self._extract_character_methods(),
            'quality_patterns': self._extract_quality_patterns(),
            'constraint_strategies': self._extract_constraint_strategies(),
            'raw_prompts_library': self._build_prompts_library()
        }

        with open(output_dir / "ai_materials_library.json", 'w', encoding='utf-8') as f:
            json.dump(materials, f, ensure_ascii=False, indent=2)

        # 同时保存为Markdown便于阅读
        self._save_markdown_version(materials, output_dir)

    def _extract_thinking_frameworks(self) -> List[Dict]:
        """提取思维框架"""
        frameworks = []

        for preset in self.presets_data:
            if 'thinking_framework' not in preset['methodology_tags']:
                continue

            for prompt in preset['prompts_analysis']:
                if 'cot_thinking' in prompt['techniques_found'] or 'draft_system' in prompt['techniques_found']:
                    frameworks.append({
                        'source': f"{preset['source_thread']}/{prompt['name']}",
                        'framework_name': prompt['name'],
                        'core_idea': prompt['content_summary'],
                        'techniques': prompt['techniques_found']
                    })

        return frameworks[:20]  # 限制数量

    def _extract_writing_techniques(self) -> List[Dict]:
        """提取写作技法"""
        techniques = []

        for preset in self.presets_data:
            for prompt in preset['prompts_analysis']:
                if any(t in prompt['techniques_found'] for t in ['writing_style', 'scene_building', 'emotion_layer']):
                    techniques.append({
                        'source': preset['filename'],
                        'name': prompt['name'],
                        'summary': prompt['content_summary'],
                        'techniques': prompt['techniques_found']
                    })

        return techniques[:20]

    def _extract_character_methods(self) -> List[Dict]:
        """提取角色构建方法"""
        methods = []

        for preset in self.presets_data:
            if 'character_building' not in preset['methodology_tags']:
                continue

            for prompt in preset['prompts_analysis']:
                if 'character_anchor' in prompt['techniques_found']:
                    methods.append({
                        'source': preset['filename'],
                        'method_name': prompt['name'],
                        'approach': prompt['content_summary']
                    })

        return methods[:15]

    def _extract_quality_patterns(self) -> List[Dict]:
        """提取质量控制模式"""
        patterns = []

        for preset in self.presets_data:
            if 'quality_control' not in preset['methodology_tags']:
                continue

            for prompt in preset['prompts_analysis']:
                if any(t in prompt['techniques_found'] for t in ['self_check', 'draft_system']):
                    patterns.append({
                        'source': preset['filename'],
                        'control_name': prompt['name'],
                        'mechanism': prompt['content_summary']
                    })

        return patterns[:15]

    def _extract_constraint_strategies(self) -> List[Dict]:
        """提取约束策略"""
        strategies = []

        for preset in self.presets_data:
            if 'constraint_mechanism' not in preset['methodology_tags']:
                continue

            for prompt in preset['prompts_analysis']:
                if 'persona_override' in prompt['techniques_found']:
                    strategies.append({
                        'source': preset['filename'],
                        'strategy_name': prompt['name'],
                        'approach': prompt['content_summary']
                    })

        return strategies[:10]

    def _build_prompts_library(self) -> Dict[str, List[str]]:
        """构建提示词库"""
        library = defaultdict(list)

        for preset in self.presets_data:
            for prompt in preset['raw_content']['prompts']:
                content = prompt.get('content', '')
                name = prompt.get('name', 'unnamed')

                # 分类存储
                if any(kw in content.lower() for kw in ['thinking', '思维', 'cot']):
                    library['thinking_systems'].append(f"[{name}]\n{content[:500]}")
                elif any(kw in content.lower() for kw in ['character', '人设', 'personality']):
                    library['character_systems'].append(f"[{name}]\n{content[:500]}")
                elif any(kw in content.lower() for kw in ['style', '文风', 'writing']):
                    library['style_systems'].append(f"[{name}]\n{content[:500]}")
                elif any(kw in content.lower() for kw in ['draft', 'check', '自检']):
                    library['quality_systems'].append(f"[{name}]\n{content[:500]}")

        # 限制每个类别的数量
        return {k: v[:10] for k, v in library.items()}

    def _save_markdown_version(self, materials: Dict, output_dir: Path):
        """保存Markdown版本便于阅读"""
        md_content = f"""# 预设方法论精华素材库

> 生成时间: {materials['metadata']['generated_at']}
> 分析预设数: {materials['metadata']['total_presets_analyzed']}

## 目录

1. [思维框架](#思维框架)
2. [写作技法](#写作技法)
3. [角色构建方法](#角色构建方法)
4. [质量控制模式](#质量控制模式)
5. [约束策略](#约束策略)

---

## 思维框架

"""

        for item in materials['thinking_frameworks']:
            md_content += f"""### {item['framework_name']}
**来源**: {item['source']}

**核心思想**: {item['core_idea']}

**使用技法**: {', '.join(item['techniques'])}

---

"""

        md_content += """## 写作技法

"""
        for item in materials['writing_techniques']:
            md_content += f"""### {item['name']}
**来源**: {item['source']}

{item['summary']}

---

"""

        md_content += """## 角色构建方法

"""
        for item in materials['character_methods']:
            md_content += f"""### {item['method_name']}
**来源**: {item['source']}

{item['approach']}

---

"""

        md_content += """## 质量控制模式

"""
        for item in materials['quality_patterns']:
            md_content += f"""### {item['control_name']}
**来源**: {item['source']}

{item['mechanism']}

---

"""

        md_content += """## 约束策略

"""
        for item in materials['constraint_strategies']:
            md_content += f"""### {item['strategy_name']}
**来源**: {item['source']}

{item['approach']}

---

"""

        with open(output_dir / "ai_materials_library.md", 'w', encoding='utf-8') as f:
            f.write(md_content)

    def _save_statistics(self, output_dir: Path):
        """保存统计信息"""
        stats = {
            'total_presets': len(self.presets_data),
            'methodology_distribution': {
                dim: len(self.methodology_db.get(dim, []))
                for dim in self.DIMENSIONS.keys()
            },
            'technique_frequency': self._count_technique_frequency(),
            'top_prompts_by_length': self._get_top_prompts_by_length(),
            'parameter_ranges': self._analyze_parameter_ranges()
        }

        with open(output_dir / "statistics.json", 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    def _count_technique_frequency(self) -> Dict[str, int]:
        """统计技法使用频率"""
        freq = defaultdict(int)
        for preset in self.presets_data:
            for prompt in preset['prompts_analysis']:
                for tech in prompt['techniques_found']:
                    freq[tech] += 1
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True)[:20])

    def _get_top_prompts_by_length(self) -> List[Dict]:
        """获取最长的prompts（通常内容最丰富）"""
        all_prompts = []
        for preset in self.presets_data:
            for prompt in preset['prompts_analysis']:
                all_prompts.append({
                    'name': prompt['name'],
                    'source': preset['filename'],
                    'length': prompt['content_length'],
                    'summary': prompt['content_summary'][:100]
                })
        return sorted(all_prompts, key=lambda x: x['length'], reverse=True)[:10]

    def _analyze_parameter_ranges(self) -> Dict[str, Dict[str, float]]:
        """分析参数范围"""
        ranges = {}
        params_to_analyze = ['temperature', 'top_p', 'frequency_penalty']

        for param in params_to_analyze:
            values = [p['parameters'].get(param) for p in self.presets_data if param in p['parameters']]
            if values:
                ranges[param] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values)
                }

        return ranges


def main():
    analyzer = PresetAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()
