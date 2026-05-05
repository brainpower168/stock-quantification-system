#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识点提取器 最终版
支持多种课本格式
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

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.formulas is None:
            self.formulas = []
        if self.examples is None:
            self.examples = []
        if self.exercises is None:
            self.exercises = []


class KnowledgeExtractorFinal:
    """知识点提取器 最终版"""

    def __init__(self):
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

        # 查找所有章节标题
        lines = content.split("\n")
        current_chapter = ""
        current_chapter_num = 0
        current_section = ""
        current_section_num = ""
        section_content = []

        for i, line in enumerate(lines):
            # 检测章节标题（多种格式）
            # 格式1: 第一章　有理数（中文数字）
            chapter_match1 = re.match(
                r"第([一二三四五六七八九十]+)章[ 　](.+?)(?:\n|$)", line
            )
            # 格式2: 第七章　相交线与平行线（中文数字）
            chapter_match2 = re.match(
                r"第([一二三四五六七八九十]+)章[ 　](.+?)(?:\n|$)", line
            )
            # 格式3: 第７章　相交线与平行线（全角数字）
            chapter_match3 = re.match(r"第([０-９]+)章[ 　](.+?)(?:\n|$)", line)

            if chapter_match1 or chapter_match2:
                # 保存上一节的内容
                if current_section and section_content:
                    kp = self._create_knowledge_point(
                        current_chapter_num,
                        current_chapter,
                        current_section_num,
                        current_section,
                        "\n".join(section_content),
                        grade,
                        semester,
                    )
                    if kp:
                        knowledge_points.append(kp)

                match = chapter_match1 or chapter_match2
                current_chapter_num = self.chinese_num_map.get(match.group(1), 0)
                current_chapter = match.group(2).strip()
                current_section = ""
                section_content = []
                continue

            if chapter_match3:
                # 保存上一节的内容
                if current_section and section_content:
                    kp = self._create_knowledge_point(
                        current_chapter_num,
                        current_chapter,
                        current_section_num,
                        current_section,
                        "\n".join(section_content),
                        grade,
                        semester,
                    )
                    if kp:
                        knowledge_points.append(kp)

                current_chapter_num = int(
                    self.fullwidth_to_normal(chapter_match3.group(1))
                )
                current_chapter = chapter_match3.group(2).strip()
                current_section = ""
                section_content = []
                continue

            # 检测小节标题（多种格式）
            # 格式1: １．１ 正数和负数
            section_match1 = re.match(r"([０-９]+)．([０-９]+)[ 　](.+?)(?:\n|$)", line)
            # 格式2: ７．１　相交线
            section_match2 = re.match(
                r"([０-９]+)\\.([０-９]+)[ 　](.+?)(?:\n|$)", line
            )
            # 格式3: 10.1 二元一次方程组的概念
            section_match3 = re.match(r"(\d+)\.(\d+)[ 　](.+?)(?:\n|$)", line)

            if section_match1 or section_match2 or section_match3:
                # 保存上一节的内容
                if current_section and section_content:
                    kp = self._create_knowledge_point(
                        current_chapter_num,
                        current_chapter,
                        current_section_num,
                        current_section,
                        "\n".join(section_content),
                        grade,
                        semester,
                    )
                    if kp:
                        knowledge_points.append(kp)

                match = section_match1 or section_match2 or section_match3
                current_section_num = self.fullwidth_to_normal(match.group(2))
                current_section = match.group(3).strip()
                section_content = []
                continue

            # 收集小节内容
            if current_section:
                section_content.append(line)

        # 保存最后一节
        if current_section and section_content:
            kp = self._create_knowledge_point(
                current_chapter_num,
                current_chapter,
                current_section_num,
                current_section,
                "\n".join(section_content),
                grade,
                semester,
            )
            if kp:
                knowledge_points.append(kp)

        return knowledge_points

    def _create_knowledge_point(
        self,
        chapter_num: int,
        chapter: str,
        section_num: str,
        section: str,
        content: str,
        grade: int,
        semester: str,
    ) -> KnowledgePoint:
        """创建知识点"""
        if not chapter or not section:
            return None

        # 生成ID
        kp_id = f"{grade}-{chapter_num}-{section_num}"

        # 提取例题
        examples = self._extract_examples(content)

        # 提取关键词
        keywords = self._extract_keywords(section, content)

        # 提取描述
        description = self._extract_description(content)

        return KnowledgePoint(
            id=kp_id,
            name=section,
            grade=grade,
            semester=semester,
            chapter=chapter,
            section=section,
            description=description,
            keywords=keywords,
            examples=examples,
        )

    def _extract_examples(self, content: str) -> List[str]:
        """提取例题"""
        examples = []
        # 例题模式
        example_pattern = re.compile(
            r"例[０-９１２３４５６７８９\d]+\s*(.+?)(?=\n\s*解[：:]|\n\n|$)", re.DOTALL
        )
        matches = example_pattern.findall(content)
        for match in matches[:5]:
            example = self.fullwidth_to_normal(match.strip())
            example = re.sub(r"\s+", " ", example)
            if len(example) > 10:
                examples.append(example)
        return examples

    def _extract_keywords(self, title: str, content: str) -> List[str]:
        """提取关键词"""
        keywords = []

        # 从标题提取
        title_keywords = re.findall(r"[\u4e00-\u9fa5]{2,6}", title)
        keywords.extend(title_keywords)

        # 常见关键词
        common_keywords = [
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
            "方程",
            "函数",
            "不等式",
            "几何",
            "图形",
            "角",
            "线",
            "面",
            "数",
            "式",
            "方程组",
            "坐标系",
            "概率",
            "统计",
        ]

        for keyword in common_keywords:
            if keyword in content:
                keywords.append(keyword)

        return list(set(keywords))[:10]

    def _extract_description(self, content: str) -> str:
        """提取知识点描述"""
        lines = content.split("\n")
        desc_lines = []
        total_len = 0

        for line in lines[:20]:  # 只看前20行
            line = line.strip()
            if (
                line
                and not line.startswith("图")
                and not line.startswith("表")
                and len(line) > 5
            ):
                desc_lines.append(line)
                total_len += len(line)
                if total_len > 200:
                    break

        description = " ".join(desc_lines)
        description = self.fullwidth_to_normal(description)
        description = re.sub(r"\s+", " ", description)

        return description[:300]

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

        report.append("\n## 内容统计")
        report.append(f"- 例题总数：{total_examples} 道")

        # 示例知识点
        report.append("\n## 示例知识点（前5个）")
        for kp in knowledge_points[:5]:
            report.append(f"\n### {kp.id} {kp.name}")
            report.append(f"- 章节：{kp.chapter}")
            report.append(f"- 描述：{kp.description[:100]}...")
            if kp.keywords:
                report.append(f"- 关键词：{', '.join(kp.keywords[:5])}")

        return "\n".join(report)


def main():
    import sys

    if len(sys.argv) < 2:
        print("用法: python extract_knowledge_final.py <课本markdown文件>")
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
        grade, semester = 7, "上册"

    print(f"正在提取知识点：{filename}")
    print(f"年级：{grade}，学期：{semester}")

    extractor = KnowledgeExtractorFinal()
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
