#!/usr/bin/env python3
"""
环境配置检查脚本
检查 .env 文件、API Keys、依赖等是否配置正确
"""

import sys
import os
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}")

def check_env_file():
    """检查 .env 文件"""
    print_header("1. 检查 .env 文件")
    
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists():
        print("❌ .env 文件不存在")
        if env_example.exists():
            print("   建议执行：cp .env.example .env")
        return False
    else:
        print("✅ .env 文件存在")
        return True

def check_api_keys():
    """检查必需的 API Keys"""
    print_header("2. 检查 API Keys")
    
    # 加载 .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv 未安装，请执行：pip install python-dotenv")
        return False
    
    required_keys = [
        ('IWENCAI_API_KEY', '问财 API'),
        ('MX_APIKEY', '妙想 API'),
    ]
    
    optional_keys = [
        ('LONGCAT_API_KEY', 'LongCat AI'),
        ('XUNFEI_API_KEY', '讯飞星火'),
        ('GLM_API_KEY', '智谱 GLM'),
        ('GS_API_KEY', '国信证券'),
    ]
    
    all_ok = True
    
    print("必需 API Keys:")
    for key, name in required_keys:
        value = os.getenv(key)
        if not value or value == 'your_iwencai_api_key_here' or value == 'your_mx_apikey_here':
            print(f"   ❌ {name} ({key}) 未配置")
            all_ok = False
        else:
            print(f"   ✅ {name} ({key}) 已配置")
    
    print("\n可选 API Keys:")
    for key, name in optional_keys:
        value = os.getenv(key)
        if value:
            print(f"   ✅ {name} ({key}) 已配置")
        else:
            print(f"   ⚪  {name} ({key}) 未配置 (可选)")
    
    return all_ok

def check_dependencies():
    """检查依赖包"""
    print_header("3. 检查依赖包")
    
    required_packages = [
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('requests', 'requests'),
        ('dotenv', 'python-dotenv'),
    ]
    
    all_ok = True
    
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print(f"   ✅ {package_name}")
        except ImportError:
            print(f"   ❌ {package_name} 未安装 (pip install {package_name})")
            all_ok = False
    
    print("\n可选依赖:")
    optional_packages = [
        ('talib', 'TA-Lib', 'talib'),
        ('xgboost', 'XGBoost', 'xgboost'),
        ('sklearn', 'scikit-learn', 'scikit-learn'),
    ]
    
    for import_name, package_name, install_name in optional_packages:
        try:
            __import__(import_name)
            print(f"   ✅ {package_name}")
        except ImportError:
            print(f"   ⚪  {package_name} 未安装 (可选)")
    
    return all_ok

def check_directories():
    """检查必要目录"""
    print_header("4. 检查目录结构")
    
    required_dirs = ['data', 'logs']
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ⚠️  {dir_name}/ 不存在 (将自动创建)")
            dir_path.mkdir(exist_ok=True)
    
    return True

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║         量化交易系统 - 环境配置检查工具                    ║
║              Environment Check Tool                        ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    results = []
    
    results.append(('env_file', check_env_file()))
    results.append(('api_keys', check_api_keys()))
    results.append(('dependencies', check_dependencies()))
    results.append(('directories', check_directories()))
    
    # 总结
    print_header("检查结果总结")
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"   {status} - {name}")
    
    print(f"\n总体：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有检查通过！系统已配置完成。")
        print("\n下一步:")
        print("   1. 启动 API: uvicorn api.quant_api:app --reload")
        print("   2. 访问文档：http://localhost:8000/docs")
        print("   3. 运行测试：pytest tests/ -v")
        return 0
    else:
        print("\n⚠️  有检查项未通过，请先修复问题。")
        print("\n快速修复:")
        if not results[0][1]:
            print("   cp .env.example .env")
        if not results[1][1]:
            print("   编辑 .env 文件，填写 API Keys")
        if not results[2][1]:
            print("   pip install -r requirements.txt")
        return 1

if __name__ == '__main__':
    sys.exit(main())
