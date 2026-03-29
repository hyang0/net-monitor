#!/usr/bin/env python3
"""
网络会话监控系统 - 启动入口
"""

import argparse
import sys
from app import create_app
from app.config import Config


def main():
    parser = argparse.ArgumentParser(description='网络会话监控系统')
    parser.add_argument('--config', '-c', default='config.yaml', help='配置文件路径')
    parser.add_argument('--host', '-H', help='监听主机 (覆盖配置)')
    parser.add_argument('--port', '-p', type=int, help='监听端口 (覆盖配置)')
    args = parser.parse_args()

    # 检查配置文件是否存在
    config_path = args.config
    cfg = Config()
    if not cfg.load(config_path):
        print(f"错误: 无法加载配置文件 {config_path}")
        sys.exit(1)
    
    # 命令行参数覆盖配置
    if args.host:
        cfg.web['host'] = args.host
    if args.port:
        cfg.web['port'] = args.port
    
    # 创建应用
    app = create_app(config_path)
    
    # 启动
    host = cfg.web.get('host', '0.0.0.0')
    port = cfg.web.get('port', 5000)
    debug = cfg.web.get('debug', False)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                     网络会话监控系统                            ║
║                     Network Session Monitor                     ║
╠══════════════════════════════════════════════════════════════╣
║  启动参数:                                                   ║
║    配置文件: {config_path:<40}  ║
║    监听地址: {host}:{port:<34}  ║
║    调试模式: {str(debug):<32}  ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
