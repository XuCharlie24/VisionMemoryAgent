# Vision Memory Agent Frontend

本目录是本地 Windows 前端项目，技术栈为 React + Vite + JSX + SCSS + Three.js。

## 启动

```bat
cd /d E:\vision-memory-agent\frontend
npm run dev
```

## 构建

```bat
npm run build
```

## API 地址

默认读取 `.env.local`：

```env
VITE_RDK_API_BASE=http://172.20.10.2:8000
```

## 页面组成

- CameraPanel：显示 RDK X3 MJPEG 摄像头流
- HologramStage：Three.js 3D 科技舞台
- MemoryPanel：视觉记忆状态与目标列表
- GestureStatusPanel：空中交互状态
- TouchControlPanel：模式切换、平滑参数、记忆重置
- AirCursor：根据后端 cursor 状态显示空中光标

## 说明

请先在 RDK X3 上启动后端，再启动前端。不要把本前端目录上传到板子。

