# index-board

多市场指数看板：实时/日更行情、十年 PE 分位、历史走势、卡片拖拽排序。

## 功能

- 沪深300、A500、红利低波、白酒、创业板、科创50/100
- 恒生、恒科、纳指、DAX、黄金、原油、XOP、万家周期视野C
- 中/美十年期国债收益率
- 卡片估值指标（官方 PE 或 10 年价格/收益率分位）
- 按估值便宜→贵排序
- 底部抽屉历史图

## 数据说明

详见 [DATA_SOURCES.md](DATA_SOURCES.md)

---

## 快速启动

### 前置要求

- Python 3.9+
- pip（Python 包管理工具）

### 1. 克隆仓库

```bash
git clone https://github.com/sktt13ef/index-board.git
cd index-board
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

推荐使用虚拟环境：

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 运行应用

```bash
python app.py
```

### 4. 打开浏览器

访问 http://127.0.0.1:5000

---

## 部署到服务器

以下为几种常见部署方式，按推荐程度排序。

### 方式一：使用 Gunicorn + Nginx（Linux 生产环境推荐）

#### 安装 Gunicorn

```bash
pip install gunicorn
```

#### 修改 app.py

将最后一行从 `socketio.run(...)` 改为支持 WSGI 启动：

```python
# 在 app.py 末尾添加
if __name__ == "__main__":
    import threading
    stock_provider.get_all_indices(force_refresh=True)
    threading.Thread(
        target=stock_provider.update_valuation_cache,
        daemon=True,
    ).start()
    stock_provider.start_auto_update(interval=30)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)
```

#### 使用 Gunicorn 启动

```bash
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 -b 0.0.0.0:5000 app:app
```

> 注意：Flask-SocketIO 需要 gevent-websocket 支持，先安装：`pip install gevent-websocket`

#### Nginx 反向代理配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 使用 systemd 管理进程（建议）

创建 `/etc/systemd/system/index-board.service`：

```ini
[Unit]
Description=Index Board Dashboard
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/index-board
Environment="PATH=/path/to/index-board/venv/bin"
ExecStart=/path/to/index-board/venv/bin/gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 -b 127.0.0.1:5000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable index-board
sudo systemctl start index-board
```

### 方式二：使用 Waitress（Windows 服务器）

```bash
pip install waitress
```

启动命令：

```bash
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

### 方式三：使用 Screen / tmux 后台运行（简单场景）

```bash
screen -S index-board
python app.py
# Ctrl+A, D 分离会话
```

### 方式四：Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
```

创建 `docker-compose.yml`（可选）：

```yaml
version: '3'
services:
  index-board:
    build: .
    ports:
      - "5000:5000"
    restart: always
```

构建并运行：

```bash
docker build -t index-board .
docker run -d -p 5000:5000 --name index-board --restart always index-board
```

或者使用 docker compose：

```bash
docker-compose up -d
```

---

## 端口

默认端口为 `5000`。如需修改，编辑 `app.py` 最后一行中的 `port` 参数：

```python
socketio.run(app, host="0.0.0.0", port=8080, debug=True, use_reloader=False)
```

## 自动更新

应用启动后每 30 秒自动刷新行情数据（可通过 `stock_provider.start_auto_update(interval=30)` 调整间隔）。

## 项目结构

```
index-board/
├── app.py                      # Flask 应用入口
├── stock_data.py               # 股票数据提供者（主逻辑）
├── stock_data_realtime.py      # 实时估值模块
├── history_data_manager.py     # 历史数据管理器
├── init_history_data.py        # 初始化历史数据
├── update_history_data.py      # 更新历史数据
├── local_valuation_calculator.py  # 本地估值计算器
├── validate_data_quality.py    # 数据质量验证
├── requirements.txt            # Python 依赖
├── data/history/               # 历史数据缓存目录
├── templates/
│   └── index.html              # 前端页面
└── README.md                   # 本文件
```
