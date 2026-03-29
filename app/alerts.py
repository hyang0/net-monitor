"""
告警模块 - 支持邮件和Slack告警
"""

import logging
import smtplib
from email.mime.text import MIMEText
import json
import requests
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AlertContext:
    """告警上下文"""
    port_threshold: int
    ip_threshold: int
    top_ports: list
    top_ips: list
    timestamp: str


class AlertManager:
    """告警管理器"""

    def __init__(self, config: Dict):
        self.config = config
        self.last_alerts: Dict[str, str] = {}  # 防止频繁告警

    def check_and_alert(self, context: AlertContext) -> None:
        """检查并发送告警"""
        # 检查端口阈值
        for port_info in context.top_ports:
            port = port_info.get('port')
            count = port_info.get('count')
            if count >= context.port_threshold:
                self._send_port_alert(port, count, context.timestamp)
        
        # 检查IP阈值
        for ip_info in context.top_ips:
            ip = ip_info.get('ip')
            count = ip_info.get('count')
            if count >= context.ip_threshold:
                self._send_ip_alert(ip, count, context.timestamp)

    def _send_port_alert(self, port: int, count: int, timestamp: str) -> None:
        """发送端口告警"""
        key = f"port_{port}"
        # 简单去重，同一小时内不重复告警
        if self._should_suppress(key, timestamp):
            return
        
        message = f"⚠️ 端口连接数告警\n端口: {port}\n当前连接数: {count}\n阈值: {self.config['port_connection_threshold']}\n时间: {timestamp}"
        
        logger.warning(message)
        self._send_email(message)
        self._send_slack(message)

    def _send_ip_alert(self, ip: str, count: int, timestamp: str) -> None:
        """发送IP告警"""
        key = f"ip_{ip}"
        if self._should_suppress(key, timestamp):
            return
        
        message = f"⚠️ IP连接数告警\n远程IP: {ip}\n当前连接数: {count}\n阈值: {self.config['ip_connection_threshold']}\n时间: {timestamp}"
        
        logger.warning(message)
        self._send_email(message)
        self._send_slack(message)

    def _should_suppress(self, key: str, timestamp: str) -> bool:
        """判断是否应该抑制告警（防止刷屏）"""
        # 简单按小时去重
        hour = timestamp[:13]  # YYYY-MM-DDTHH
        last = self.last_alerts.get(key)
        if last == hour:
            return True
        self.last_alerts[key] = hour
        return False

    def _send_email(self, message: str) -> None:
        """发送邮件告警"""
        email_cfg = self.config.get('email', {})
        if not email_cfg.get('enabled'):
            return
        
        try:
            msg = MIMEText(message, 'plain', 'utf-8')
            msg['Subject'] = '网络会话监控告警'
            msg['From'] = email_cfg['username']
            msg['To'] = email_cfg['to']
            
            with smtplib.SMTP(email_cfg['smtp_server'], email_cfg['smtp_port'], timeout=10) as server:
                server.starttls()
                server.login(email_cfg['username'], email_cfg['password'])
                server.send_message(msg)
            
            logger.info("邮件告警已发送")
        except Exception as e:
            logger.error(f"发送邮件告警失败: {e}")

    def _send_slack(self, message: str) -> None:
        """发送Slack告警"""
        slack_cfg = self.config.get('slack', {})
        if not slack_cfg.get('enabled') or not slack_cfg.get('webhook_url'):
            return
        
        try:
            payload = {
                "text": message
            }
            response = requests.post(
                slack_cfg['webhook_url'],
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info("Slack告警已发送")
        except Exception as e:
            logger.error(f"发送Slack告警失败: {e}")
