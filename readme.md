# 基于云边端协同的智能教室环境监测系统

本项目是一个可本地运行、也可部署到云服务器的云边端协同智能教室环境监测系统。系统用端侧模拟器产生教室环境数据，边缘侧进行数据校验、滑动窗口聚合和异常事件检测，云端完成持久化、查询和大模型分析，前端提供可视化仪表盘。

```text
sensor-simulator -> edge-service -> cloud-service + SQLite -> frontend
```

## 功能概览

- 端侧模拟温度、湿度、CO2、光照和人数数据。
- 边缘侧校验原始读数，维护每个教室的滑动窗口。
- 边缘侧检测高温、高 CO2、低光照、人数过多等异常事件。
- 云端存储教室、设备、聚合快照、异常事件和 AI 分析记录。
- 前端展示教室总览、详情曲线、异常事件和 AI 建议。
- 云端固定调用 GLM 免费模型，API Key 只保存在服务端环境变量中。

## 技术栈

- 后端：Python 3.11+、FastAPI、Pydantic、SQLAlchemy、SQLite、httpx
- 前端：React、Vite、TypeScript、ECharts、lucide-react
- 测试：pytest、FastAPI TestClient、TypeScript build
- 部署：Ubuntu、systemd、Nginx、Cloudflare Tunnel

## 目录结构

```text
.
├── cloud-service/       # 云端 API、SQLite 数据库、大模型分析
├── edge-service/        # 边缘侧 API、滑动窗口、异常检测
├── sensor-simulator/    # 端侧数据模拟器
├── frontend/            # React + Vite 可视化前端
└── readme.md
```

## 本地快速启动

### 1. 准备环境

需要安装：

- Python 3.11+
- Node.js 20+
- npm

建议分别为三个 Python 服务创建虚拟环境。

### 2. 启动云端服务

```bash
cd cloud-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export GLM_API_KEY="your-glm-api-key"
export GLM_API_URL="https://open.bigmodel.cn/api/paas/v4/chat/completions"
export GLM_MODEL="GLM-4.7-Flash"

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如果暂时不需要 AI 分析，可以不设置 `GLM_API_KEY`，其他数据采集、事件检测和前端展示仍可运行。

### 3. 启动边缘服务

```bash
cd edge-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export CLOUD_BASE_URL="http://127.0.0.1:8000"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### 4. 启动端侧模拟器

```bash
cd sensor-simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py --edge-url http://127.0.0.1:8001 --mode mixed --interval 20
```

可选模式：

```text
normal, hot, co2, low_light, crowd, mixed
```

参数说明：

- `--edge-url`：边缘服务地址。
- `--mode`：模拟数据模式。
- `--interval`：每轮数据间隔，单位秒。每轮会向 A101、A102、B201 三个教室各发送一条数据。

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开：

```text
http://localhost:5173
```

本地开发模式下，前端默认请求：

```text
http://localhost:8000
```

如果前端和后端不在同一台机器，可以在构建或启动前设置：

```bash
export VITE_API_BASE="https://your-api-domain.example.com"
```

## API 快速检查

云端健康检查：

```bash
curl http://127.0.0.1:8000/health
```

边缘侧健康检查：

```bash
curl http://127.0.0.1:8001/health
```

查看教室列表：

```bash
curl http://127.0.0.1:8000/api/v1/rooms
```

查看 A101 最新数据：

```bash
curl http://127.0.0.1:8000/api/v1/rooms/A101/latest
```

查看异常事件：

```bash
curl http://127.0.0.1:8000/api/v1/events
```

## 环境变量

### cloud-service

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./smart_classroom.db` | 云端数据库连接，默认使用 SQLite |
| `GLM_API_KEY` | 无 | GLM API Key，触发 AI 分析时必填 |
| `GLM_API_URL` | `https://open.bigmodel.cn/api/paas/v4/chat/completions` | GLM Chat Completions 地址 |
| `GLM_MODEL` | `GLM-4.7-Flash` | 使用的 GLM 模型 |

### edge-service

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CLOUD_BASE_URL` | `http://localhost:8000` | 云端服务地址 |

### frontend

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE` | 本地开发为 `http://localhost:8000`，生产构建为空字符串 | 前端访问云端 API 的基础地址 |

生产部署时，如果 Nginx 同时托管前端并反向代理 `/api/` 和 `/health` 到云端服务，可以不设置 `VITE_API_BASE`。

## 测试与构建

边缘侧测试：

```bash
cd edge-service
source .venv/bin/activate
python -m pytest -q
```

云端测试：

```bash
cd cloud-service
source .venv/bin/activate
python -m pytest -q
```

前端构建：

```bash
cd frontend
npm run build
```

## 云服务器快速部署参考

以下示例适用于 Ubuntu 服务器。命令中的路径、域名和密钥请替换为你自己的值，不要把真实 API Key 提交到 Git。

### 1. 安装系统依赖

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip nodejs npm nginx git
```

### 2. 拉取代码

```bash
sudo mkdir -p /opt/smart-classroom
sudo chown "$USER":"$USER" /opt/smart-classroom
git clone https://github.com/freecodetiger/Intelligent-Classroom-Environment-Monitoring-System-Based-on-Cloud-Edge-Device-Collaboration.git /opt/smart-classroom
cd /opt/smart-classroom
```

### 3. 安装后端依赖

```bash
cd /opt/smart-classroom/cloud-service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cd /opt/smart-classroom/edge-service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cd /opt/smart-classroom/sensor-simulator
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 4. 构建前端

