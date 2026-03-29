"""
网络会话监控 - 主应用
"""

import logging
from logging.handlers import TimedRotatingFileHandler
import asyncio
import threading
from datetime import datetime
from flask import Flask, render_template
from .collector import NetworkCollector
from .config import Config, ConfigWatcher
from .api import api, init_api
from .alerts import AlertManager, AlertContext

__version__ = "1.0.0"


def setup_logging(config: Config):
    """配置日志"""
    log_level = getattr(logging, config.log.get('level', 'INFO'), logging.INFO)
    log_path = config.log.get('path', './monitor.log')
    rotation_days = config.log.get('rotation_days', 7)
    
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # 文件轮转
    file_handler = TimedRotatingFileHandler(
        log_path,
        when='D',
        interval=1,
        backupCount=rotation_days,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def create_app(config_path: str = "config.yaml") -> Flask:
    """创建Flask应用"""
    # 加载配置
    cfg = Config()
    cfg.load(config_path)
    
    # 设置日志
    setup_logging(cfg)
    logger = logging.getLogger(__name__)
    
    # 创建采集器
    collector = NetworkCollector(
        port_filter=cfg.port_filter,
        exclude_ports=cfg.exclude_ports
    )
    
    # 初始采样
    collector.sample()
    
    # 创建Flask应用
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # 注册API
    init_api(collector, cfg)
    app.register_blueprint(api)
    
    # 告警管理器
    alert_manager = AlertManager(cfg.alert)
    
    # 前端首页
    @app.route('/')
    def index():
        return render_template('index.html', language=cfg.language)
    
    # 后台采样任务
    def sampling_loop():
        while True:
            try:
                success = collector.sample()
                if success:
                    # 检查告警
                    top_ports = [p.to_dict() for p in collector.get_top_ports(10)]
                    top_ips = [ip.to_dict() for ip in collector.get_top_ips(10)]
                    ctx = AlertContext(
                        port_threshold=cfg.alert['port_connection_threshold'],
                        ip_threshold=cfg.alert['ip_connection_threshold'],
                        top_ports=top_ports,
                        top_ips=top_ips,
                        timestamp=datetime.now().isoformat()
                    )
                    alert_manager.check_and_alert(ctx)
            except Exception as e:
                logger.error(f"采样循环异常: {e}", exc_info=True)
            
            # 等待下一次采样
            import time
            time.sleep(cfg.sample_interval)
    
    # 启动后台采样线程
    thread = threading.Thread(target=sampling_loop, daemon=True)
    thread.start()
    logger.info(f"后台采样线程已启动，间隔: {cfg.sample_interval}秒")
    
    # 启动配置热加载
    config_watcher = ConfigWatcher(cfg, config_path, callback=lambda: None)
    config_watcher.start()
    logger.info("配置热加载已启动")
    
    return app