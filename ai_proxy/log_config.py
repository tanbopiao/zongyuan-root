"""统一日志配置 - 所有服务共用"""
import logging, os, time

LOG_DIR = "/opt/ZONGYUAN-ROOT/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name, level=logging.INFO):
    """获取统一格式的logger"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    fh = logging.FileHandler(os.path.join(LOG_DIR, name + ".log"))
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    return logger
