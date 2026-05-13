# 智慧教室环境监测系统 P0

本项目实现一个本地可运行的云边端协同智慧教室检测系统：

```text
sensor-simulator -> edge-service -> cloud-service + SQLite -> frontend
```

## 本地端口

- cloud-service: http://localhost:8000
- edge-service: http://localhost:8001
- frontend: http://localhost:5173

## 快速启动

分别打开四个终端。

### 1. 启动云端服务

```bash
cd cloud-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. 启动边缘服务

```bash
cd edge-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 3. 启动端侧模拟器

```bash
cd sensor-simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --mode mixed --interval 1
```

可选模式：

```text
normal, hot, co2, low_light, crowd, mixed
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173。

## AI 配置

前端不暴露模型配置入口。云端固定使用 GLM 免费模型，服务端通过环境变量配置：

```env
GLM_API_KEY=your-key
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4-flash
```

API Key 不写入源码，也不会由前端提交。

## 验证命令

```bash
cd edge-service
source .venv/bin/activate
python -m pytest -q
```

```bash
cd cloud-service
source .venv/bin/activate
python -m pytest -q
```

```bash
cd frontend
npm run build
```

## 验证结果

- Edge tests: pass
- Cloud tests: pass
- Frontend build: pass
- End-to-end data flow: sensor simulator can create A101 data and cloud APIs return latest metrics and abnormal events
