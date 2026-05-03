# -*- coding: utf-8 -*-
"""
系统监控模块 - System Monitor
健康检查、性能监控、告警通知
"""

import os
import time
import psutil
import platform
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

from .logger import get_logger

logger = get_logger('monitor')


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = datetime.now()
        
        # 阈值配置
        self.thresholds = {
            'cpu_warning': 70,
            'cpu_critical': 90,
            'memory_warning': 70,
            'memory_critical': 85,
            'disk_warning': 70,
            'disk_critical': 85,
        }
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """获取 CPU 使用率"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        status = self._get_status(
            cpu_percent,
            self.thresholds['cpu_warning'],
            self.thresholds['cpu_critical']
        )
        
        return {
            'usage_percent': cpu_percent,
            'core_count': cpu_count,
            'status': status.value,
            'timestamp': datetime.now().isoformat(),
        }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用率"""
        memory = psutil.virtual_memory()
        
        status = self._get_status(
            memory.percent,
            self.thresholds['memory_warning'],
            self.thresholds['memory_critical']
        )
        
        return {
            'total_gb': round(memory.total / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'usage_percent': memory.percent,
            'status': status.value,
            'timestamp': datetime.now().isoformat(),
        }
    
    def get_disk_usage(self, path: str = '/') -> Dict[str, Any]:
        """获取磁盘使用率"""
        try:
            usage = psutil.disk_usage(path)
            
            status = self._get_status(
                usage.percent,
                self.thresholds['disk_warning'],
                self.thresholds['disk_critical']
            )
            
            return {
                'path': path,
                'total_gb': round(usage.total / (1024**3), 2),
                'used_gb': round(usage.used / (1024**3), 2),
                'free_gb': round(usage.free / (1024**3), 2),
                'usage_percent': usage.percent,
                'status': status.value,
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"获取磁盘使用率失败：{e}")
            return {
                'path': path,
                'error': str(e),
                'status': HealthStatus.UNKNOWN.value,
            }
    
    def get_process_info(self) -> Dict[str, Any]:
        """获取进程信息"""
        try:
            with self.process.oneshot():
                cpu_percent = self.process.cpu_percent()
                memory_percent = self.process.memory_percent()
                memory_info = self.process.memory_info()
                num_threads = self.process.num_threads()
                open_files = len(self.process.open_files())
                connections = len(self.process.connections())
                
                return {
                    'pid': self.process.pid,
                    'name': self.process.name(),
                    'status': self.process.status(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_rss_mb': round(memory_info.rss / (1024**2), 2),
                    'memory_vms_mb': round(memory_info.vms / (1024**2), 2),
                    'num_threads': num_threads,
                    'open_files': open_files,
                    'connections': connections,
                    'create_time': datetime.fromtimestamp(
                        self.process.create_time()
                    ).isoformat(),
                    'uptime_seconds': (
                        datetime.now() - self.start_time
                    ).total_seconds(),
                }
        except Exception as e:
            logger.error(f"获取进程信息失败：{e}")
            return {'error': str(e)}
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'python_implementation': platform.python_implementation(),
            'hostname': platform.node(),
            'boot_time': datetime.fromtimestamp(
                psutil.boot_time()
            ).isoformat(),
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取整体健康状态"""
        cpu = self.get_cpu_usage()
        memory = self.get_memory_usage()
        disk = self.get_disk_usage()
        process = self.get_process_info()
        
        # 计算整体健康状态
        statuses = [
            HealthStatus(cpu['status']),
            HealthStatus(memory['status']),
            HealthStatus(disk.get('status', 'unknown')),
        ]
        
        if any(s == HealthStatus.CRITICAL for s in statuses):
            overall = HealthStatus.CRITICAL
        elif any(s == HealthStatus.WARNING for s in statuses):
            overall = HealthStatus.WARNING
        else:
            overall = HealthStatus.HEALTHY
        
        return {
            'overall': overall.value,
            'cpu': cpu,
            'memory': memory,
            'disk': disk,
            'process': process,
            'system': self.get_system_info(),
            'timestamp': datetime.now().isoformat(),
        }
    
    def check_health(self) -> bool:
        """
        检查系统是否健康
        
        Returns:
            True if healthy, False otherwise
        """
        health = self.get_health_status()
        return health['overall'] == HealthStatus.HEALTHY.value
    
    def _get_status(
        self,
        value: float,
        warning_threshold: float,
        critical_threshold: float
    ) -> HealthStatus:
        """根据阈值判断状态"""
        if value >= critical_threshold:
            return HealthStatus.CRITICAL
        elif value >= warning_threshold:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def generate_report(self) -> str:
        """生成监控报告"""
        health = self.get_health_status()
        
        report = f"""
{'='*60}
系统健康监控报告
{'='*60}
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
整体状态：{health['overall'].upper()}

系统信息:
  操作系统：{health['system']['system']} {health['system']['release']}
  Python: {health['system']['python_version']}
  主机名：{health['system']['hostname']}

CPU 使用:
  使用率：{health['cpu']['usage_percent']:.1f}%
  核心数：{health['cpu']['core_count']}
  状态：{health['cpu']['status'].upper()}

内存使用:
  总量：{health['memory']['total_gb']} GB
  已用：{health['memory']['used_gb']} GB
  可用：{health['memory']['available_gb']} GB
  使用率：{health['memory']['usage_percent']:.1f}%
  状态：{health['memory']['status'].upper()}

磁盘使用:
  路径：{health['disk'].get('path', 'N/A')}
  使用率：{health['disk'].get('usage_percent', 0):.1f}%
  状态：{health['disk'].get('status', 'unknown').upper()}

进程信息:
  PID: {health['process'].get('pid', 'N/A')}
  名称：{health['process'].get('name', 'N/A')}
  状态：{health['process'].get('status', 'N/A')}
  CPU: {health['process'].get('cpu_percent', 0):.1f}%
  内存：{health['process'].get('memory_percent', 0):.1f}%
  运行时间：{health['process'].get('uptime_seconds', 0)/3600:.2f} 小时

{'='*60}
"""
        return report


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.timings: Dict[str, List[float]] = {}
    
    def record(self, metric_name: str, value: float) -> None:
        """记录指标值"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
    
    def start_timer(self, operation: str) -> None:
        """开始计时"""
        self.timings[f"{operation}_start"] = time.time()
    
    def end_timer(self, operation: str) -> Optional[float]:
        """结束计时并返回耗时（秒）"""
        start_key = f"{operation}_start"
        if start_key not in self.timings:
            logger.warning(f"未找到计时器：{operation}")
            return None
        
        elapsed = time.time() - self.timings[start_key]
        self.record(f"{operation}_duration", elapsed)
        del self.timings[start_key]
        
        return elapsed
    
    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """获取统计信息"""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {}
        
        values = self.metrics[metric_name]
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'sum': sum(values),
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """获取所有指标的统计信息"""
        return {
            name: self.get_stats(name)
            for name in self.metrics.keys()
        }
    
    def reset(self) -> None:
        """重置所有监控数据"""
        self.metrics.clear()
        self.timings.clear()


def check_api_health(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """检查 API 健康状态"""
    import requests
    
    try:
        # 健康检查端点
        response = requests.get(f"{base_url}/api/v1/health", timeout=5)
        
        if response.status_code == 200:
            return {
                'healthy': True,
                'status_code': 200,
                'message': 'API is healthy',
                'data': response.json(),
            }
        else:
            return {
                'healthy': False,
                'status_code': response.status_code,
                'message': f'API returned status {response.status_code}',
            }
    
    except requests.ConnectionError:
        return {
            'healthy': False,
            'status_code': 0,
            'message': '无法连接到 API 服务',
        }
    except requests.Timeout:
        return {
            'healthy': False,
            'status_code': 0,
            'message': 'API 响应超时',
        }
    except Exception as e:
        return {
            'healthy': False,
            'status_code': 0,
            'message': f'检查失败：{str(e)}',
        }


# 全局监控实例
system_monitor = SystemMonitor()
performance_monitor = PerformanceMonitor()
