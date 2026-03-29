"""
配置管理 - 支持热加载
"""

import yaml
import logging
from typing import Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import threading

logger = logging.getLogger(__name__)


class Config:
    """配置类"""
    def __init__(self):
        self.sample_interval: int = 5
        self.port_filter: str = ""
        self.exclude_ports: list = []
        self.alert: Dict = {
            "port_connection_threshold": 100,
            "ip_connection_threshold": 50,
            "email": {"enabled": False},
            "slack": {"enabled": False}
        }
        self.log: Dict = {
            "path": "./monitor.log",
            "rotation_days": 7,
            "level": "INFO"
        }
        self.web: Dict = {
            "host": "0.0.0.0",
            "port": 5000,
            "debug": False
        }
        self.language: str = "zh-CN"

    def load(self, config_path: str) -> bool:
        """从YAML文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"配置文件 {config_path} 为空，使用默认配置")
                return True
            
            # 遍历加载
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            logger.info(f"配置已加载: {config_path}")
            return True
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False

    def save(self, config_path: str) -> bool:
        """保存配置到文件"""
        try:
            data = {
                'sample_interval': self.sample_interval,
                'port_filter': self.port_filter,
                'exclude_ports': self.exclude_ports,
                'alert': self.alert,
                'log': self.log,
                'web': self.web,
                'language': self.language
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"配置已保存: {config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False


class ConfigChangeHandler(FileSystemEventHandler):
    """配置文件变化处理器"""
    def __init__(self, config: Config, config_path: str, callback=None):
        self.config = config
        self.config_path = config_path
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory and os.path.abspath(event.src_path) == os.path.abspath(self.config_path):
            logger.info("检测到配置文件变化，重新加载...")
            self.config.load(self.config_path)
            if self.callback:
                self.callback()


class ConfigWatcher:
    """配置文件热加载监控"""
    def __init__(self, config: Config, config_path: str, callback=None):
        self.config = config
        self.config_path = config_path
        self.callback = callback
        self.observer: Optional[Observer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """启动监控"""
        if not os.path.exists(self.config_path):
            logger.warning(f"配置文件不存在，无法监控: {self.config_path}")
            return
        
        event_handler = ConfigChangeHandler(self.config, self.config_path, self.callback)
        self.observer = Observer()
        self.observer.schedule(event_handler, os.path.dirname(self.config_path) or '.', recursive=False)
        self.observer.start()
        logger.info(f"配置热加载已启动: {self.config_path}")

    def stop(self):
        """停止监控"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
