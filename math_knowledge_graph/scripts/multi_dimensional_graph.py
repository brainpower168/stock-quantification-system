#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多维度知识图谱构建器
按主题、模型、方法、定理等多维度组织知识点
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class CategoryType(Enum):
    """知识点分类类型"""

    TOPIC = "主题"  # 几何、代数、函数等
    MODEL = "模型"  # 胡不归模型、十字架模型等
    METHOD = "方法"  # 辅助线、代数变形等
    THEOREM = "定理"  # 勾股定理、三线合一等
    FORMULA = "公式"  # 求根公式、面积公式等
    CONCEPT = "概念"  # 定义、基本概念
    SKILL = "技能"  # 作图、计算技巧
    EXAM = "考题"  # 中考真题、典型题型


@dataclass
class KnowledgeContent:
    """知识点内容"""

    explanation: str = ""  # 详细讲解
    examples: List[Dict] = field(default_factory=list)  # 例题
    exercises: List[Dict] = field(default_factory=list)  # 练习题
    animations: List[str] = field(default_factory=list)  # 动画演示链接
    formulas: List[str] = field(default_factory=list)  # 公式
    tips: List[str] = field(default_factory=list)  # 学习提示
    common_mistakes: List[str] = field(default_factory=list)  # 常见错误


@dataclass
class KnowledgeNode:
    """知识点节点（支持多层级展开）"""

    id: str
    name: str
    level: int  # 层级：1=主题, 2=子主题, 3=知识点, 4=内容
    categories: List[str] = field(default_factory=list)  # 所属分类（可属于多个）
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)  # 子节点ID列表
    content: Optional[KnowledgeContent] = None
    difficulty: int = 3  # 1-5难度
    importance: int = 3  # 1-5重要性
    keywords: List[str] = field(default_factory=list)
    source: str = ""  # 来源课本

    def to_dict(self):
        """转换为字典"""
        result = {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "categories": self.categories,
            "parent_id": self.parent_id,
            "children": self.children,
            "difficulty": self.difficulty,
            "importance": self.importance,
            "keywords": self.keywords,
            "source": self.source,
        }
        if self.content:
            result["content"] = asdict(self.content)
        return result


@dataclass
class Category:
    """分类节点"""

    id: str
    name: str
    type: CategoryType
    description: str = ""
    children: List[str] = field(default_factory=list)  # 子分类ID
    knowledge_nodes: List[str] = field(default_factory=list)  # 包含的知识点ID