```bash
cd /opt/smart-classroom/frontend
npm install
npm run build
sudo mkdir -p /var/www/classroom
sudo rsync -a --delete dist/ /var/www/classroom/
```

### 5. 配置云端环境变量

推荐把大模型配置放在服务器本地环境文件中，例如：

```bash
sudo tee /etc/smart-classroom-glm.env >/dev/null <<'EOF'
GLM_API_KEY=your-glm-api-key
GLM_API_URL=https://open.bigmodel.cn/api/paas/v4/chat/completions
GLM_MODEL=GLM-4.7-Flash
DATABASE_URL=sqlite:////opt/smart-classroom/cloud-service/smart_classroom.db
EOF

sudo chmod 600 /etc/smart-classroom-glm.env
```

### 6. 创建 systemd 服务

云端服务：

```bash
sudo tee /etc/systemd/system/smart-classroom-cloud.service >/dev/null <<'EOF'
[Unit]
Description=Smart Classroom Cloud FastAPI Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/smart-classroom/cloud-service
EnvironmentFile=/etc/smart-classroom-glm.env
ExecStart=/opt/smart-classroom/cloud-service/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

边缘服务：

```bash
sudo tee /etc/systemd/system/smart-classroom-edge.service >/dev/null <<'EOF'
[Unit]
Description=Smart Classroom Edge FastAPI Service
After=network-online.target smart-classroom-cloud.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/smart-classroom/edge-service
Environment=CLOUD_BASE_URL=http://127.0.0.1:8000
ExecStart=/opt/smart-classroom/edge-service/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

端侧模拟器：

```bash
sudo tee /etc/systemd/system/smart-classroom-simulator.service >/dev/null <<'EOF'
[Unit]
Description=Smart Classroom Sensor Simulator
After=network-online.target smart-classroom-edge.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/smart-classroom/sensor-simulator
ExecStart=/opt/smart-classroom/sensor-simulator/.venv/bin/python main.py --edge-url http://127.0.0.1:8001 --mode mixed --interval 20
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now smart-classroom-cloud.service
sudo systemctl enable --now smart-classroom-edge.service
sudo systemctl enable --now smart-classroom-simulator.service
```

检查状态：

```bash
systemctl status smart-classroom-cloud.service
systemctl status smart-classroom-edge.service
systemctl status smart-classroom-simulator.service
```

### 7. 配置 Nginx

```bash
sudo tee /etc/nginx/sites-available/smart-classroom >/dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    root /var/www/classroom;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/smart-classroom /etc/nginx/sites-enabled/smart-classroom
sudo nginx -t
sudo systemctl reload nginx
```

访问服务器本机验证：

```bash
curl http://127.0.0.1/health
```

### 8. 绑定公网域名

如果使用 Cloudflare Tunnel，可以在服务器上安装 `cloudflared`，登录 Cloudflare 并创建命名 Tunnel：

```bash
cloudflared tunnel login
cloudflared tunnel create smart-classroom
cloudflared tunnel route dns smart-classroom classroom.example.com
```

创建配置文件：

```bash
sudo mkdir -p /etc/cloudflared
sudo tee /etc/cloudflared/config.yml >/dev/null <<'EOF'
tunnel: your-tunnel-id
credentials-file: /root/.cloudflared/your-tunnel-id.json
no-autoupdate: true
ingress:
  - hostname: classroom.example.com
    service: http://127.0.0.1:80
  - service: http_status:404
EOF
```

安装并启动服务：

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared.service
```

DNS 中应看到类似记录：

```text
Type: CNAME
Name: classroom
Target: your-tunnel-id.cfargotunnel.com
Proxy: Proxied
```

不要把 CNAME 指向 `trycloudflare.com` 临时域名，否则可能触发 Cloudflare `Error 1014 CNAME Cross-User Banned`。

## 常见问题

### 前端一直显示旧时间的数据

确认云端 `/api/v1/rooms/{room_id}/history` 返回的是最近 100 条数据。当前代码会先按时间倒序取最近 100 条，再反转为时间升序输出，便于 ECharts 正常绘制趋势。

也可以直接检查：

```bash
curl http://127.0.0.1:8000/api/v1/rooms/A101/history
```

### 前端没有数据

按顺序检查：

```bash
systemctl status smart-classroom-simulator.service
systemctl status smart-classroom-edge.service
systemctl status smart-classroom-cloud.service
curl http://127.0.0.1:8000/api/v1/rooms
curl http://127.0.0.1:8000/api/v1/events
```

如果本地开发，请确认模拟器的 `--edge-url` 指向边缘服务，边缘服务的 `CLOUD_BASE_URL` 指向云端服务。

### AI 分析失败

检查云端环境变量：

```bash
systemctl show smart-classroom-cloud.service --property=Environment
journalctl -u smart-classroom-cloud.service -n 100 --no-pager
```

确认 `GLM_API_KEY` 已在服务器端设置，并且没有提交到 Git 仓库。

### Cloudflare Tunnel 可以访问前端，但 API 失败

检查 Nginx 是否代理了 `/api/` 和 `/health`：

```bash
sudo nginx -T | grep -E "location /api|location /health|proxy_pass"
curl http://127.0.0.1/health
```

## 安全说明

- 不要提交 `ecs.md`、`.env`、API Key、服务器密码、代理节点配置等敏感文件。
- GLM API Key 应只保存在服务器环境变量或受限权限的环境文件中。
- 生产环境建议使用 HTTPS、最小开放端口、数据库备份和日志监控。
