"""
FractalClaw 日志模块

提供统一的日志记录功能，支持多级别、日志格式配置。
"""

import logging
import sys
from typing import Optional

from .exceptions import FractalClawException

# 默认日志格式
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class Logger:
    """
    FractalClaw 日志记录器

    提供统一的日志接口，支持控制台和文件输出。
    """

    _instances: dict = {}

    def __init__(
        self,
        name: str,
        level: str = "INFO",
        log_file: Optional[str] = None,
        format_string: Optional[str] = None,
    ):
        self.name = name
        self.level = LOG_LEVELS.get(level.upper(), logging.INFO)
        self.log_file = log_file
        self.format_string = format_string or DEFAULT_FORMAT

        self._logger = self._create_logger()

    def _create_logger(self) -> logging.Logger:
        """创建日志记录器"""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)

        # 避免重复添加 handler
        if logger.handlers:
            return logger

        # 设置格式
        formatter = logging.Formatter(self.format_string, DATE_FORMAT)

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件输出（如果指定）
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
            file_handler.setLevel(self.level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    @classmethod
    def get_logger(
        cls,
        name: str,
        level: str = "INFO",
        log_file: Optional[str] = None,
    ) -> "Logger":
        """
        获取日志记录器实例（单例模式）

        Args:
            name: 日志记录器名称
            level: 日志级别
            log_file: 日志文件路径

        Returns:
            Logger 实例
        """
        key = f"{name}:{level}:{log_file}"
        if key not in cls._instances:
            cls._instances[key] = cls(name, level, log_file)
        return cls._instances[key]

    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """记录一般信息"""
        self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """记录警告信息"""
        self._logger.warning(message, extra=kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs):
        """
        记录错误信息

        Args:
            message: 错误消息
            exc_info: 是否包含异常堆栈信息
        """
        if exc_info:
            self._logger.exception(message, extra=kwargs)
        else:
            self._logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """记录严重错误信息"""
        self._logger.critical(message, extra=kwargs)

    def log_exception(self, exception: FractalClawException):
        """记录 FractalClaw 异常"""
        self.error(
            str(exception),
            exc_info=True,
            error_code=exception.error_code,
            details=exception.details,
        )


# 全局日志记录器
def get_logger(name: str, level: str = "INFO") -> Logger:
    """
    便捷函数：获取全局日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别

    Returns:
        Logger 实例
    """
    return Logger.get_logger(f"fractalclaw.{name}", level)


# 预定义的日志记录器
agent_logger = get_logger("agent")
memory_logger = get_logger("memory")
executor_logger = get_logger("executor")
planner_logger = get_logger("planner")
core_logger = get_logger("core")
