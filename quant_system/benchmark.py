# -*- coding: utf-8 -*-
"""
性能基准测试 - Performance Benchmark
测试量化系统各模块的性能表现
"""

import time
import statistics
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from .logger import get_logger
from .monitor import performance_monitor

logger = get_logger('benchmark')


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    std_dev: float
    ops_per_second: float
    timestamp: str


class Benchmark:
    """性能基准测试器"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.results: List[BenchmarkResult] = []
    
    def run(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        iterations: int = 10,
        warmup: bool = True,
    ) -> BenchmarkResult:
        """
        运行基准测试
        
        Args:
            func: 测试函数
            args: 位置参数
            kwargs: 关键字参数
            iterations: 迭代次数
            warmup: 是否预热
        
        Returns:
            BenchmarkResult
        """
        kwargs = kwargs or {}
        times = []
        
        # 预热
        if warmup:
            logger.debug(f"预热：{func.__name__}")
            func(*args, **kwargs)
            time.sleep(0.1)
        
        # 正式测试
        logger.info(f"开始基准测试：{func.__name__} (iterations={iterations})")
        
        for i in range(iterations):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            
            elapsed = end - start
            times.append(elapsed)
            
            logger.debug(f"  迭代 {i+1}/{iterations}: {elapsed*1000:.2f}ms")
        
        # 统计分析
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        median_time = statistics.median(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        total_time = sum(times)
        ops_per_second = iterations / total_time if total_time > 0 else 0
        
        result = BenchmarkResult(
            name=func.__name__,
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            std_dev=std_dev,
            ops_per_second=ops_per_second,
            timestamp=datetime.now().isoformat(),
        )
        
        self.results.append(result)
        
        # 记录到性能监控
        performance_monitor.record(f"{func.__name__}_time", avg_time * 1000)
        
        logger.info(
            f"基准测试完成：{func.__name__}\n"
            f"  平均：{avg_time*1000:.2f}ms\n"
            f"  中位数：{median_time*1000:.2f}ms\n"
            f"  最小：{min_time*1000:.2f}ms\n"
            f"  最大：{max_time*1000:.2f}ms\n"
            f"  标准差：{std_dev*1000:.2f}ms\n"
            f"  OPS: {ops_per_second:.2f}"
        )
        
        return result
    
    def compare(
        self,
        funcs: List[tuple],
        iterations: int = 10,
    ) -> Dict[str, BenchmarkResult]:
        """
        比较多个函数的性能
        
        Args:
            funcs: [(func, args, kwargs), ...]
            iterations: 迭代次数
        
        Returns:
            函数名到结果的映射
        """
        results = {}
        
        for func_info in funcs:
            func = func_info[0]
            args = func_info[1] if len(func_info) > 1 else ()
            kwargs = func_info[2] if len(func_info) > 2 else {}
            
            result = self.run(func, args, kwargs, iterations)
            results[func.__name__] = result
        
        return results
    
    def generate_report(self) -> str:
        """生成基准测试报告"""
        if not self.results:
            return "无测试结果"
        
        report = f"""
{'='*70}
性能基准测试报告 - {self.name}
{'='*70}
测试数量：{len(self.results)}
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*70}
测试结果
{'='*70}
"""
        
        for i, result in enumerate(self.results, 1):
            report += f"""
{i}. {result.name}
   迭代次数：{result.iterations}
   总耗时：{result.total_time*1000:.2f}ms
   平均耗时：{result.avg_time*1000:.2f}ms
   中位数：{result.median_time*1000:.2f}ms
   最小值：{result.min_time*1000:.2f}ms
   最大值：{result.max_time*1000:.2f}ms
   标准差：{result.std_dev*1000:.2f}ms
   OPS: {result.ops_per_second:.2f}
"""
        
        report += f"\n{'='*70}\n"
        
        return report
    
    def save_results(self, filepath: str) -> None:
        """保存测试结果到 JSON 文件"""
        data = {
            'name': self.name,
            'timestamp': datetime.now().isoformat(),
            'results': [
                {
                    'name': r.name,
                    'iterations': r.iterations,
                    'total_time': r.total_time,
                    'avg_time': r.avg_time,
                    'min_time': r.min_time,
                    'max_time': r.max_time,
                    'median_time': r.median_time,
                    'std_dev': r.std_dev,
                    'ops_per_second': r.ops_per_second,
                    'timestamp': r.timestamp,
                }
                for r in self.results
            ],
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"测试结果已保存：{filepath}")
    
    def load_results(self, filepath: str) -> List[BenchmarkResult]:
        """从 JSON 文件加载测试结果"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.results = [
            BenchmarkResult(
                name=r['name'],
                iterations=r['iterations'],
                total_time=r['total_time'],
                avg_time=r['avg_time'],
                min_time=r['min_time'],
                max_time=r['max_time'],
                median_time=r['median_time'],
                std_dev=r['std_dev'],
                ops_per_second=r['ops_per_second'],
                timestamp=r['timestamp'],
            )
            for r in data.get('results', [])
        ]
        
        logger.info(f"已加载 {len(self.results)} 个测试结果")
        return self.results
    
    def clear(self) -> None:
        """清空测试结果"""
        self.results.clear()


def benchmark_func(
    iterations: int = 10,
    warmup: bool = True,
    name: str = None,
):
    """
    基准测试装饰器
    
    Usage:
        @benchmark_func(iterations=10)
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            benchmark = Benchmark(name or func.__name__)
            return benchmark.run(func, args, kwargs, iterations, warmup)
        return wrapper
    return decorator


# 预定义基准测试
def run_all_benchmarks() -> Dict[str, BenchmarkResult]:
    """运行所有预定义的基准测试"""
    benchmark = Benchmark("Quant System All Benchmarks")
    results = {}
    
    # 添加要测试的函数
    # 这里需要根据实际模块添加
    
    return results


# CLI 使用
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="性能基准测试")
    parser.add_argument('--iterations', type=int, default=10, help='迭代次数')
    parser.add_argument('--output', type=str, help='输出文件路径')
    parser.add_argument('--module', type=str, help='测试模块')
    
    args = parser.parse_args()
    
    benchmark = Benchmark(args.module or "default")
    results = run_all_benchmarks()
    
    print(benchmark.generate_report())
    
    if args.output:
        benchmark.save_results(args.output)
