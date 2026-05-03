#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检查脚本 - 快速验证系统配置
运行: python scripts/check_env.py
"""

import os
import sys
from pathlib import Path


# 颜色输出
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"


def print_ok(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def print_warn(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


def print_err(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_ok(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_err(
            f"Python版本过低: {version.major}.{version.minor}.{version.micro}, 需要 >= 3.8"
        )
        return False


def check_env_file():
    """检查.env文件"""
    env_path = Path(__file__).parent.parent / ".env"
    env_example = Path(__file__).parent.parent / ".env.example"

    if env_path.exists():
        print_ok(".env 文件存在")
        return True
    elif env_example.exists():
        print_warn(".env 文件不存在，请复制 .env.example 为 .env 并配置API Key")
        print("    cp .env.example .env")
        return False
    else:
        print_err(".env 和 .env.example 都不存在")
        return False


def check_api_keys():
    """检查API Key配置"""
    keys = {
        "MX_APIKEY": "妙想API（首选）",
        "IWENCAI_API_KEY": "问财API（备用）",
        "GS_API_KEY": "国信API（补充）",
        "LONGCAT_API_KEY": "LongCat API（AI Council）",
    }

    configured = 0
    for key, name in keys.items():
        value = os.environ.get(key, "")
        if value and value != f"your_{key.lower()}_here":
            print_ok(f"{name}: 已配置")
            configured += 1
        else:
            print_warn(f"{name}: 未配置")

    if configured == 0:
        print_err("没有配置任何API Key，系统将无法正常工作")
        return False
    elif configured < len(keys):
        print_warn(f"已配置 {configured}/{len(keys)} 个API Key")
        return True
    else:
        print_ok(f"所有 {configured} 个API Key已配置")
        return True


def check_dependencies():
    """检查依赖包"""
    required = [
        ("requests", "HTTP请求"),
        ("pandas", "数据处理"),
        ("numpy", "数值计算"),
    ]

    optional = [
        ("talib", "技术指标（可选）"),
        ("xgboost", "机器学习（可选）"),
        ("fastapi", "API服务（可选）"),
    ]

    all_ok = True
    for pkg, name in required:
        try:
            __import__(pkg)
            print_ok(f"{name} ({pkg})")
        except ImportError:
            print_err(f"{name} ({pkg}) 未安装")
            all_ok = False

    for pkg, name in optional:
        try:
            __import__(pkg)
            print_ok(f"{name} ({pkg})")
        except ImportError:
            print_warn(f"{name} ({pkg}) 未安装（可选）")

    return all_ok


def check_quant_system():
    """检查quant_system模块"""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from quant_system.logger import get_logger

        print_ok("quant_system.logger")

        from quant_system.exceptions import QuantException

        print_ok("quant_system.exceptions")

        from quant_system.cache import MemoryCache

        print_ok("quant_system.cache")

        from quant_system.data_sources import DataSource

        print_ok("quant_system.data_sources")

        return True
    except ImportError as e:
        print_err(f"quant_system模块导入失败: {e}")
        return False


def main():
    """主检查流程"""
    print("\n" + "=" * 50)
    print("🔍 炒股大师量化系统 - 环境检查")
    print("=" * 50 + "\n")

    results = []

    print("【1. Python版本】")
    results.append(check_python_version())
    print()

    print("【2. 环境配置文件】")
    results.append(check_env_file())
    print()

    print("【3. API Key配置】")
    results.append(check_api_keys())
    print()

    print("【4. 依赖包】")
    results.append(check_dependencies())
    print()

    print("【5. 核心模块】")
    results.append(check_quant_system())
    print()

    print("=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print_ok(f"检查通过: {passed}/{total}")
        print("\n🚀 系统已就绪，可以开始使用！")
    else:
        print_warn(f"检查完成: {passed}/{total}")
        print("\n⚠️  请根据上述提示修复问题后重试")

    print("=" * 50 + "\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
