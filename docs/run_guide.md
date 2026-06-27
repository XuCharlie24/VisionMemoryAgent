# 运行步骤

1. 将 USB 摄像头连接到 RDK X3。
2. 确保 PC 和 RDK X3 在同一网络，RDK 当前地址为 `172.20.10.2`。
3. 在 PC 终端 SSH 连接 RDK：`ssh sunrise@172.20.10.2`。
4. 在 RDK 上启动后端：

```bash
cd ~/vision-memory-agent/backend
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

5. 在 Windows 本地启动前端：

```bat
cd /d E:\vision-memory-agent\frontend
npm install
npm run dev
```

6. 根据 Vite 输出地址打开浏览器，通常为 `http://localhost:5173`。
7. 检查页面摄像头画面是否在线，或访问 `http://172.20.10.2:8000/api/video/stream`。
8. 在摄像头前放入水杯、手机、书本等目标。
9. 观察视觉记忆列表、三维记忆空间和事件时间线是否更新。
10. 测试手势切换、锁定和详情查看；如果手势模型不可用，可先用键盘方向键、回车和空格测试交互。
