# Vision Memory Agent 后端说明

## 1. 后端功能说明

后端运行在 RDK X3 上，负责 USB 摄像头采集、MJPEG 视频流输出、目标检测、视觉记忆生成与去重、状态聚合接口，以及手势/触控状态接口。FastAPI 入口为 `app.main:app`。

## 2. 后端运行环境

- RDK X3 4GB
- USB 摄像头
- Python 3
- FastAPI / Uvicorn
- OpenCV / NumPy / Pydantic
- ONNX 目标检测模型：`models/yolov5n.onnx`

## 3. 依赖安装

```bash
cd ~/vision-memory-agent/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. 启动命令

```bash
cd ~/vision-memory-agent/backend
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

也可以执行：

```bash
bash start_backend.sh
```

## 5. API 接口

- `GET /api/health`：健康检查，返回项目、设备和摄像头状态。
- `GET /api/video/stream`：MJPEG 摄像头视频流。
- `GET /api/video/snapshot`：当前摄像头 JPEG 截图。
- `GET /api/video/gesture-frame`：前端手势识别用低分辨率 JPEG 帧。
- `GET /api/status/current`：综合状态，包含摄像头、视觉记忆和交互状态。
- `GET /api/memory/status`：视觉记忆兼容状态接口。
- `POST /api/memory/reset`：重置视觉记忆。
- `GET /api/vision-memory/status`：视觉记忆状态接口。
- `POST /api/vision-memory/reset`：重置视觉记忆。
- `GET /api/vision-touch/status`：手势/触控状态。
- `GET /api/vision-touch/config`：手势/触控配置。
- `POST /api/vision-touch/config`：更新手势/触控配置。

## 6. 模型文件说明

当前代码在 `app/services/vision_memory/object_tracker.py` 中优先加载 `models/yolov5n.onnx`。本核心代码包只保留该实际使用模型，未复制未被当前加载列表引用的重复模型文件。

## 7. 常见问题

- 摄像头离线：检查 USB 摄像头连接，并确认 `app/core/settings.py` 中 `camera_device` 默认 `/dev/video8` 是否与实际设备一致。
- 前端无法访问：确认 RDK 与 PC 在同一网络，后端监听 `0.0.0.0:8000`，并检查防火墙。
- 模型未加载：确认 `models/yolov5n.onnx` 存在且 OpenCV DNN 能读取。
- 记忆为空：先确认 `/api/video/stream` 有画面，再放入水杯、手机、书本等目标等待检测更新。
