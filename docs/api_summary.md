# API 接口汇总

## GET /api/health

- 请求方式：GET
- 路径：`/api/health`
- 功能：后端健康检查。
- 主要返回字段：`ok`、`project`、`device`、`camera`。

## GET /api/video/stream

- 请求方式：GET
- 路径：`/api/video/stream`
- 功能：返回 MJPEG 摄像头视频流。
- 主要返回字段：该接口为 `multipart/x-mixed-replace` 视频流，不返回 JSON。

## GET /api/video/snapshot

- 请求方式：GET
- 路径：`/api/video/snapshot`
- 功能：返回当前摄像头 JPEG 截图。
- 主要返回字段：该接口返回 JPEG 二进制图片。

## GET /api/video/gesture-frame

- 请求方式：GET
- 路径：`/api/video/gesture-frame`
- 功能：返回前端手势识别使用的低分辨率 JPEG 帧。
- 主要返回字段：该接口返回 JPEG 二进制图片。

## GET /api/status/current

- 请求方式：GET
- 路径：`/api/status/current`
- 功能：返回系统综合状态。
- 主要返回字段：`camera`、`vision_memory`、`vision_touch`。

## GET /api/memory/status

- 请求方式：GET
- 路径：`/api/memory/status`
- 功能：返回视觉记忆状态，兼容前端调用。
- 主要返回字段：`enabled`、`camera_status`、`object_count`、`memory_count`、`memories`、`latest_memory`、`latest_event`、`performance`、`version`。

## POST /api/memory/reset

- 请求方式：POST
- 路径：`/api/memory/reset`
- 功能：清空/重置视觉记忆。
- 主要返回字段：`ok`、`message`。

## GET /api/vision-memory/status

- 请求方式：GET
- 路径：`/api/vision-memory/status`
- 功能：返回视觉记忆状态。
- 主要返回字段：同 `/api/memory/status`。

## POST /api/vision-memory/reset

- 请求方式：POST
- 路径：`/api/vision-memory/reset`
- 功能：清空/重置视觉记忆。
- 主要返回字段：`ok`、`message`。

## GET /api/vision-touch/status

- 请求方式：GET
- 路径：`/api/vision-touch/status`
- 功能：返回手势/触控状态。
- 主要返回字段：`tracking`、`state`、`gesture`、`action`、`cursor`、`hand`、`metrics`、`interaction`。

## GET /api/vision-touch/config

- 请求方式：GET
- 路径：`/api/vision-touch/config`
- 功能：返回手势/触控配置。
- 主要返回字段：平滑、激活区域、冷却时间等配置项。

## POST /api/vision-touch/config

- 请求方式：POST
- 路径：`/api/vision-touch/config`
- 功能：更新手势/触控配置。
- 主要返回字段：更新后的配置或状态信息。
