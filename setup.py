from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="stock-quant-system",
    version="1.0.0",
    author="炒股大师",
    author_email="your-email@example.com",
    description="炒股大师量化交易系统 - 多因子选股、持仓监控、情绪分析、回测验证",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitee.com/brainpower168/stock-quantification-system",
    packages=find_packages(),
    classifiers=[
        "Development Status : : 3 - Alpha",
        "Intended Audience : : Developers",
        "Topic : : Office/Business : : Financial : : Investment",
        "License : : OSI Approved : MIT License",
        "Programming Language : : Python : : 3",
        "Programming Language : : Python : : 3.7",
        "Programming Language : : Python : : 3.8",
        "Programming Language : : Python : : 3.9",
        "Programming Language : : Python : : 3.10",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.0",
        "pydantic>=1.8.0",
        "fastapi>=0.65.0",
        "uvicorn>=0.14.0",
        "numpy>=1.20.0",
        "pandas>=1.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.12.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
        ],
    },
    include_package_data=True,
    package_data={
        "quant_system": ["py.typed"],
    },
)