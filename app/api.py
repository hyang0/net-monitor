"""
Flask API 路由
"""

from flask import Blueprint, jsonify, request
from .collector import NetworkCollector
from .config import Config

api = Blueprint('api', __name__)
collector: NetworkCollector = None
config: Config = None


def init_api(c: NetworkCollector, cfg: Config):
    global collector, config
    collector = c
    config = cfg
    return api


@api.route('/api/ports', methods=['GET'])
def get_ports():
    """获取所有监听端口"""
    ports = collector.get_ports()
    return jsonify([p.to_dict() for p in ports])


@api.route('/api/connections', methods=['GET'])
def get_connections():
    """获取活跃连接，支持分页"""
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 50, type=int)
    result = collector.get_connections(page, size)
    return jsonify(result)


@api.route('/api/top', methods=['GET'])
def get_top():
    """获取热点信息"""
    count = request.args.get('count', 5, type=int)
    top_ports = [p.to_dict() for p in collector.get_top_ports(count)]
    top_ips = [ip.to_dict() for ip in collector.get_top_ips(count)]
    stats = collector.get_stats()
    return jsonify({
        'top_ports': top_ports,
        'top_ips': top_ips,
        'stats': stats
    })


@api.route('/api/stats', methods=['GET'])
def get_stats():
    """获取整体统计"""
    return jsonify(collector.get_stats())


@api.route('/api/config', methods=['GET'])
def get_config():
    """获取当前配置（不包含敏感信息）"""
    return jsonify({
        'sample_interval': config.sample_interval,
        'port_filter': config.port_filter,
        'exclude_ports': config.exclude_ports,
        'alert': {
            'port_connection_threshold': config.alert['port_connection_threshold'],
            'ip_connection_threshold': config.alert['ip_connection_threshold'],
            'email_enabled': config.alert['email']['enabled'],
            'slack_enabled': config.alert['slack']['enabled']
        },
        'language': config.language
    })


@api.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    data = request.get_json()
    if 'sample_interval' in data:
        config.sample_interval = int(data['sample_interval'])
    if 'port_filter' in data:
        config.port_filter = data['port_filter']
    if 'exclude_ports' in data:
        config.exclude_ports = data['exclude_ports']
    if 'alert' in data and 'port_connection_threshold' in data['alert']:
        config.alert['port_connection_threshold'] = int(data['alert']['port_connection_threshold'])
    if 'alert' in data and 'ip_connection_threshold' in data['alert']:
        config.alert['ip_connection_threshold'] = int(data['alert']['ip_connection_threshold'])
    if 'language' in data:
        config.language = data['language']
    
    # 这里需要调用者保存配置到文件
    return jsonify({'status': 'ok', 'message': '配置已更新'})
