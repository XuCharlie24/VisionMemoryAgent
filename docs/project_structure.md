# 项目结构说明

## 后端

- 主程序入口：`backend/app/main.py`
- API 路由目录：`backend/app/api/`
- 健康检查接口：`backend/app/api/health_routes.py`
- 视频流接口：`backend/app/api/video_routes.py`
- 状态接口：`backend/app/api/status_routes.py`
- 视觉记忆接口：`backend/app/api/vision_memory_routes.py`
- 手势/触控接口：`backend/app/api/vision_touch_routes.py`
- 状态管理：`backend/app/core/app_state.py`
- 配置文件：`backend/app/core/settings.py`
- 数据结构：`backend/app/core/schemas.py`
- 摄像头采集模块：`backend/app/services/camera_service.py`
- 视觉记忆引擎：`backend/app/services/vision_memory/memory_engine.py`
- 视觉记忆存储/去重：`backend/app/services/vision_memory/memory_store.py`
- 目标检测与位置识别：`backend/app/services/vision_memory/object_tracker.py`
- 视觉记忆配置：`backend/app/services/vision_memory/config.py`
- 手势/触控引擎：`backend/app/services/vision_touch/gesture_engine.py`
- 手部跟踪模块：`backend/app/services/vision_touch/hand_tracker.py`
- 手势状态常量：`backend/app/services/vision_touch/touch_state.py`
- 后端模型目录：`backend/models/`
- 当前模型文件：`backend/models/yolov5n.onnx`

## 前端

- 前端入口：`frontend/src/main.jsx`
- 应用入口组件：`frontend/src/App.jsx`
- 主页面：`frontend/src/pages/VisionMemoryAgentPage.jsx`
- API 基础服务：`frontend/src/services/rdkApi.js`
- 视觉记忆 API：`frontend/src/services/visionMemoryApi.js`
- 手势/触控 API：`frontend/src/services/visionTouchApi.js`
- 手势识别服务：`frontend/src/services/HandLandmarkerService.js`
- 记忆数据归一化：`frontend/src/services/memoryNormalize.js`
- 摄像头组件：`frontend/src/components/camera/CameraPanel.jsx`
- 三维记忆空间组件：`frontend/src/components/hologram/HologramStage.jsx`
- 视觉记忆面板：`frontend/src/components/vision-memory/MemoryPanel.jsx`
- 视觉记忆卡片：`frontend/src/components/vision-memory/ObjectCards.jsx`
- 事件时间线组件：`frontend/src/components/vision-memory/MemoryTimeline.jsx`
- 空中光标组件：`frontend/src/components/vision-touch/AirCursor.jsx`
- 手势状态面板：`frontend/src/components/vision-touch/GestureStatusPanel.jsx`
- 触控控制面板：`frontend/src/components/vision-touch/TouchControlPanel.jsx`
- 样式文件：`frontend/src/styles/vision-memory-agent.scss`
- 静态资源目录：`frontend/public/`
- 前端手势模型资源：`frontend/public/models/`
- MediaPipe 静态资源：`frontend/public/vendor/mediapipe/`
- MediaPipe 资源复制脚本：`frontend/scripts/copy-mediapipe-tasks-assets.mjs`
