"""
网络数据采集器
使用 psutil 跨平台采集端口和连接信息
"""

import re
import psutil
from collections import Counter
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PortInfo:
    """监听端口信息"""
    port: int
    type: str  # 'system' or 'process'
    process_name: str
    process_pid: Optional[int]
    connections: int = 0
    last_update: Optional[datetime] = None

    def to_dict(self):
        return {
            'port': self.port,
            'type': self.type,
            'process_name': self.process_name,
            'process_pid': self.process_pid,
            'connections': self.connections,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


@dataclass
class ConnectionInfo:
    """已建立连接信息"""
    local_port: int
    remote_ip: str
    remote_port: int
    status: str
    timestamp: datetime

    def to_dict(self):
        return {
            'local_port': self.local_port,
            'remote_ip': self.remote_ip,
            'remote_port': self.remote_port,
            'status': self.status,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class HotSpot:
    """热点统计"""
    port: int
    count: int

    def to_dict(self):
        return {'port': self.port, 'count': self.count}


@dataclass
class IpHotSpot:
    """IP热点统计"""
    ip: str
    count: int

    def to_dict(self):
        return {'ip': self.ip, 'count': self.count}


class NetworkCollector:
    """网络数据采集器"""

    # 系统端口范围（通常小于1024）
    SYSTEM_PORT_THRESHOLD = 1024

    # 常见系统进程名称关键字
    SYSTEM_PROCESS_NAMES = {
        'system', 'sshd', 'nginx', 'apache', 'httpd', 'mysql', 
        'postgres', 'redis', 'memcached', 'docker', 'kube',
        'systemd', 'launchd', 'svchost', 'wininit'
    }

    def __init__(self, port_filter: str = "", exclude_ports: List[int] = None):
        self.port_filter_re = re.compile(port_filter) if port_filter else None
        self.exclude_ports = set(exclude_ports) if exclude_ports else set()
        self._ports: Dict[int, PortInfo] = {}
        self._connections: List[ConnectionInfo] = []
        self._port_counter = Counter()
        self._ip_counter = Counter()
        self._last_sample: Optional[datetime] = None

    def is_system_port(self, port: int, process_name: str) -> bool:
        """判断是否为系统服务端口"""
        if port < self.SYSTEM_PORT_THRESHOLD:
            return True
        
        lower_name = process_name.lower()
        for sys_name in self.SYSTEM_PROCESS_NAMES:
            if sys_name in lower_name:
                return True
        
        return False

    def sample(self) -> bool:
        """执行一次采样"""
        try:
            now = datetime.now()
            
            # 获取所有网络连接
            all_conns = psutil.net_connections(kind='inet')
            
            # 1. 收集监听端口
            new_ports: Dict[int, PortInfo] = {}
            for conn in all_conns:
                if conn.status != psutil.CONN_LISTEN:
                    continue
                
                port = conn.laddr.port
                if port in self.exclude_ports:
                    continue
                if self.port_filter_re and not self.port_filter_re.match(str(port)):
                    continue
                
                process_name = ""
                process_pid = None
                if conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        process_name = proc.name()
                        process_pid = conn.pid
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                port_type = 'system' if self.is_system_port(port, process_name) else 'process'
                
                new_ports[port] = PortInfo(
                    port=port,
                    type=port_type,
                    process_name=process_name,
                    process_pid=process_pid,
                    connections=0,
                    last_update=now
                )
            
            # 2. 收集已建立连接
            new_connections: List[ConnectionInfo] = []
            port_counter = Counter()
            ip_counter = Counter()
            
            for conn in all_conns:
                if conn.status != psutil.CONN_ESTABLISHED:
                    continue
                if not conn.raddr:  # 没有远程地址
                    continue
                
                local_port = conn.laddr.port
                if local_port in self.exclude_ports:
                    continue
                if self.port_filter_re and not self.port_filter_re.match(str(local_port)):
                    continue
                
                # 如果本地端口不在监听列表，跳过（出站连接）
                if local_port not in new_ports:
                    continue
                
                remote_ip = conn.raddr.ip
                remote_port = conn.raddr.port
                
                conn_info = ConnectionInfo(
                    local_port=local_port,
                    remote_ip=remote_ip,
                    remote_port=remote_port,
                    status=conn.status,
                    timestamp=now
                )
                new_connections.append(conn_info)
                
                # 统计
                port_counter[local_port] += 1
                ip_counter[remote_ip] += 1
                
                # 更新端口连接计数
                if local_port in new_ports:
                    new_ports[local_port].connections = port_counter[local_port]
            
            # 更新缓存
            self._ports = new_ports
            self._connections = new_connections
            self._port_counter = port_counter
            self._ip_counter = ip_counter
            self._last_sample = now
            
            logger.debug(f"采样完成: {len(self._ports)} 监听端口, {len(self._connections)} 活跃连接")
            return True
            
        except psutil.AccessDenied:
            logger.error("权限不足，无法读取完整网络连接信息，请使用管理员/root权限运行")
            return False
        except Exception as e:
            logger.error(f"采样失败: {e}", exc_info=True)
            return False

    def get_ports(self) -> List[PortInfo]:
        """获取所有监听端口"""
        return sorted(self._ports.values(), key=lambda p: p.port)

    def get_connections(self, page: int = 1, size: int = 50) -> Dict:
        """获取连接列表，分页"""
        start = (page - 1) * size
        end = start + size
        total = len(self._connections)
        connections = self._connections[start:end]
        return {
            'total': total,
            'page': page,
            'size': size,
            'data': [c.to_dict() for c in connections]
        }

    def get_top_ports(self, count: int = 5) -> List[HotSpot]:
        """获取连接数最多的端口"""
        top = self._port_counter.most_common(count)
        return [HotSpot(port=p, count=c) for p, c in top]

    def get_top_ips(self, count: int = 5) -> List[IpHotSpot]:
        """获取连接数最多的IP"""
        top = self._ip_counter.most_common(count)
        return [IpHotSpot(ip=i, count=c) for i, c in top]

    def get_stats(self) -> Dict:
        """获取整体统计"""
        return {
            'total_listen_ports': len(self._ports),
            'total_active_connections': len(self._connections),
            'last_sample': self._last_sample.isoformat() if self._last_sample else None
        }
