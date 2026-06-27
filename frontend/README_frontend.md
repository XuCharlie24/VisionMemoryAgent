# Vision Memory Agent 前端说明

## 1. 前端功能说明

前端运行在 Windows 本地电脑，基于 React + Vite + Three.js + MediaPipe Tasks Vision。主要功能包括 RDK X3 视频流展示、视觉记忆列表、三维记忆空间、事件时间线、手势交互状态、记忆切换/锁定/详情查看和后端状态监控。

## 2. Node.js 版本建议

建议使用 Node.js 20 LTS 或更新版本。项目依赖通过 `package.json` 与 `package-lock.json` 恢复，核心代码包不包含 `node_modules`。

## 3. 依赖安装

```bat
cd /d E:\vision-memory-agent\frontend
npm install
```

`postinstall` 会执行 `scripts/copy-mediapipe-tasks-assets.mjs`，用于复制 MediaPipe 手势模型运行所需的静态资源。

## 4. 启动命令

```bat
cd /d E:\vision-memory-agent\frontend
npm run dev
```

## 5. 后端地址配置

项目实际读取环境变量 `VITE_RDK_API_BASE`。`.env.example` 内容为：

```env
VITE_RDK_API_BASE=http://172.20.10.2:8000
```

如果 RDK X3 IP 变化，请在本地 `.env.local` 中修改该地址。

## 6. 手势模型资源说明

手势识别由前端 `src/services/HandLandmarkerService.js` 使用 MediaPipe Tasks Vision 完成。核心静态资源位于：

- `public/models/hand_landmarker.task`
- `public/models/hand/`
- `public/vendor/mediapipe/`

这些资源需要随前端核心代码一起打包。

## 7. 常见问题

- 页面无视频：确认后端已启动，并能访问 `http://172.20.10.2:8000/api/video/stream`。
- API 离线：确认 `.env.local` 或 `.env.example` 中 RDK 地址正确。
- 手势不可用：确认 `public/models` 和 `public/vendor/mediapipe` 已存在，重新执行 `npm install`。
- 依赖缺失：不要复制 `node_modules`，在目标机器重新执行 `npm install`。
