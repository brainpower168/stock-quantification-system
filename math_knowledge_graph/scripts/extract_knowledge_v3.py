#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识点提取器 v3.0
针对人教版初中数学课本Markdown格式优化
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class KnowledgePoint:
    """知识点数据结构"""

    id: str
    name: str
    grade: int
    semester: str
    chapter: str
    section: str
    description: str = ""
    difficulty: int = 3
    keywords: List[str] = None
    formulas: List[str] = None
    examples: List[str] = None
    exercises: List[str] = None
    prerequisites: List[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.formulas is None:
            self.formulas = []
        if self.examples is None:
            self.examples = []
        if self.exercises is None:
            self.exercises = []
        if self.prerequisites is None:
            self.prerequisites = []


class KnowledgeExtractorV3:
    """知识点提取器 v3.0"""

    def __init__(self):
        # 章节标题模式（全角字符）
        self.chapter_pattern = re.compile(
            r"第([一二三四五六七八九十]+)章[ 　](.+?)(?:\n|$)"
        )
        self.section_pattern = re.compile(r"([０-９]+)．([０-９]+)[ 　](.+?)(?:\n|$)")

        # 知识点关键词
        self.knowledge_keywords = [
            "定义",
            "概念",
            "定理",
            "公理",
            "公式",
            "法则",
            "性质",
            "规律",
            "方法",
            "步骤",
            "运算",
            "计算",
            "证明",
            "判定",
            "条件",
            "结论",
        ]

        # 例题模式
        self.example_pattern = re.compile(
            r"例[０-９１２３４５６７８９]+\s*(.+?)(?=\n\s*解：|\n\s*解:|\n\n|$)",
            re.DOTALL,
        )

        # 练习模式
        self.exercise_pattern = re.compile(
            r"(\d+)\.\s*(.+?)(?=\n\d+\.|\n\n|$)", re.DOTALL
        )

        # 公式模式
        self.formula_pattern = re.compile(
            r"[a-zA-Z]+\s*=\s*[^，。；\n]+|[a-zA-Z]+\([a-zA-Z,]+\)\s*=\s*[^，。；\n]+"
        )

        # 中文数字映射
        self.chinese_num_map = {
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
        }

        # 全角数字映射
        self.fullwidth_num_map = {
            "０": "0",
            "１": "1",
            "２": "2",
            "３": "3",
            "４": "4",
            "５": "5",
            "６": "6",
            "７": "7",
            "８": "8",
            "９": "9",
        }

    def chinese_to_arabic(self, chinese_num: str) -> int:
        """中文数字转阿拉伯数字"""
        return self.chinese_num_map.get(chinese_num, 0)

    def fullwidth_to_normal(self, text: str) -> str:
        """全角字符转半角"""
        result = []
        for char in text:
            if char in self.fullwidth_num_map:
                result.append(self.fullwidth_num_map[char])
            elif char == "．":
                result.append(".")
            elif char == "　":
                result.append(" ")
            else:
                result.append(char)
        return "".join(result)

    def extract_from_markdown(
        self, md_file: Path, grade: int, semester: str
    ) -> List[KnowledgePoint]:
        """从Markdown文件提取知识点"""
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        knowledge_points = []

        # 按章节分割
        chapters = self._split_chapters(content)

        for chapter_num, chapter_title, chapter_content in chapters:
            # 按小节分割
            sections = self._split_sections(chapter_content, chapter_num)

            for section_num, section_title, section_content in sections:
                # 提取知识点
                kps = self._extract_knowledge_from_section(
                    chapter_num,
                    chapter_title,
                    section_num,
                    section_title,
                    section_content,
                    grade,
                    semester,
                )
                knowledge_points.extend(kps)

        return knowledge_points

    def _split_chapters(self, content: str) -> List[tuple]:
        """分割章节"""
        chapters = []
        matches = list(self.chapter_pattern.finditer(content))

        for i, match in enumerate(matches):
            chapter_num = self.chinese_to_arabic(match.group(1))
            chapter_title = match.group(2).strip()

            # 获取章节内容（到下一章节开始）
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            chapter_content = content[start:end]

            chapters.append((chapter_num, chapter_title, chapter_content))

        return chapters

    def _split_sections(self, content: str, chapter_num: int) -> List[tuple]:
        """分割小节"""
        sections = []
        matches = list(self.section_pattern.finditer(content))

        for i, match in enumerate(matches):
            section_num_str = self.fullwidth_to_normal(match.group(2))
            section_title = match.group(3).strip()

            # 获取小节内容
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start:end]

            sections.append((section_num_str, section_title, section_content))

        return sections

    def _extract_knowledge_from_section(
        self,
        chapter_num: int,
        chapter_title: str,
        section_num: str,
        section_title: str,
        section_content: str,
        grade: int,
        semester: str,
    ) -> List[KnowledgePoint]:
        """从小节提取知识点"""
        knowledge_points = []

        # 生成知识点ID
        kp_id = f"{grade}-{chapter_num}-{section_num}"

        # 提取例题
        examples = self._extract_examples(section_content)

        # 提取练习题
        exercises = self._extract_exercises(section_content)

        # 提取公式
        formulas = self._extract_formulas(section_content)

        # 提取关键词
        keywords = self._extract_keywords(section_title, section_content)

        # 提取描述
        description = self._extract_description(section_content)

        # 创建知识点
        kp = KnowledgePoint(
            id=kp_id,
            name=section_title,
            grade=grade,
            semester=semester,
            chapter=chapter_title,
            section=section_title,
            description=description,
            keywords=keywords,
            formulas=formulas,
            examples=examples,
            exercises=exercises,
        )

        knowledge_points.append(kp)

        # 尝试提取子知识点（如定理、性质等）
        sub_kps = self._extract_sub_knowledge(
            kp_id, section_content, grade, semester, chapter_title, section_title
        )
        knowledge_points.extend(sub_kps)

        return knowledge_points

    def _extract_examples(self, content: str) -> List[str]:
        """提取例题"""
        examples = []
        matches = self.example_pattern.findall(content)
        for match in matches:
            # 清理格式
            example = self.fullwidth_to_normal(match.strip())
            example = re.sub(r"\s+", " ", example)
            if len(example) > 10:  # 过滤太短的内容
                examples.append(example)
        return examples[:5]  # 最多5个例题

    def _extract_exercises(self, content: str) -> List[str]:
        """提取练习题"""
        exercises = []
        matches = self.exercise_pattern.findall(content)
        for num, text in matches[:10]:  # 最多10个练习题
            exercise = self.fullwidth_to_normal(text.strip())
            exercise = re.sub(r"\s+", " ", exercise)
            if len(exercise) > 5:
                exercises.append(exercise)
        return exercises

    def _extract_formulas(self, content: str) -> List[str]:
        """提取公式"""
        formulas = []
        matches = self.formula_pattern.findall(content)
        for formula in matches[:10]:  # 最多10个公式
            formula = formula.strip()
            if len(formula) > 3:
                formulas.append(formula)
        return formulas

    def _extract_keywords(self, title: str, content: str) -> List[str]:
        """提取关键词"""
        keywords = []

        # 从标题提取
        title_keywords = re.findall(r"[\u4e00-\u9fa5]{2,4}", title)
        keywords.extend(title_keywords)

        # 从内容提取
        for keyword in self.knowledge_keywords:
            if keyword in content:
                keywords.append(keyword)

        return list(set(keywords))[:10]  # 去重，最多10个

    def _extract_description(self, content: str) -> str:
        """提取知识点描述"""
        # 取前200个字符作为描述
        lines = content.split("\n")
        desc_lines = []
        total_len = 0

        for line in lines:
            line = line.strip()
            if line and not line.startswith("图") and not line.startswith("表"):
                desc_lines.append(line)
                total_len += len(line)
                if total_len > 200:
                    break

        description = " ".join(desc_lines)
        description = self.fullwidth_to_normal(description)
        description = re.sub(r"\s+", " ", description)

        return description[:300]  # 最多300字符

    def _extract_sub_knowledge(
        self,
        parent_id: str,
        content: str,
        grade: int,
        semester: str,
        chapter: str,
        section: str,
    ) -> List[KnowledgePoint]:
        """提取子知识点（定理、性质、公式等）"""
        sub_kps = []

        # 定理模式
        theorem_pattern = re.compile(r"([^\n]{2,20}(?:定理|公理|性质|法则|公式)[^\n]*)")
        theorems = theorem_pattern.findall(content)

        for i, theorem in enumerate(theorems[:5]):  # 最多5个子知识点
            theorem = theorem.strip()
            if len(theorem) > 5:
                sub_kp = KnowledgePoint(
                    id=f"{parent_id}-{i + 1}",
                    name=theorem,
                    grade=grade,
                    semester=semester,
                    chapter=chapter,
                    section=section,
                    description=theorem,
                    keywords=[
                        theorem.split("定理")[0]
                        .split("公理")[0]
                        .split("性质")[0]
                        .strip()
                    ],
                )
                sub_kps.append(sub_kp)

        return sub_kps

    def save_to_json(self, knowledge_points: List[KnowledgePoint], output_file: Path):
        """保存为JSON"""
        data = [asdict(kp) for kp in knowledge_points]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def generate_report(self, knowledge_points: List[KnowledgePoint]) -> str:
        """生成提取报告"""
        report = []
        report.append("# 知识点提取报告")
        report.append(f"总计提取知识点：**{len(knowledge_points)}** 个\n")

        # 按年级统计
        report.append("## 按年级统计")
        grade_count = {}
        for kp in knowledge_points:
            grade_count[kp.grade] = grade_count.get(kp.grade, 0) + 1
        for grade, count in sorted(grade_count.items()):
            report.append(f"- {grade}年级：{count} 个知识点")

        # 按章节统计
        report.append("\n## 按章节统计")
        chapter_count = {}
        for kp in knowledge_points:
            key = f"{kp.chapter}"
            chapter_count[key] = chapter_count.get(key, 0) + 1
        for chapter, count in sorted(chapter_count.items()):
            report.append(f"- {chapter}：{count} 个知识点")

        # 内容统计
        total_examples = sum(len(kp.examples) for kp in knowledge_points)
        total_exercises = sum(len(kp.exercises) for kp in knowledge_points)
        total_formulas = sum(len(kp.formulas) for kp in knowledge_points)

        report.append("\n## 内容统计")
        report.append(f"- 例题总数：{total_examples} 道")
        report.append(f"- 练习题总数：{total_exercises} 道")
        report.append(f"- 公式总数：{total_formulas} 个")

        # 示例知识点
        report.append("\n## 示例知识点（前5个）")
        for kp in knowledge_points[:5]:
            report.append(f"\n### {kp.id} {kp.name}")
            report.append(f"- 章节：{kp.chapter} - {kp.section}")
            report.append(f"- 描述：{kp.description[:100]}...")
            if kp.keywords:
                report.append(f"- 关键词：{', '.join(kp.keywords[:5])}")
            if kp.formulas:
                report.append(f"- 公式：{', '.join(kp.formulas[:3])}")

        return "\n".join(report)


