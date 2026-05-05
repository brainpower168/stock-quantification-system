#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量知识点提取器
从所有课本提取知识点
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


class BatchKnowledgeExtractor:
    """批量知识点提取器"""

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
        }

    def parse_chinese_number(self, text: str) -> int:
        """解析中文数字（支持组合数字如：二十一、三十等）"""
        if text in self.chinese_num_map:
            return self.chinese_num_map[text]

        # 处理组合数字
        result = 0
        if "十" in text:
            parts = text.split("十")
            if len(parts) == 2:
                # 二十、三十等
                tens = self.chinese_num_map.get(parts[0], 1) if parts[0] else 1
                ones = self.chinese_num_map.get(parts[1], 0) if parts[1] else 0
                result = tens * 10 + ones
        else:
            # 单个数字
            result = self.chinese_num_map.get(text, 0)

        return result

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

    def extract_keywords(self, text: str) -> List[str]:
        """从文本提取关键词"""
        # 移除标点符号和数字
        text = re.sub(r"[，。！？、；：" "' " "（）【】《》\d]+", " ", text)
        # 分词（简单按空格分）
        words = text.split()
        # 过滤停用词
        stopwords = {
            "的",
            "了",
            "是",
            "在",
            "有",
            "和",
            "与",
            "或",
            "等",
            "中",
            "为",
            "对",
            "这",
            "那",
            "它",
            "他",
            "她",
        }
        keywords = [w for w in words if len(w) >= 2 and w not in stopwords]
        return keywords[:10]  # 最多10个关键词

    def extract_from_markdown(
        self, md_file: Path, grade: int, semester: str
    ) -> List[KnowledgePoint]:
        """从Markdown文件提取知识点"""
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        knowledge_points = []

        # 先尝试按行分割处理
        lines = content.split("\n")

        # 检查是否所有内容都在少数几行中（PDF解析问题）
        if len(lines) < 100 and len(content) > 50000:
            # 使用全局搜索方式
            return self._extract_from_flat_content(content, grade, semester)

        # 正常按行处理
        return self._extract_from_lines(lines, grade, semester)

    def _extract_from_flat_content(
        self, content: str, grade: int, semester: str
    ) -> List[KnowledgePoint]:
        """从扁平内容中提取知识点（所有内容在少数几行中）"""
        knowledge_points = []

        # 查找所有章节（章节名称不包含数字，避免匹配到小节编号）
        chapter_pattern = (
            r"第([一二三四五六七八九十]+)章[ 　]([^\d１２３４５６７８９０第\n]+)"
        )
        chapters = list(re.finditer(chapter_pattern, content))

        for i, chapter_match in enumerate(chapters):
            chapter_num = self.parse_chinese_number(chapter_match.group(1))
            chapter_name = chapter_match.group(2).strip()

            # 获取该章节的内容范围
            start_pos = chapter_match.end()
            end_pos = chapters[i + 1].start() if i + 1 < len(chapters) else len(content)
            chapter_content = content[start_pos:end_pos]

            # 根据章节号构建小节正则
            # 例如：第七章 → 匹配 ７.１, ７.２ 等
            chapter_num_fullwidth = str(chapter_num).translate(
                str.maketrans("0123456789", "０１２３４５６７８９")
            )
            section_pattern = rf"{chapter_num_fullwidth}[．.]([０-９]+)[ 　]([^\d１２３４５６７８９０第\n]+)"

            # 在章节内容中查找小节
            sections = list(re.finditer(section_pattern, chapter_content))

            for j, section_match in enumerate(sections):
                section_num = self.fullwidth_to_normal(section_match.group(1))
                section_name = section_match.group(2).strip()

                # 获取小节内容
                section_start = section_match.end()
                section_end = (
                    sections[j + 1].start()
                    if j + 1 < len(sections)
                    else len(chapter_content)
                )
                section_content = chapter_content[section_start:section_end]

                # 创建知识点
                kp = self._create_knowledge_point(
                    chapter_num,
                    chapter_name,
                    section_num,
                    section_name,
                    section_content[:500],  # 限制长度
                    grade,
                    semester,
                )
                if kp:
                    knowledge_points.append(kp)

        return knowledge_points

    def _extract_from_lines(
        self, lines: List[str], grade: int, semester: str
    ) -> List[KnowledgePoint]:
        """从按行分割的内容中提取知识点"""
        knowledge_points = []

        current_chapter = ""
        current_chapter_num = 0
        current_section = ""
        current_section_num = ""
        section_content = []

        for i, line in enumerate(lines):
            # 检测章节标题（多种格式）
            # 格式1: 第一章　有理数（中文数字）
            chapter_match1 = re.search(
                r"第([一二三四五六七八九十]+)章[ 　](.+?)(?:\n|$)", line
            )
            # 格式2: 第７章　相交线与平行线（全角数字）
            chapter_match2 = re.search(r"第([０-９]+)章[ 　](.+?)(?:\n|$)", line)

            if chapter_match1:
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

                current_chapter_num = self.parse_chinese_number(chapter_match1.group(1))
                current_chapter = chapter_match1.group(2).strip()
                current_section = ""
                section_content = []
                continue

            if chapter_match2:
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
                    self.fullwidth_to_normal(chapter_match2.group(1))
                )
                current_chapter = chapter_match2.group(2).strip()
                current_section = ""
                section_content = []
                continue

            # 检测小节标题（多种格式）
            # 格式1: １．１ 正数和负数（全角数字+全角点）
            section_match1 = re.search(
                r"([０-９]+)．([０-９]+)[ 　](.+?)(?:\n|$)", line
            )
            # 格式2: ７．１　相交线（全角数字+半角点）
            section_match2 = re.search(
                r"([０-９]+)\.([０-９]+)[ 　](.+?)(?:\n|$)", line
            )
            # 格式3: 10.1 二元一次方程组的概念（半角数字）
            section_match3 = re.search(r"(\d+)\.(\d+)[ 　](.+?)(?:\n|$)", line)

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

        # 保存最后一节的内容
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
        """创建知识点对象"""
        if not chapter or not section:
            return None

        # 提取描述（前200字符）
        description = content.strip()[:200]

        # 提取关键词
        keywords = self.extract_keywords(content)

        # 创建知识点ID
        kp_id = f"{grade}-{chapter_num}-{section_num}"

        return KnowledgePoint(
            id=kp_id,
            name=section,
            grade=grade,
            semester=semester,
            chapter=chapter,
            section=section,
            description=description,
            keywords=keywords,
        )

    def extract_all_textbooks(
        self, textbooks_dir: Path
    ) -> Dict[str, List[KnowledgePoint]]:
        """提取所有课本的知识点"""
        results = {}

        # 课本配置
        textbooks = [
            ("七年级上册.md", 7, "上册"),
            ("七年级下册.md", 7, "下册"),
            ("八年级上册.md", 8, "上册"),
            ("八年级下册.md", 8, "下册"),
            ("九年级上册.md", 9, "上册"),
            ("九年级下册.md", 9, "下册"),
        ]

        for filename, grade, semester in textbooks:
            md_file = textbooks_dir / filename
            if md_file.exists():
                print(f"\n正在提取：{filename}")
                kps = self.extract_from_markdown(md_file, grade, semester)
                results[filename] = kps
                print(f"  提取知识点：{len(kps)} 个")
            else:
                print(f"⚠️ 文件不存在：{filename}")

        return results

    def save_results(self, results: Dict[str, List[KnowledgePoint]], output_dir: Path):
        """保存提取结果"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存每个课本的知识点
        for filename, kps in results.items():
            json_file = output_dir / f"{filename.replace('.md', '_知识点.json')}"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump([asdict(kp) for kp in kps], f, ensure_ascii=False, indent=2)
            print(f"✅ 已保存：{json_file}")

        # 保存汇总报告
        total = sum(len(kps) for kps in results.values())
        report_file = output_dir / "提取报告.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 知识点提取报告\n\n")
            f.write(f"总计提取知识点：**{total}** 个\n\n")

            f.write("## 按年级统计\n")
            for grade in [7, 8, 9]:
                count = sum(
                    len(kps) for fn, kps in results.items() if f"{grade}年级" in fn
                )
                f.write(f"- {grade}年级：{count} 个\n")

            f.write("\n## 按课本统计\n")
            for filename, kps in results.items():
                f.write(f"- {filename}：{len(kps)} 个\n")

        print(f"✅ 已保存报告：{report_file}")


def main():
    """主函数"""
    import sys

    # 默认路径
    textbooks_dir = Path("textbooks")
    output_dir = Path("textbooks")

    # 命令行参数
    if len(sys.argv) > 1:
        textbooks_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    print(f"课本目录：{textbooks_dir}")
    print(f"输出目录：{output_dir}")

    # 提取知识点
    extractor = BatchKnowledgeExtractor()
    results = extractor.extract_all_textbooks(textbooks_dir)

    # 保存结果
    extractor.save_results(results, output_dir)

    # 打印统计
    total = sum(len(kps) for kps in results.values())
    print(f"\n{'=' * 50}")
    print(f"总计提取知识点：{total} 个")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