class MultiDimensionalKnowledgeGraph:
    """多维度知识图谱"""

    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.categories: Dict[str, Category] = {}

        # 初始化基础分类
        self._init_base_categories()

    def _init_base_categories(self):
        """初始化基础分类"""
        base_categories = [
            ("topic_geometry", "几何", CategoryType.TOPIC, "平面几何、立体几何"),
            ("topic_algebra", "代数", CategoryType.TOPIC, "方程、不等式、函数"),
            (
                "topic_function",
                "函数",
                CategoryType.TOPIC,
                "一次函数、二次函数、反比例函数",
            ),
            ("topic_statistics", "统计与概率", CategoryType.TOPIC, "数据分析、概率"),
            ("model_basic", "基本模型", CategoryType.MODEL, "常见几何模型"),
            ("model_advanced", "进阶模型", CategoryType.MODEL, "胡不归、十字架等"),
            ("method_proof", "证明方法", CategoryType.METHOD, "几何证明技巧"),
            ("method_calculation", "计算方法", CategoryType.METHOD, "代数计算技巧"),
            ("method_construction", "作图方法", CategoryType.METHOD, "尺规作图"),
            (
                "theorem_triangle",
                "三角形定理",
                CategoryType.THEOREM,
                "勾股定理、正余弦定理",
            ),
            (
                "theorem_circle",
                "圆相关定理",
                CategoryType.THEOREM,
                "圆周角定理、切线定理",
            ),
            (
                "theorem_quadrilateral",
                "四边形定理",
                CategoryType.THEOREM,
                "平行四边形判定",
            ),
            (
                "formula_area",
                "面积公式",
                CategoryType.FORMULA,
                "三角形、四边形、圆面积",
            ),
            ("formula_volume", "体积公式", CategoryType.FORMULA, "柱体、锥体体积"),
            (
                "formula_equation",
                "方程公式",
                CategoryType.FORMULA,
                "求根公式、韦达定理",
            ),
        ]

        for cat_id, name, cat_type, desc in base_categories:
            self.categories[cat_id] = Category(
                id=cat_id, name=name, type=cat_type, description=desc
            )

    def add_node(self, node: KnowledgeNode):
        """添加知识点节点"""
        self.nodes[node.id] = node

        # 更新父节点的children列表
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.id not in parent.children:
                parent.children.append(node.id)

        # 更新分类的knowledge_nodes列表
        for cat_id in node.categories:
            if cat_id in self.categories:
                cat = self.categories[cat_id]
                if node.id not in cat.knowledge_nodes:
                    cat.knowledge_nodes.append(node.id)

    def build_triangle_topic(self) -> Dict:
        """构建三角形主题知识图谱（示例）"""
        # Level 1: 主题
        triangle_topic = KnowledgeNode(
            id="topic_triangle",
            name="三角形",
            level=1,
            categories=["topic_geometry"],
            importance=5,
        )
        self.add_node(triangle_topic)

        # Level 2: 子主题
        subtopics = [
            (
                "subtopic_triangle_basic",
                "三角形的基本概念",
                ["topic_geometry", "topic_algebra"],
            ),
            (
                "subtopic_triangle_properties",
                "三角形的性质",
                ["topic_geometry", "theorem_triangle"],
            ),
            (
                "subtopic_triangle_congruence",
                "全等三角形",
                ["topic_geometry", "method_proof"],
            ),
            (
                "subtopic_triangle_similarity",
                "相似三角形",
                ["topic_geometry", "method_proof"],
            ),
            ("subtopic_triangle_special", "特殊三角形", ["topic_geometry"]),
            (
                "subtopic_triangle_calculation",
                "三角形的计算",
                ["topic_geometry", "method_calculation"],
            ),
        ]

        for sub_id, name, cats in subtopics:
            node = KnowledgeNode(
                id=sub_id,
                name=name,
                level=2,
                categories=cats,
                parent_id="topic_triangle",
                importance=4,
            )
            self.add_node(node)

        # Level 3: 具体知识点
        # 三角形的基本概念
        basic_concepts = [
            (
                "kp_triangle_definition",
                "三角形的定义",
                "subtopic_triangle_basic",
                "由不在同一直线上的三条线段首尾顺次连接所组成的封闭图形",
            ),
            (
                "kp_triangle_elements",
                "三角形的元素",
                "subtopic_triangle_basic",
                "边、角、顶点、高、中线、角平分线",
            ),
            (
                "kp_triangle_classification",
                "三角形的分类",
                "subtopic_triangle_basic",
                "按边分：等边、等腰、不等边；按角分：锐角、直角、钝角",
            ),
        ]

        for kp_id, name, parent, desc in basic_concepts:
            node = KnowledgeNode(
                id=kp_id,
                name=name,
                level=3,
                categories=["topic_geometry", "concept"],
                parent_id=parent,
                content=KnowledgeContent(explanation=desc),
                difficulty=2,
                importance=4,
            )
            self.add_node(node)

        # 三角形的性质
        properties = [
            (
                "kp_triangle_angle_sum",
                "三角形内角和定理",
                "subtopic_triangle_properties",
                "三角形三个内角的和等于180°",
                ["theorem_triangle"],
            ),
            (
                "kp_triangle_exterior_angle",
                "三角形外角性质",
                "subtopic_triangle_properties",
                "三角形的一个外角等于与它不相邻的两个内角的和",
                ["theorem_triangle"],
            ),
            (
                "kp_triangle_inequality",
                "三角形三边关系",
                "subtopic_triangle_properties",
                "三角形任意两边之和大于第三边，任意两边之差小于第三边",
                ["theorem_triangle"],
            ),
            (
                "kp_triangle_midline",
                "三角形中位线定理",
                "subtopic_triangle_properties",
                "三角形的中位线平行于第三边且等于第三边的一半",
                ["theorem_triangle", "model_basic"],
            ),
        ]

        for kp_id, name, parent, desc, cats in properties:
            node = KnowledgeNode(
                id=kp_id,
                name=name,
                level=3,
                categories=cats,
                parent_id=parent,
                content=KnowledgeContent(explanation=desc),
                difficulty=3,
                importance=5,
            )
            self.add_node(node)

        # 全等三角形
        congruence = [
            (
                "kp_congruence_sss",
                "SSS（边边边）",
                "subtopic_triangle_congruence",
                "三边对应相等的两个三角形全等",
                ["method_proof"],
            ),
            (
                "kp_congruence_sas",
                "SAS（边角边）",
                "subtopic_triangle_congruence",
                "两边及其夹角对应相等的两个三角形全等",
                ["method_proof"],
            ),
            (
                "kp_congruence_asa",
                "ASA（角边角）",
                "subtopic_triangle_congruence",
                "两角及其夹边对应相等的两个三角形全等",
                ["method_proof"],
            ),
            (
                "kp_congruence_aas",
                "AAS（角角边）",
                "subtopic_triangle_congruence",
                "两角及其中一角的对边对应相等的两个三角形全等",
                ["method_proof"],
            ),
            (
                "kp_congruence_hl",
                "HL（斜边直角边）",
                "subtopic_triangle_congruence",
                "斜边和一条直角边对应相等的两个直角三角形全等",
                ["method_proof"],
            ),
        ]

        for kp_id, name, parent, desc, cats in congruence:
            node = KnowledgeNode(
                id=kp_id,
                name=name,
                level=3,
                categories=cats,
                parent_id=parent,
                content=KnowledgeContent(explanation=desc),
                difficulty=3,
                importance=5,
            )
            self.add_node(node)

        # 相似三角形
        similarity = [
            (
                "kp_similarity_aa",
                "AA（角角）",
                "subtopic_triangle_similarity",
                "两角对应相等的两个三角形相似",
                ["method_proof"],
            ),
            (
                "kp_similarity_sas",
                "SAS（边角边）",
                "subtopic_triangle_similarity",
                "两边对应成比例且夹角相等的两个三角形相似",
                ["method_proof"],
            ),
            (
                "kp_similarity_sss",
                "SSS（边边边）",
                "subtopic_triangle_similarity",
                "三边对应成比例的两个三角形相似",
                ["method_proof"],
            ),
            (
                "kp_similarity_properties",
                "相似三角形的性质",
                "subtopic_triangle_similarity",
                "对应角相等，对应边成比例，面积比等于相似比的平方",
                ["theorem_triangle"],
            ),
        ]

        for kp_id, name, parent, desc, cats in similarity:
            node = KnowledgeNode(
                id=kp_id,
                name=name,
                level=3,
                categories=cats,
                parent_id=parent,
                content=KnowledgeContent(explanation=desc),
                difficulty=4,
                importance=5,
            )
            self.add_node(node)

        # 特殊三角形
        special = [
            (
                "kp_isosceles_triangle",
                "等腰三角形",
                "subtopic_triangle_special",
                "两边相等的三角形，底角相等，顶角平分线、底边中线、底边高三线合一",
                ["topic_geometry"],
            ),
            (
                "kp_equilateral_triangle",
                "等边三角形",
                "subtopic_triangle_special",
                "三边相等的三角形，三个内角都是60°",
                ["topic_geometry"],
            ),
            (
                "kp_right_triangle",
                "直角三角形",
                "subtopic_triangle_special",
                "有一个角是90°的三角形",
                ["topic_geometry"],
            ),
            (
                "kp_pythagorean_theorem",
                "勾股定理",
                "subtopic_triangle_special",
                "直角三角形两直角边的平方和等于斜边的平方",
                ["theorem_triangle", "formula_area"],
            ),
        ]

        for kp_id, name, parent, desc, cats in special:
            node = KnowledgeNode(
                id=kp_id,
                name=name,
                level=3,
                categories=cats,
                parent_id=parent,
                content=KnowledgeContent(explanation=desc),
                difficulty=3,
                importance=5,
            )
            self.add_node(node)

        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "categories": {k: asdict(v) for k, v in self.categories.items()},
        }

    def export_to_json(self, output_file: Path):
        """导出为JSON"""
        # 转换分类，将枚举转为字符串
        categories_data = {}
        for k, v in self.categories.items():
            cat_dict = asdict(v)
            cat_dict["type"] = v.type.value  # 枚举转字符串
            categories_data[k] = cat_dict

        data = {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "categories": categories_data,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ 已导出知识图谱：{output_file}")
        print(f"   知识点数量：{len(self.nodes)}")
        print(f"   分类数量：{len(self.categories)}")


def main():
    """主函数"""
    graph = MultiDimensionalKnowledgeGraph()

    # 构建三角形主题
    graph.build_triangle_topic()

    # 导出
    output_file = Path("data/multi_dimensional_graph.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    graph.export_to_json(output_file)

    # 打印结构
    print("\n📊 三角形知识图谱结构：")
    print("三角形（主题）")
    for node_id, node in graph.nodes.items():
        if node.level == 2:
            print(f"  ├─ {node.name}（子主题）")
            for child_id in node.children:
                child = graph.nodes[child_id]
                print(f"  │   ├─ {child.name}")


if __name__ == "__main__":
    main()
