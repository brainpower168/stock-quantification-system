#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能知识点提取器 - 使用规则+启发式方法提取知识点
目标：比探数蚁更详细的知识框架
"""

import re
import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, asdict, field
from collections import defaultdict


@dataclass
class KnowledgePoint:
    """知识点数据结构"""

    id: str
    name: str
    grade: int
    semester: str
    chapter: str
    section: str

    # 核心内容
    definition: str = ""
    formulas: List[str] = field(default_factory=list)
    theorems: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)

    # 例题习题
    examples: List[Dict] = field(default_factory=list)
    exercises: List[Dict] = field(default_factory=list)

    # 学习指导
    key_points: List[str] = field(default_factory=list)
    difficulties: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)

    # 关联关系
    prerequisites: List[str] = field(default_factory=list)
    related_points: List[str] = field(default_factory=list)

    # 元数据
    difficulty_level: str = "基础"
    importance: int = 3
    exam_frequency: int = 3


class SmartKnowledgeExtractor:
    """智能知识点提取器"""

    def __init__(self):
        self.knowledge_points = []

        # 章节模式（匹配"第十六章　二次根式"）
        self.chapter_pattern = re.compile(
            r"第([一二三四五六七八九十]+)章[　\s]+(.+?)(?=\d+\.|$)"
        )

        # 小节模式（匹配"16.1　二次根式"）
        self.section_pattern = re.compile(
            r"(\d+)\.(\d+)[　\s]+([^第]+?)(?=\d+\.\d+|习题|复习题|小结|阅读与思考|$)"
        )

        # 定义模式
        self.definition_patterns = [
            r"一般地[，,]([^。\n]{5,50})叫做([^。\n]{2,30})",
            r"我们把([^。\n]{5,50})叫做([^。\n]{2,30})",
            r"([^。\n]{2,30})是指([^。\n]{5,50})",
            r"如果[^。\n]{5,50}，那么[^。\n]{5,50}叫做([^。\n]{2,30})",
        ]

        # 定理模式
        self.theorem_patterns = [
            r"([^。\n]{2,30}定理)",
            r"([^。\n]{2,30}公式)",
            r"([^。\n]{2,30}法则)",
            r"命题\s*(\d+)[：:]([^。\n]{10,100})",
        ]

        # 例题模式
        self.example_pattern = re.compile(
            r"例\s*(\d+)[　\s]+(.*?)(?=例\s*\d+|解[：:]|$)", re.DOTALL
        )

    def extract_from_markdown(
        self, md_path: str, grade: int, semester: str
    ) -> List[KnowledgePoint]:
        """从Markdown文件提取知识点"""
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 清理内容
        content = self._clean_content(content)

        # 提取章节
        chapters = self._extract_chapters(content)

        points = []
        point_counter = 0

        for chapter_num, chapter_name, chapter_content in chapters:
            # 提取小节
            sections = self._extract_sections(chapter_content, chapter_num)

            for section_num, section_name, section_content in sections:
                # 提取知识点
                section_points = self._extract_knowledge_points(
                    section_content,
                    grade,
                    semester,
                    chapter_name,
                    section_num,
                    section_name,
                )

                # 重新编号
                for point in section_points:
                    point_counter += 1
                    point.id = f"{grade}-{chapter_num}-{section_num}-{point_counter}"

                points.extend(section_points)

        return points

    def _clean_content(self, content: str) -> str:
        """清理内容"""
        # 移除多余空白
        content = re.sub(r"\n{3,}", "\n\n", content)
        # 移除特殊字符
        content = content.replace("", "")
        return content

    def _extract_chapters(self, content: str) -> List[tuple]:
        """提取章节"""
        chapters = []

        # 查找所有章节标题
        chapter_matches = list(self.chapter_pattern.finditer(content))

        for i, match in enumerate(chapter_matches):
            chapter_num = self._chinese_to_number(match.group(1))
            chapter_name = match.group(2).strip()

            # 获取章节内容（从当前匹配到下一个章节或文件结束）
            start = match.end()
            if i + 1 < len(chapter_matches):
                end = chapter_matches[i + 1].start()
            else:
                end = len(content)

            chapter_content = content[start:end]

            chapters.append((chapter_num, chapter_name, chapter_content))

        return chapters

    def _extract_sections(self, content: str, chapter_num: int) -> List[tuple]:
        """提取小节"""
        sections = []

        # 查找所有小节
        section_matches = list(self.section_pattern.finditer(content))

        for i, match in enumerate(section_matches):
            section_num = int(match.group(2))
            section_name = match.group(3).strip()

            # 获取小节内容
            start = match.end()
            if i + 1 < len(section_matches):
                end = section_matches[i + 1].start()
            else:
                end = len(content)

            section_content = content[start:end]

            sections.append((section_num, section_name, section_content))

        return sections

    def _extract_knowledge_points(
        self,
        content: str,
        grade: int,
        semester: str,
        chapter_name: str,
        section_num: int,
        section_name: str,
    ) -> List[KnowledgePoint]:
        """提取知识点"""
        points = []

        # 提取定义
        definitions = self._extract_definitions(content)

        # 提取公式
        formulas = self._extract_formulas(content)

        # 提取定理
        theorems = self._extract_theorems(content)

        # 提取性质
        properties = self._extract_properties(content)

        # 提取例题
        examples = self._extract_examples(content)

        # 提取练习题
        exercises = self._extract_exercises(content)

        # 创建知识点
        if definitions:
            for i, definition in enumerate(definitions):
                point = KnowledgePoint(
                    id="",  # 后续设置
                    name=definition.get("name", section_name),
                    grade=grade,
                    semester=semester,
                    chapter=chapter_name,
                    section=f"{section_num}.{section_name}",
                    definition=definition.get("content", ""),
                    formulas=formulas if i == 0 else [],
                    theorems=theorems if i == 0 else [],
                    properties=properties if i == 0 else [],
                    examples=examples,
                    exercises=exercises,
                )
                points.append(point)
        else:
            # 没有明确定义，创建一个通用知识点
            point = KnowledgePoint(
                id="",  # 后续设置
                name=section_name,
                grade=grade,
                semester=semester,
                chapter=chapter_name,
                section=f"{section_num}.{section_name}",
                formulas=formulas,
                theorems=theorems,
                properties=properties,
                examples=examples,
                exercises=exercises,
            )
            points.append(point)

        return points

    def _extract_definitions(self, content: str) -> List[Dict]:
        """提取定义"""
        definitions = []

        for pattern in self.definition_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    # 定义模式匹配
                    if len(match) == 2:
                        definitions.append(
                            {
                                "name": match[1].strip(),
                                "content": f"{match[0].strip()}叫做{match[1].strip()}",
                            }
                        )

        return definitions

    def _extract_formulas(self, content: str) -> List[str]:
        """提取公式"""
        formulas = []

        # 匹配包含数学符号的行
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            # 包含等号、根号等数学符号
            if any(
                symbol in line for symbol in ["＝", "≈", "≤", "≥", "=", "≤", "≥", "槡"]
            ):
                # 长度适中
                if 5 < len(line) < 100:
                    formulas.append(line)

        return formulas[:10]  # 限制数量

    def _extract_theorems(self, content: str) -> List[str]:
        """提取定理"""
        theorems = []

        for pattern in self.theorem_patterns:
            matches = re.findall(pattern, content)
            theorems.extend(matches)

        return list(set(theorems))[:10]

    def _extract_properties(self, content: str) -> List[str]:
        """提取性质"""
        properties = []

        # 匹配"XXX的性质"
        pattern = r"([^。\n]{2,30})的性质"
        matches = re.findall(pattern, content)
        properties.extend(matches)

        return list(set(properties))[:10]

    def _extract_examples(self, content: str) -> List[Dict]:
        """提取例题"""
        examples = []

        matches = self.example_pattern.findall(content)
        for num, example_content in matches:
            example_content = example_content.strip()
            if len(example_content) > 10:
                examples.append(
                    {
                        "number": int(num),
                        "content": example_content[:500],  # 限制长度
                        "type": "例题",
                    }
                )

        return examples[:20]

    def _extract_exercises(self, content: str) -> List[Dict]:
        """提取练习题"""
        exercises = []

        # 匹配题号
        pattern = r"(\d+)[\.、．]\s*([^0-9\n]{10,200})"
        matches = re.findall(pattern, content)

        for num, exercise_content in matches:
            exercise_content = exercise_content.strip()
            if len(exercise_content) > 10:
                exercises.append(
                    {"number": int(num), "content": exercise_content, "type": "练习题"}
                )

        return exercises[:30]

    def _chinese_to_number(self, chinese: str) -> int:
        """中文数字转阿拉伯数字"""
        mapping = {
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
            "十一": 11,
            "十二": 12,
            "十三": 13,
            "十四": 14,
            "十五": 15,
            "十六": 16,
            "十七": 17,
            "十八": 18,
            "十九": 19,
            "二十": 20,
        }
        return mapping.get(chinese, 0)

    def save_to_json(self, points: List[KnowledgePoint], output_path: str):
        """保存为JSON"""
        data = [asdict(p) for p in points]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def generate_report(self, points: List[KnowledgePoint]) -> str:
        """生成提取报告"""
        report = []
        report.append("# 知识点提取报告\n")
        report.append(f"总计提取知识点：**{len(points)}** 个\n")

        # 按年级统计
        grade_stats = defaultdict(int)
        for p in points:
            grade_stats[p.grade] += 1

        report.append("\n## 按年级统计\n")
        for grade in sorted(grade_stats.keys()):
            report.append(f"- {grade}年级：{grade_stats[grade]} 个知识点\n")

        # 按章节统计
        chapter_stats = defaultdict(int)
        for p in points:
            chapter_stats[p.chapter] += 1

        report.append("\n## 按章节统计\n")
        for chapter, count in sorted(chapter_stats.items(), key=lambda x: -x[1]):
            report.append(f"- {chapter}：{count} 个知识点\n")

        # 统计例题和练习题
        total_examples = sum(len(p.examples) for p in points)
        total_exercises = sum(len(p.exercises) for p in points)
        total_formulas = sum(len(p.formulas) for p in points)
        total_theorems = sum(len(p.theorems) for p in points)

        report.append("\n## 内容统计\n")
        report.append(f"- 例题总数：{total_examples} 道\n")
        report.append(f"- 练习题总数：{total_exercises} 道\n")
        report.append(f"- 公式总数：{total_formulas} 个\n")
        report.append(f"- 定理总数：{total_theorems} 个\n")

        # 示例知识点
        report.append("\n## 示例知识点（前5个）\n")
        for i, p in enumerate(points[:5]):
            report.append(f"\n### {i + 1}. {p.name}\n")
            report.append(f"- 章节：{p.chapter} - {p.section}\n")
            if p.definition:
                report.append(f"- 定义：{p.definition[:100]}...\n")
            if p.formulas:
                report.append(f"- 公式：{', '.join(p.formulas[:3])}\n")
            if p.examples:
                report.append(f"- 例题数：{len(p.examples)} 道\n")

        return "".join(report)


def main():
    """主函数"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python smart_knowledge_extractor.py <课本markdown文件>")
        sys.exit(1)

    md_path = sys.argv[1]
    filename = Path(md_path).stem

    # 从文件名推断年级和学期
    if "七年级" in filename:
        grade = 7
    elif "八年级" in filename:
        grade = 8
    elif "九年级" in filename:
        grade = 9
    else:
        grade = 0

    if "上册" in filename:
        semester = "上册"
    elif "下册" in filename:
        semester = "下册"
    else:
        semester = "未知"

    print(f"正在提取知识点：{filename}")
    print(f"年级：{grade}，学期：{semester}")

    extractor = SmartKnowledgeExtractor()
    points = extractor.extract_from_markdown(md_path, grade, semester)

    # 保存结果
    output_json = f"{filename}_知识点.json"
    extractor.save_to_json(points, output_json)

    # 生成报告
    report = extractor.generate_report(points)
    print(report)

    # 保存报告
    report_path = f"{filename}_提取报告.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✅ 知识点已保存到：{output_json}")
    print(f"✅ 提取报告已保存到：{report_path}")


if __name__ == "__main__":
    main()
