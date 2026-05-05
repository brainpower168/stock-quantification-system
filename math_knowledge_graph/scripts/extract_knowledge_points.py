#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识点提取器 - 从课本Markdown中提取知识点
目标：比探数蚁更详细的知识框架
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class KnowledgePoint:
    """知识点数据结构"""

    id: str  # 知识点ID，如 "8-16-1-1" (八年级第16章第1节第1个知识点)
    name: str  # 知识点名称
    grade: int  # 年级
    semester: str  # 学期（上册/下册）
    chapter: str  # 章节名称
    section: str  # 小节名称

    # 核心内容
    definition: str = ""  # 定义/概念
    formulas: List[str] = None  # 公式列表
    theorems: List[str] = None  # 定理列表
    properties: List[str] = None  # 性质列表

    # 例题习题
    examples: List[Dict] = None  # 例题列表
    exercises: List[Dict] = None  # 练习题列表

    # 学习指导
    key_points: List[str] = None  # 重点
    difficulties: List[str] = None  # 难点
    common_mistakes: List[str] = None  # 易错点
    learning_tips: List[str] = None  # 学习建议

    # 关联关系
    prerequisites: List[str] = None  # 前置知识点
    related_points: List[str] = None  # 相关知识点
    applications: List[str] = None  # 应用场景

    # 元数据
    difficulty_level: str = "基础"  # 难度等级：基础/中等/困难/竞赛
    importance: int = 3  # 重要程度：1-5
    exam_frequency: int = 3  # 考试频率：1-5

    def __post_init__(self):
        if self.formulas is None:
            self.formulas = []
        if self.theorems is None:
            self.theorems = []
        if self.properties is None:
            self.properties = []
        if self.examples is None:
            self.examples = []
        if self.exercises is None:
            self.exercises = []
        if self.key_points is None:
            self.key_points = []
        if self.difficulties is None:
            self.difficulties = []
        if self.common_mistakes is None:
            self.common_mistakes = []
        if self.learning_tips is None:
            self.learning_tips = []
        if self.prerequisites is None:
            self.prerequisites = []
        if self.related_points is None:
            self.related_points = []
        if self.applications is None:
            self.applications = []


