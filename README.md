
# Vision Memory Agent

## 基于 RDK X3 的视觉记忆型边缘智能体

---

## 项目简介

Vision Memory Agent 是运行在 RDK X3 边缘计算平台上的视觉智能系统，实现实时视频分析、目标识别与视觉记忆建模。

系统通过摄像头获取画面，在本地完成目标检测与记忆构建，并通过 Web 前端进行三维可视化展示。

---

## 核心功能

- 实时摄像头视频采集（USB Camera）
- 边缘端目标检测（人 / 物体）
- 视觉记忆构建（出现 / 消失 / 时长记录）
- 基础手势交互
- Web 前端可视化
- Three.js 三维记忆空间

---

## 系统架构

RDK X3（边缘端）
- 视频采集模块
- 目标检测模块
- 视觉记忆模块
- FastAPI 后端服务

↓  

本地前端（Frontend）
- React + Vite
- Three.js
- UI展示层

---

## 项目结构

VisionMemoryAgent/
- backend/   后端服务（RDK X3）
- frontend/  前端可视化
- docs/      项目文档

---

## 快速启动

### 后端（RDK X3）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

```

------

### 前端

```bash

cd frontend
npm install
npm run dev
```



## 访问地址

前端：[http://localhost:5173](http://localhost:5173/)
后端：[http://localhost:8000](http://localhost:8000/)

------

## 项目特点

- 视觉记忆机制（记录目标出现与消失）
- 边缘计算本地推理
- 实时视觉 + 手势交互
- 三维空间可视化
- 完整感知-记忆闭环系统

------

## 应用场景

- 智能学习陪伴系统
- AI视觉监控
- 人机交互实验平台
- 视觉记忆增强系统

------

## 技术栈

- Python 3 / FastAPI
- OpenCV
- ONNX Runtime
- React + Vite
- Three.js
- RDK X3

------

## 项目状态

- 已完成核心功能
- 已完成前后端联调
- 支持实时视频流
- 支持目标识别
- 支持视觉记忆系统
- 支持Web可视化

------
