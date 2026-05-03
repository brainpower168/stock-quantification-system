# -*- coding: utf-8 -*-
"""
配置验证模块 - Configuration Validation
验证配置文件的完整性和有效性
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from .logger import get_logger
from .exceptions import ConfigException, ValidationException

logger = get_logger('config')


class ConfigValidator:
    """配置验证器"""
    
    # 必需的环境变量
    REQUIRED_ENV_VARS = [
        'IWENCAI_API_KEY',
        'MX_APIKEY',
    ]
    
    # 可选的环境变量
    OPTIONAL_ENV_VARS = [
        'GS_API_KEY',
        'LONGCAT_API_KEY',
        'XUNFEI_API_KEY',
        'GLM_API_KEY',
        'TOTAL_CAPITAL',
        'MAX_POSITION_PCT',
        'STOP_LOSS_PCT',
        'TAKE_PROFIT_PCT',
        'MAX_DRAWDOWN_PCT',
        'LOG_LEVEL',
        'DB_TYPE',
    ]
    
    # 环境变量验证规则
    VALIDATION_RULES = {
        'TOTAL_CAPITAL': lambda v: v.isdigit() and int(v) > 0,
        'MAX_POSITION_PCT': lambda v: 0 < float(v) <= 1,
        'MAX_SECTOR_PCT': lambda v: 0 < float(v) <= 1,
        'MAX_TOTAL_PCT': lambda v: 0 < float(v) <= 1,
        'STOP_LOSS_PCT': lambda v: -1 < float(v) < 0,
        'TAKE_PROFIT_PCT': lambda v: 0 < float(v) < 1,
        'MAX_DRAWDOWN_PCT': lambda v: -1 < float(v) < 0,
        'CONSENSUS_THRESHOLD': lambda v: 0 <= float(v) <= 1,
        'MIN_CONFIDENCE': lambda v: 0 <= float(v) <= 1,
        'LOG_LEVEL': lambda v: v.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        'DB_TYPE': lambda v: v.lower() in ['sqlite', 'postgresql'],
        'REDIS_PORT': lambda v: v.isdigit() and 1 <= int(v) <= 65535,
    }
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Args:
            env_file: .env 文件路径
        """
        self.env_file = env_file or '.env'
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
    
    def load_env(self) -> bool:
        """加载环境变量"""
        if Path(self.env_file).exists():
            load_dotenv(self.env_file)
            logger.info(f"环境变量已加载：{self.env_file}")
            return True
        else:
            logger.warning(f".env 文件不存在：{self.env_file}")
            return False
    
    def validate_required(self) -> bool:
        """验证必需的环境变量"""
        missing = []
        
        for var in self.REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if not value or value == f'your_{var.lower()}_here':
                missing.append(var)
        
        if missing:
            msg = f"缺少必需的环境变量：{', '.join(missing)}"
            self.validation_errors.append(msg)
            logger.error(msg)
            return False
        
        logger.info("必需的环境变量检查通过")
        return True
    
    def validate_optional(self) -> None:
        """验证可选的环境变量"""
        missing = []
        
        for var in self.OPTIONAL_ENV_VARS:
            value = os.getenv(var)
            if value is None:
                missing.append(var)
        
        if missing:
            msg = f"可选环境变量未设置：{', '.join(missing)}"
            self.validation_warnings.append(msg)
            logger.warning(msg)
    
    def validate_values(self) -> bool:
        """验证环境变量值的有效性"""
        valid = True
        
        for var, validator in self.VALIDATION_RULES.items():
            value = os.getenv(var)
            if value:
                try:
                    if not validator(value):
                        msg = f"环境变量'{var}'的值无效：{value}"
                        self.validation_errors.append(msg)
                        valid = False
                        logger.error(msg)
                except Exception as e:
                    msg = f"验证'{var}'时出错：{e}"
                    self.validation_errors.append(msg)
                    valid = False
                    logger.error(msg)
        
        if valid:
            logger.info("环境变量值验证通过")
        
        return valid
    
    def validate_config_file(self, config_path: str) -> bool:
        """验证配置文件（JSON）"""
        path = Path(config_path)
        
        if not path.exists():
            logger.warning(f"配置文件不存在：{config_path}")
            return True
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证 AI Council 配置
            if 'models' in config:
                for model_name, model_config in config['models'].items():
                    if model_config.get('enabled', False):
                        if 'api_key_env' not in model_config:
                            msg = f"AI 模型'{model_name}'缺少 api_key_env 配置"
                            self.validation_errors.append(msg)
                            logger.error(msg)
                        else:
                            api_key_env = model_config['api_key_env']
                            if not os.getenv(api_key_env):
                                msg = f"AI 模型'{model_name}'的 API Key 未设置：{api_key_env}"
                                self.validation_warnings.append(msg)
                                logger.warning(msg)
            
            # 验证决策权重
            if 'decision_weights' in config:
                weights = config['decision_weights']
                total = sum(weights.values())
                if abs(total - 1.0) > 0.01:
                    msg = f"决策权重总和不等于 1：{total:.2f}"
                    self.validation_warnings.append(msg)
                    logger.warning(msg)
            
            # 验证阈值
            if 'consensus_threshold' in config:
                threshold = config['consensus_threshold']
                if not 0 <= threshold <= 1:
                    msg = f"共识阈值超出范围：{threshold}"
                    self.validation_errors.append(msg)
                    logger.error(msg)
                    return False
            
            logger.info(f"配置文件验证通过：{config_path}")
            return True
            
        except json.JSONDecodeError as e:
            msg = f"配置文件 JSON 格式错误：{e}"
            self.validation_errors.append(msg)
            logger.error(msg)
            return False
        except Exception as e:
            msg = f"读取配置文件失败：{e}"
            self.validation_errors.append(msg)
            logger.error(msg)
            return False
    
    def validate_all(self) -> bool:
        """执行完整验证"""
        logger.info("开始验证配置...")
        
        # 加载环境变量
        self.load_env()
        
        # 验证必需环境变量
        required_ok = self.validate_required()
        
        # 验证可选环境变量
        self.validate_optional()
        
        # 验证环境变量值
        values_ok = self.validate_values()
        
        # 验证配置文件
        config_ok = True
        config_files = [
            'config/council_config.json',
            'config/council_config.example.json'
        ]
        
        for config_file in config_files:
            if Path(config_file).exists():
                config_ok &= self.validate_config_file(config_file)
        
        # 输出验证结果
        if self.validation_errors:
            logger.error(f"验证失败，发现 {len(self.validation_errors)} 个错误")
            for error in self.validation_errors:
                logger.error(f"  - {error}")
        
        if self.validation_warnings:
            logger.warning(f"发现 {len(self.validation_warnings)} 个警告")
            for warning in self.validation_warnings:
                logger.warning(f"  - {warning}")
        
        all_ok = required_ok and values_ok and config_ok
        
        if all_ok:
            logger.info("配置验证通过 ✅")
        else:
            logger.error("配置验证失败 ❌")
        
        return all_ok
    
    def get_report(self) -> Dict[str, Any]:
        """获取验证报告"""
        return {
            'valid': len(self.validation_errors) == 0,
            'errors': self.validation_errors,
            'warnings': self.validation_warnings,
            'error_count': len(self.validation_errors),
            'warning_count': len(self.validation_warnings),
        }


def validate_config(env_file: str = '.env') -> bool:
    """
    验证配置的便捷函数
    
    Args:
        env_file: .env 文件路径
    
    Returns:
        验证是否通过
    """
    validator = ConfigValidator(env_file)
    return validator.validate_all()


def check_config_with_exit(env_file: str = '.env') -> None:
    """
    验证配置，失败则退出程序
    
    Args:
        env_file: .env 文件路径
    """
    validator = ConfigValidator(env_file)
    
    if not validator.validate_all():
        error_count = len(validator.validation_errors)
        logger.critical(f"配置验证失败，发现 {error_count} 个错误，程序退出")
        
        print("\n配置验证失败，请检查以下问题:")
        for error in validator.validation_errors:
            print(f"  ❌ {error}")
        
        print("\n警告:")
        for warning in validator.validation_warnings:
            print(f"  ⚠️  {warning}")
        
        print("\n复制 .env.example 为 .env 并正确配置后重试。")
        
        import sys
        sys.exit(1)
