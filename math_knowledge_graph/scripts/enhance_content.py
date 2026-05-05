#!/usr/bin/env python3
"""
知识点内容增强器
从课本Markdown文件中提取详细内容，补充到知识点JSON中
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class KnowledgeContent:
    """知识点内容"""

    explanation: str = ""  # 讲解
    examples: List[Dict[str, str]] = field(default_factory=list)  # 例题
    exercises: List[str] = field(default_factory=list)  # 练习题
    formulas: List[str] = field(default_factory=list)  # 公式
    key_points: List[str] = field(default_factory=list)  # 要点
    common_mistakes: List[str] = field(default_factory=list)  # 常见错误
    applications: List[str] = field(default_factory=list)  # 应用场景
    history: str = ""  # 数学历史


class ContentEnhancer:
    """知识点内容增强器"""

    def __init__(self, textbooks_dir: str = "textbooks"):
        self.textbooks_dir = Path(textbooks_dir)

    def extract_section_content(
        self, md_file: Path, chapter: str, section: str
    ) -> Optional[str]:
        """提取章节内容"""
        content = md_file.read_text(encoding="utf-8")

        # 查找章节标题
        # 格式：１．１　正数和负数 或 １．１ 正数和负数
        section_pattern = rf"{re.escape(section)}.*?(?=\n\d+\.\d+|\n第|\n综合与实践|\Z)"
        match = re.search(section_pattern, content, re.DOTALL)

        if match:
            return match.group(0)
        return None

    def parse_examples(self, content: str) -> List[Dict[str, str]]:
        """解析例题"""
        examples = []
        # 匹配：例１　题目
        pattern = r"例(\d+)　(.*?)(?=例\d+|练习|习题|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)

        for num, example_content in matches:
            # 提取题目和解
            lines = example_content.strip().split("\n")
            question = lines[0] if lines else ""
            solution = "\n".join(lines[1:]) if len(lines) > 1 else ""

            examples.append(
                {
                    "number": num,
                    "question": question.strip(),
                    "solution": solution.strip(),
                }
            )

        return examples

    def parse_exercises(self, content: str) -> List[str]:
        """解析练习题"""
        exercises = []
        # 匹配：１．题目 或 1. 题目
        pattern = r"(\d+)．\s*(.+?)(?=\d+．|\Z)"
        matches = re.findall(pattern, content)

        for num, question in matches:
            exercises.append(f"{num}. {question.strip()}")

        return exercises[:10]  # 最多10道题

    def extract_key_points(self, content: str) -> List[str]:
        """提取要点"""
        key_points = []

        # 查找定义句
        definition_patterns = [
            r"(.{0,50})叫作(.+?)。",
            r"(.{0,50})称为(.+?)。",
            r"(.{0,50})是(.+?)。",
        ]

        for pattern in definition_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                key_point = f"{match[0]}叫作{match[1]}"
                if len(key_point) > 10 and len(key_point) < 100:
                    key_points.append(key_point)

        return key_points[:5]  # 最多5个要点

    def extract_applications(self, content: str) -> List[str]:
        """提取应用场景"""
        applications = []

        # 查找应用关键词
        app_keywords = ["温度", "海拔", "盈利", "亏损", "增长", "减少", "收入", "支出"]
        for keyword in app_keywords:
            if keyword in content:
                # 提取包含关键词的句子
                sentences = re.findall(rf"[^。]*{keyword}[^。]*。", content)
                for sentence in sentences[:2]:
                    if len(sentence) > 10 and len(sentence) < 100:
                        applications.append(sentence)

        return applications[:5]  # 最多5个应用

    def extract_history(self, content: str) -> str:
        """提取数学历史"""
        # 查找历史相关段落
        history_keywords = ["古代", "历史", "九章算术", "刘徽", "算筹"]
        for keyword in history_keywords:
            if keyword in content:
                # 提取包含关键词的段落
                paragraphs = content.split("\n\n")
                for para in paragraphs:
                    if keyword in para and len(para) > 50:
                        return para.strip()[:300]  # 最多300字

        return ""

    def enhance_knowledge_point(self, kp: Dict, content: str) -> Dict:
        """增强单个知识点"""
        enhanced = kp.copy()

        # 解析内容
        examples = self.parse_examples(content)
        exercises = self.parse_exercises(content)
        key_points = self.extract_key_points(content)
        applications = self.extract_applications(content)
        history = self.extract_history(content)

        # 更新知识点
        enhanced["examples"] = examples
        enhanced["exercises"] = exercises
        enhanced["key_points"] = key_points
        enhanced["applications"] = applications
        enhanced["history"] = history

        # 提取讲解（第一段）
        paragraphs = content.split("\n\n")
        for para in paragraphs:
            if (
                len(para) > 50
                and not para.startswith("例")
                and not para.startswith("图")
            ):
                enhanced["explanation"] = para.strip()[:500]  # 最多500字
                break

        return enhanced

    def enhance_textbook(self, grade: int, semester: str):
        """增强一本课本的所有知识点"""
        # 中文数字映射
        chinese_nums = {7: "七", 8: "八", 9: "九"}

        # 读取课本Markdown
        md_file = self.textbooks_dir / f"{chinese_nums[grade]}年级{semester}.md"
        if not md_file.exists():
            print(f"课本文件不存在: {md_file}")
            return

        # 读取知识点JSON
        kp_file = (
            self.textbooks_dir / f"{chinese_nums[grade]}年级{semester}_知识点.json"
        )
        if not kp_file.exists():
            print(f"知识点文件不存在: {kp_file}")
            return

        with open(kp_file, "r", encoding="utf-8") as f:
            knowledge_points = json.load(f)

        print(f"\n处理 {grade}年级{semester}，共 {len(knowledge_points)} 个知识点")

        # 读取课本内容
        md_content = md_file.read_text(encoding="utf-8")

        # 增强每个知识点
        enhanced_kps = []
        for kp in knowledge_points:
            chapter = kp.get("chapter", "")
            section = kp.get("section", "")

            # 提取章节内容
            section_content = self.extract_section_content(md_file, chapter, section)

            if section_content:
                enhanced_kp = self.enhance_knowledge_point(kp, section_content)
                enhanced_kps.append(enhanced_kp)
                print(
                    f"  ✓ {section} - 例题{len(enhanced_kp.get('examples', []))}道，练习{len(enhanced_kp.get('exercises', []))}道"
                )
            else:
                enhanced_kps.append(kp)
                print(f"  ✗ {section} - 未找到内容")

        # 保存增强后的知识点
        output_file = self.textbooks_dir / f"{grade}年级{semester}_知识点_增强.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(enhanced_kps, f, ensure_ascii=False, indent=2)

        print(f"已保存到: {output_file}")

    def enhance_all(self):
        """增强所有课本"""
        for grade in [7, 8, 9]:
            for semester in ["上册", "下册"]:
                self.enhance_textbook(grade, semester)


def main():
    enhancer = ContentEnhancer()
    enhancer.enhance_all()


if __name__ == "__main__":
    main()
