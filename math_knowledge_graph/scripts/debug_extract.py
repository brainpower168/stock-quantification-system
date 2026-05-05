#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试知识点提取
检查文件格式和正则匹配
"""

import re
from pathlib import Path

# 测试文件
md_file = Path(__file__).parent.parent / "textbooks" / "七年级下册.md"

with open(md_file, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")

print("=" * 60)
print("文件信息")
print("=" * 60)
print(f"总行数: {len(lines)}")
print(f"文件大小: {len(content)} 字符")

# 显示前20行
print("\n" + "=" * 60)
print("前20行内容（显示特殊字符）")
print("=" * 60)
for i, line in enumerate(lines[:20]):
    # 显示特殊字符
    line_repr = repr(line)
    print(f"第{i + 1}行: {line_repr}")

# 测试章节匹配
print("\n" + "=" * 60)
print("测试章节匹配")
print("=" * 60)

chapter_pattern1 = r"第([一二三四五六七八九十]+)章[ 　](.+?)(?:\n|$)"
chapter_pattern2 = r"第([０-９]+)章[ 　](.+?)(?:\n|$)"

for i, line in enumerate(lines[:50]):
    match1 = re.search(chapter_pattern1, line)
    match2 = re.search(chapter_pattern2, line)

    if match1:
        print(f"✅ 第{i + 1}行匹配到章节（中文数字）: {match1.group(0)}")
        print(f"   章节号: {match1.group(1)}, 章节名: {match1.group(2)}")
    if match2:
        print(f"✅ 第{i + 1}行匹配到章节（全角数字）: {match2.group(0)}")
        print(f"   章节号: {match2.group(1)}, 章节名: {match2.group(2)}")

# 测试小节匹配
print("\n" + "=" * 60)
print("测试小节匹配")
print("=" * 60)

section_pattern1 = r"([０-９]+)．([０-９]+)[ 　](.+?)(?:\n|$)"
section_pattern2 = r"([０-９]+)\.([０-９]+)[ 　](.+?)(?:\n|$)"
section_pattern3 = r"(\d+)\.(\d+)[ 　](.+?)(?:\n|$)"

for i, line in enumerate(lines[:50]):
    match1 = re.search(section_pattern1, line)
    match2 = re.search(section_pattern2, line)
    match3 = re.search(section_pattern3, line)

    if match1:
        print(f"✅ 第{i + 1}行匹配到小节（全角点）: {match1.group(0)}")
        print(
            f"   小节号: {match1.group(1)}.{match1.group(2)}, 小节名: {match1.group(3)}"
        )
    if match2:
        print(f"✅ 第{i + 1}行匹配到小节（半角点）: {match2.group(0)}")
        print(
            f"   小节号: {match2.group(1)}.{match2.group(2)}, 小节名: {match2.group(3)}"
        )
    if match3:
        print(f"✅ 第{i + 1}行匹配到小节（半角数字）: {match3.group(0)}")
        print(
            f"   小节号: {match3.group(1)}.{match3.group(2)}, 小节名: {match3.group(3)}"
        )

# 测试在整行中匹配
print("\n" + "=" * 60)
print("测试在整行中匹配（不使用$）")
print("=" * 60)

chapter_pattern_alt = r"第([一二三四五六七八九十]+)章[ 　](.+?)(?=\s|$)"

for i, line in enumerate(lines[:50]):
    match = re.search(chapter_pattern_alt, line)
    if match:
        print(f"✅ 第{i + 1}行匹配到章节: {match.group(0)}")
        print(f"   章节号: {match.group(1)}, 章节名: {match.group(2)}")

print("\n" + "=" * 60)
print("检查特殊字符")
print("=" * 60)

# 检查是否有特殊空格
for i, line in enumerate(lines[:20]):
    if "第七章" in line or "第八章" in line:
        print(f"第{i + 1}行包含章节标题")
        print(f"  原始内容: {repr(line)}")
        # 检查每个字符的Unicode编码
        for j, char in enumerate(line[:30]):
            print(f"    位置{j}: '{char}' (U+{ord(char):04X})")