class KnowledgeExtractor:
    """知识点提取器"""

    def __init__(self):
        self.knowledge_points = []
        self.chapter_pattern = re.compile(r"^第([一二三四五六七八九十]+)章[　\s]+(.+)$")
        self.section_pattern = re.compile(r"^(\d+\.\d+)[　\s]+(.+)$")
        self.subsection_pattern = re.compile(r"^(\d+\.\d+\.\d+)[　\s]+(.+)$")

    def extract_from_markdown(
        self, md_path: str, grade: int, semester: str
    ) -> List[KnowledgePoint]:
        """从Markdown文件提取知识点"""
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 按章节分割
        chapters = self._split_chapters(content)

        points = []
        for chapter_num, chapter_name, chapter_content in chapters:
            # 提取小节
            sections = self._split_sections(chapter_content)

            for section_num, section_name, section_content in sections:
                # 提取知识点
                section_points = self._extract_knowledge_points_from_section(
                    section_content,
                    grade,
                    semester,
                    chapter_name,
                    section_num,
                    section_name,
                )
                points.extend(section_points)

        return points

    def _split_chapters(self, content: str) -> List[Tuple[str, str, str]]:
        """分割章节"""
        chapters = []
        lines = content.split("\n")

        current_chapter_num = ""
        current_chapter_name = ""
        current_chapter_content = []

        for line in lines:
            match = self.chapter_pattern.match(line.strip())
            if match:
                # 保存上一章
                if current_chapter_num:
                    chapters.append(
                        (
                            current_chapter_num,
                            current_chapter_name,
                            "\n".join(current_chapter_content),
                        )
                    )

                # 开始新章节
                current_chapter_num = match.group(1)
                current_chapter_name = match.group(2).strip()
                current_chapter_content = []
            else:
                current_chapter_content.append(line)

        # 保存最后一章
        if current_chapter_num:
            chapters.append(
                (
                    current_chapter_num,
                    current_chapter_name,
                    "\n".join(current_chapter_content),
                )
            )

        return chapters

    def _split_sections(self, content: str) -> List[Tuple[str, str, str]]:
        """分割小节"""
        sections = []
        lines = content.split("\n")

        current_section_num = ""
        current_section_name = ""
        current_section_content = []

        for line in lines:
            match = self.section_pattern.match(line.strip())
            if match:
                # 保存上一小节
                if current_section_num:
                    sections.append(
                        (
                            current_section_num,
                            current_section_name,
                            "\n".join(current_section_content),
                        )
                    )

                # 开始新小节
                current_section_num = match.group(1)
                current_section_name = match.group(2).strip()
                current_section_content = []
            else:
                current_section_content.append(line)

        # 保存最后一小节
        if current_section_num:
            sections.append(
                (
                    current_section_num,
                    current_section_name,
                    "\n".join(current_section_content),
                )
            )

        return sections

    def _extract_knowledge_points_from_section(
        self,
        content: str,
        grade: int,
        semester: str,
        chapter_name: str,
        section_num: str,
        section_name: str,
    ) -> List[KnowledgePoint]:
        """从小节内容提取知识点"""
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
        point_id = f"{grade}-{section_num.replace('.', '-')}"

        # 如果有多个定义，拆分为多个知识点
        if definitions:
            for i, definition in enumerate(definitions):
                point = KnowledgePoint(
                    id=f"{point_id}-{i + 1}" if len(definitions) > 1 else point_id,
                    name=definition.get("name", section_name),
                    grade=grade,
                    semester=semester,
                    chapter=chapter_name,
                    section=section_name,
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
                id=point_id,
                name=section_name,
                grade=grade,
                semester=semester,
                chapter=chapter_name,
                section=section_name,
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

        # 匹配"XXX叫做XXX"、"XXX称为XXX"、"XXX是指XXX"等定义句式
        patterns = [
            r"([^。\n]{2,20})叫做([^。\n]{2,30})",
            r"([^。\n]{2,20})称为([^。\n]{2,30})",
            r"([^。\n]{2,20})是指([^。\n]{2,30})",
            r"([^。\n]{2,20})，即([^。\n]{2,30})",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
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

        # 匹配数学公式（简化版，实际需要更复杂的解析）
        # 匹配包含 =、≈、≤、≥ 等符号的行
        lines = content.split("\n")
        for line in lines:
            if any(symbol in line for symbol in ["＝", "≈", "≤", "≥", "=", "≤", "≥"]):
                # 清理公式
                formula = line.strip()
                if len(formula) > 3 and len(formula) < 100:
                    formulas.append(formula)

        return formulas

    def _extract_theorems(self, content: str) -> List[str]:
        """提取定理"""
        theorems = []

        # 匹配"XXX定理"、"XXX公式"、"XXX法则"等
        patterns = [
            r"([^。\n]{2,30}定理)",
            r"([^。\n]{2,30}公式)",
            r"([^。\n]{2,30}法则)",
            r"([^。\n]{2,30}性质)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            theorems.extend(matches)

        return list(set(theorems))

    def _extract_properties(self, content: str) -> List[str]:
        """提取性质"""
        properties = []

        # 匹配"XXX具有以下性质"、"XXX的性质"等
        pattern = r"([^。\n]{2,30})的性质[：:]"
        matches = re.findall(pattern, content)
        properties.extend(matches)

        return properties

    def _extract_examples(self, content: str) -> List[Dict]:
        """提取例题"""
        examples = []

        # 匹配"例1"、"例2"等
        pattern = r"例\s*(\d+)[　\s]+([^例]+?)(?=例\s*\d+|$)"
        matches = re.findall(pattern, content, re.DOTALL)

        for num, example_content in matches:
            examples.append(
                {"number": int(num), "content": example_content.strip(), "type": "例题"}
            )

        return examples

    def _extract_exercises(self, content: str) -> List[Dict]:
        """提取练习题"""
        exercises = []

        # 匹配题号
        pattern = r"(\d+)[\.、．]\s*([^0-9]+?)(?=\d+[\.、．]|$)"
        matches = re.findall(pattern, content)

        for num, exercise_content in matches:
            if len(exercise_content.strip()) > 5:  # 过滤太短的内容
                exercises.append(
                    {
                        "number": int(num),
                        "content": exercise_content.strip(),
                        "type": "练习题",
                    }
                )

        return exercises[:20]  # 限制数量

    def save_to_json(self, points: List[KnowledgePoint], output_path: str):
        """保存为JSON"""
        data = [asdict(p) for p in points]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def generate_report(self, points: List[KnowledgePoint]) -> str:
        """生成提取报告"""
        report = []
        report.append("# 知识点提取报告\n")
        report.append(f"总计提取知识点：{len(points)} 个\n")

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

        report.append("\n## 题目统计\n")
        report.append(f"- 例题总数：{total_examples} 道\n")
        report.append(f"- 练习题总数：{total_exercises} 道\n")

        return "".join(report)


def main():
    """主函数"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python extract_knowledge_points.py <课本markdown文件>")
        print("示例: python extract_knowledge_points.py 八年级下册.md")
        sys.exit(1)

    md_path = sys.argv[1]

    # 从文件名推断年级和学期
    filename = Path(md_path).stem

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

    extractor = KnowledgeExtractor()
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

    print(f"\n知识点已保存到：{output_json}")
    print(f"提取报告已保存到：{report_path}")


if __name__ == "__main__":
    main()