def main():
    import sys

    if len(sys.argv) < 2:
        print("用法: python extract_knowledge_v3.py <课本markdown文件>")
        sys.exit(1)

    md_file = Path(sys.argv[1])
    if not md_file.exists():
        print(f"文件不存在: {md_file}")
        sys.exit(1)

    # 从文件名推断年级和学期
    filename = md_file.name
    if "七年级上册" in filename:
        grade, semester = 7, "上册"
    elif "七年级下册" in filename:
        grade, semester = 7, "下册"
    elif "八年级上册" in filename:
        grade, semester = 8, "上册"
    elif "八年级下册" in filename:
        grade, semester = 8, "下册"
    elif "九年级上册" in filename:
        grade, semester = 9, "上册"
    elif "九年级下册" in filename:
        grade, semester = 9, "下册"
    else:
        grade, semester = 7, "上册"  # 默认

    print(f"正在提取知识点：{filename}")
    print(f"年级：{grade}，学期：{semester}")

    extractor = KnowledgeExtractorV3()
    knowledge_points = extractor.extract_from_markdown(md_file, grade, semester)

    # 保存结果
    output_json = md_file.parent / f"{md_file.stem}_知识点.json"
    extractor.save_to_json(knowledge_points, output_json)

    # 生成报告
    report = extractor.generate_report(knowledge_points)
    report_file = md_file.parent / f"{md_file.stem}_提取报告.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"\n✅ 知识点已保存到：{output_json}")
    print(f"✅ 提取报告已保存到：{report_file}")


if __name__ == "__main__":
    main()
