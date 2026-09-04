#!/usr/bin/env python3
"""
P2-5: 统一日志配置
所有模块使用统一的结构化JSON日志
"""
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
LOG_DIR = ROOT / "logs"

class StructuredFormatter(logging.Formatter):
    """结构化JSON日志格式化器"""
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage()
        }
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        return json.dumps(log_entry, ensure_ascii=False)

def get_logger(name: str, level: str = "INFO", log_file: str = None) -> logging.Logger:
    """获取统一配置的logger"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)
    
    # 文件输出
    if log_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_DIR / log_file)
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)
    
    return logger

def log_event(logger: logging.Logger, event_type: str, detail: dict, level: str = "info"):
    """记录结构化事件"""
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level.upper(), logging.INFO),
        pathname="",
        lineno=0,
        msg=event_type,
        args=(),
        exc_info=None
    )
    record.extra_fields = {"event_type": event_type, "detail": detail}
    logger.handle(record)

if __name__ == "__main__":
    logger = get_logger("test", log_file="test_unified.log")
    log_event(logger, "system_start", {"status": "ok"})
    log_event(logger, "config_loaded", {"modules": 5}, "debug")
    print("统一日志配置测试完成")
