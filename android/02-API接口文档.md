# 02 — API 接口文档

> 对 Android 队友的完整接口契约。按此文档对接，双方互不依赖。

---

## 通用约定

| 项目 | 规范 |
|------|------|
| 基础地址 | `http://<host>:8000/api/v1` |
| 数据格式 | 全部 JSON |
| 编码 | UTF-8 |
| 图片上传 | multipart/form-data |
| 鉴权 | 比赛阶段暂不鉴权 |
| 错误码 | 统一格式 `{ "code": "xxx", "message": "xxx" }` |

---

## 接口列表

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | POST | `/v1/upload/image` | 上传图片，返回 image_id |
| 2 | POST | `/v1/chat` | 发起会话，返回 stream_url |
| 3 | GET | `/v1/chat/stream` | SSE 流式读取回答 |
| 4 | POST | `/v1/chat/stop` | 中断正在生成的流 |
| 5 | GET | `/v1/health` | 健康检查 |

---

## 1. 上传图片

```
POST /api/v1/upload/image
Content-Type: multipart/form-data
```

### 请求

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 图片文件，最大 10MB，支持 jpg/png/webp |

### 成功响应 (200)

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "url": "https://oss.aliyuncs.com/agent/images/a1b2c3d4.jpg",
        "width": 1080,
        "height": 1920,
        "size": 2048576
    }
}
```

### 错误响应

```json
// 文件过大
{ "code": "FILE_TOO_LARGE", "message": "图片大小超过 10MB 限制" }

// 格式不支持
{ "code": "INVALID_FORMAT", "message": "仅支持 jpg/png/webp 格式" }

// 上传失败
{ "code": "UPLOAD_FAILED", "message": "图片上传失败，请重试" }
```

### Android 侧前置校验

```
① 用户选择图片 → 本地校验 ≤ 10MB
② 本地校验格式 jpg/png/webp
③ 调用本接口上传
④ 收到 image_id 后存入本地，用于后续 /v1/chat
```

---

## 2. 发起会话

```
POST /api/v1/chat
Content-Type: application/json
```

### 请求

```json
{
    "session_id": null,
    "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "text": "推荐类似的商品"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string\|null | 是 | null 创建新会话，非 null 续旧会话 |
| image_id | string | 是 | 上传接口返回的 image_id |
| text | string\|null | 否 | 用户附加文字，没有就传 null |

### 成功响应 (200)

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "session_id": "sess_abc123",
        "message_id": "msg_def456",
        "stream_url": "/api/v1/chat/stream?message_id=msg_def456"
    }
}
```

### Android 侧逻辑

```
用户拍照/选图 → 上传 → 得到 image_id
  ↓
调 /v1/chat → 得到 stream_url
  ↓
拼接完整 URL → 建立 EventSource 连接
```

---

## 3. 流式读取回答

```
GET /api/v1/chat/stream?message_id=msg_def456
```

### 响应格式 (SSE)

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### 事件序列

**① candidates — 候选商品（最先推送，让 Android 先渲染卡片）**

```
event: candidates
data: {
    "candidates": [
        {
            "sku_id": "SKU001",
            "score": 0.92,
            "title": "索尼 WH-1000XM5 无线降噪耳机",
            "image_url": "https://oss.aliyuncs.com/agent/sku/SKU001.jpg",
            "attrs": {
                "品牌": "索尼",
                "颜色": "黑色",
                "续航": "40小时"
            },
            "price": 2999
        },
        {
            "sku_id": "SKU002",
            "score": 0.87,
            "title": "Bose QC45 无线降噪耳机",
            "image_url": "https://oss.aliyuncs.com/agent/sku/SKU002.jpg",
            "attrs": {
                "品牌": "Bose",
                "颜色": "银色",
                "续航": "24小时"
            },
            "price": 2499
        },
        {
            "sku_id": "SKU003",
            "score": 0.75,
            "title": "华为 FreeBuds Pro 3",
            "image_url": "https://oss.aliyuncs.com/agent/sku/SKU003.jpg",
            "attrs": {
                "品牌": "华为",
                "颜色": "陶瓷白",
                "续航": "31小时"
            },
            "price": 1499
        }
    ]
}
```

**② delta_text — 流式文本（逐 chunk 推送）**

```
event: delta_text
data: {"text": "根据您拍摄的图片，我推荐"}

event: delta_text
data: {"text": "这款索尼 WH-1000XM5。"}

event: delta_text
data: {"text": "它的黑色外观和您的图片高度匹配，"}
```

**③ citations — 引用来源**

```
event: citations
data: {
    "citations": [
        {
            "sku_id": "SKU001",
            "chunk_id": "c_SKU001_01",
            "snippet": "WH-1000XM5 采用新一代HD降噪处理器QN1",
            "source": "索尼官方详情页"
        },
        {
            "sku_id": "SKU001",
            "chunk_id": "c_SKU001_02",
            "snippet": "续航最长40小时，支持快充3分钟听歌3小时",
            "source": "索尼官方详情页"
        }
    ]
}
```

**④ final — 结束标志**

```json
// 正常结束
event: final
data: {
    "need_clarify": false,
    "clarify_question": null,
    "usage": {
        "total_tokens": 342,
        "prompt_tokens": 210,
        "completion_tokens": 132
    }
}

// 需要澄清
event: final
data: {
    "need_clarify": true,
    "clarify_question": "您更看重降噪效果还是舒适度？",
    "usage": {
        "total_tokens": 156,
        "prompt_tokens": 120,
        "completion_tokens": 36
    }
}
```

### Android 侧处理逻辑

```
① 收到 candidates → 渲染商品卡片列表（3 张）
② 陆续收到 delta_text → 追加到气泡文本区
③ 收到 citations → 在文本下方展示引用来源（可展开）
④ 收到 final → 结束，正常显示或弹出澄清输入框
```

---

## 4. 中断生成

```
POST /api/v1/chat/stop
Content-Type: application/json
```

### 请求

```json
{
    "message_id": "msg_def456"
}
```

### 响应

```json
{
    "code": 0,
    "message": "success"
}
```

### 说明

- Android 用户点"停止生成"时调用
- 后端收到后，取消当前 message_id 对应的 LLM 流式任务
- SSE 连接关闭，不再推送后续事件

---

## 5. 健康检查

```
GET /api/v1/health
```

### 响应

```json
{
    "status": "ok",
    "timestamp": "2026-05-15T10:00:00Z",
    "services": {
        "redis": "connected",
        "qdrant": "connected",
        "oss": "connected"
    }
}
```

---

## 错误码总表

| code | 含义 | HTTP 状态码 |
|------|------|------------|
| 0 | 成功 | 200 |
| FILE_TOO_LARGE | 文件过大 | 413 |
| INVALID_FORMAT | 格式不支持 | 415 |
| UPLOAD_FAILED | 上传失败 | 500 |
| IMAGE_NOT_FOUND | image_id 无效 | 404 |
| SESSION_NOT_FOUND | session_id 无效 | 404 |
| MESSAGE_NOT_FOUND | message_id 无效 | 404 |
| RAG_SEARCH_FAILED | 检索失败 | 502 |
| LLM_TIMEOUT | 生成超时 | 504 |
| RATE_LIMITED | 请求太频繁 | 429 |
| INTERNAL_ERROR | 内部错误 | 500 |
