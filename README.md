# 网络会话监控 Network Session Monitor

跨平台网络会话监控系统，通过识别本机开放端口并统计连接数，提供 Web 可视化仪表盘。

## 📋 功能特性

✅ **端口扫描** - 获取本机所有 LISTEN 状态端口，自动区分系统服务/后台进程  
✅ **会话监控** - 提取 ESTABLISHED 状态 TCP 连接，关联到监听端口  
✅ **数据统计** - 按端口/IP 统计连接数，找出热点  
✅ **Web 可视化** - Bootstrap + Chart.js 实时仪表盘  
✅ **告警通知** - 连接数超过阈值时发送邮件/Slack 告警  
✅ **配置热加载** - 修改配置文件自动生效  
✅ **跨平台** - 支持 Windows / Linux / macOS  
✅ **日志轮转** - 内置按天轮转日志  

## 🚀 快速开始

### 依赖安装

```bash
# 克隆/创建项目后
cd net-monitor
pip install -r requirements.txt
```

### 运行

```bash
python run.py

# 指定配置文件
python run.py --config /path/to/config.yaml

# 指定端口
python run.py -p 8080
```

### 访问

打开浏览器访问: http://localhost:5000

## ⚙️ 配置说明

编辑 `config.yaml`:

```yaml
# 采样间隔（秒）
sample_interval: 5

# 日志配置
log:
  path: "./monitor.log"
  rotation_days: 7
  level: "INFO"

# Web 服务
web:
  host: "0.0.0.0"
  port: 5000
  debug: false

# 语言
language: "zh-CN"
```

## 🔌 API 文档

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/ports` | GET | 获取所有监听端口 |
| `/api/connections?page=1&size=50` | GET | 获取连接列表（分页） |
| `/api/top?count=5` | GET | 获取热点端口/IP |
| `/api/stats` | GET | 获取整体统计 |
| `/api/config` | GET | 获取当前配置 |
| `/api/config` | POST | 更新配置 |

## 🐳 Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "run.py"]
```

构建运行:

```bash
docker build -t net-monitor .
docker run -d --net=host -p 5000:5000 -v $(pwd)/config.yaml:/app/config.yaml net-monitor
```

> **注意**: 需要 `--net=host` 才能正确读取主机网络信息

## 📊 界面预览

页面包含:
- 顶部统计卡片（监听端口数、活跃连接数、最后更新）
- 热门端口TOP5柱状图
- 热门IP TOP5柱状图  
- 监听端口表格（含类型区分）
- 最新活跃连接列表

数据每 **5秒** 自动刷新。

## 🔐 权限说明

- **Linux**: 需要 `root` 或 `cap_net_admin` 权限才能读取完整连接信息
- **Windows**: 需要以管理员身份运行
- **macOS**: 需要终端开发者权限

没有足够权限会降级运行，仍可读取部分信息。

## 📝 项目结构

```
net-monitor/
├── app/
│   ├── __init__.py     # 主应用初始化
│   ├── collector.py    # 网络数据采集
│   ├── config.py       # 配置管理 & 热加载
│   ├── alerts.py       # 告警管理器
│   └── api.py          # Flask API 路由
├── templates/
│   └── index.html      # 前端页面
├── static/             # 静态资源（可选）
├── config.yaml         # 配置文件
├── requirements.txt    # Python 依赖
├── run.py              # 启动入口
└── README.md           # 说明文档
```

## 📄 许可证

MIT License
