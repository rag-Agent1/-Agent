# Android 模块开发手册

> 本文档面向三人 PoC 团队中的 Android 开发者，定义模块架构、核心规格、接口契约与交付标准。  
> 项目全局视图见 `../README.md`

---

## 目录

1. [模块职责与边界](#1-模块职责与边界)
2. [技术选型与工程结构](#2-技术选型与工程结构)
3. [架构与数据流](#3-架构与数据流)
4. [核心功能规格](#4-核心功能规格)
5. [前后端接口契约](#5-前后端接口契约)
6. [团队协作与联调流程](#6-团队协作与联调流程)
7. [验收标准](#7-验收标准)
8. [附录：关键决策记录](#8-附录关键决策记录)

---

## 1. 模块职责与边界

### 1.1 职责范围

Android 模块承担用户交互全链路，覆盖以下功能域：

| 功能域 | 具体职责 |
|--------|---------|
| 图片采集 | 拍照（系统相机 Intent）、相册选图（Photo Picker）、压缩 |
| 图片上传 | Multipart 上传、进度回调、失败重试 |
| 会话管理 | 消息列表管理、发送/重试/中断控制、会话生命周期 |
| 流式渲染 | SSE 事件解析、逐段文本积累与增量渲染、中断处理 |
| 候选卡片 | Top-k 商品卡片横滑展示、骨架屏过渡、点击交互 |
| 引用展示 | 折叠/展开引用面板、来源展示 |
| 澄清交互 | Clarify 消息展示、快捷回复 Chips、二次发送 |
| 异常兜底 | 弱网、超时、服务端错误、图片不合规等场景的分级处理 |

### 1.2 职责边界

| 属于 Android | 不属于 Android |
|-------------|---------------|
| 所有用户界面与交互 | 后端 API 实现 |
| 图片本地压缩与上传 | 图片向量检索与排序 |
| SSE 连接管理与事件解析 | LLM 提示词策略与生成 |
| 本地状态管理 | 候选商品的筛选与打分 |
| 异常感知与用户提示 | 服务端部署与运维 |

---

## 2. 技术选型与工程结构

### 2.1 技术选型

| 层面 | 选型 | 决策依据 |
|------|------|---------|
| 语言 | Kotlin | 业界标准，协程与 Flow 原生支持流式场景 |
| UI 框架 | Jetpack Compose | 声明式框架天然适配状态驱动的增量渲染 |
| 网络 | OkHttp 4.x + Retrofit 2.9 | SSE 通过 OkHttp EventSource 实现，无需额外依赖 |
| 图片加载 | Coil 2.x | Compose 原生集成（AsyncImage） |
| 序列化 | kotlinx.serialization | 编译期生成，类型安全 |
| 相机/相册 | CameraX + ActivityResult API | 官方推荐，生命周期安全 |
| 图片压缩 | Android Bitmap API | PoC 阶段无需引入三方压缩库 |
| 状态管理 | ViewModel + StateFlow | Android 官方架构组件 |
| 日志 | OkHttp LoggingInterceptor + Logcat | 联调阶段启用 BODY 级别，release 关闭 |

### 2.2 工程结构

```
app/src/main/java/com/ragshop/
├── config/
│   └── AppConfig.kt                  # 环境配置（单例，支持一键切换 baseUrl）
│
├── data/
│   ├── api/
│   │   ├── UploadApiService.kt       # 上传接口定义
│   │   ├── ChatApiService.kt         # 会话接口定义
│   │   ├── SseClient.kt              # SSE 连接封装，产出 Flow<StreamEvent>
│   │   └── dto/                      # 网络传输模型（与后端契约对齐）
│   │       ├── Candidate.kt
│   │       ├── Citation.kt
│   │       ├── StreamEvent.kt
│   │       ├── ChatRequest.kt
│   │       └── UploadResponse.kt
│   └── repository/
│       ├── UploadRepository.kt       # 上传流程封装
│       └── ChatRepository.kt         # 会话与流式通信封装
│
├── image/
│   └── ImageCompressor.kt            # 图片压缩工具
│
└── ui/
    ├── chat/
    │   ├── ChatScreen.kt             # 聊天主界面
    │   ├── ChatViewModel.kt          # 会话状态管理
    │   ├── ChatUiState.kt            # UI 状态定义
    │   ├── MessageState.kt           # 单条消息状态机
    │   └── components/               # 聊天子组件
    │       ├── MessageList.kt
    │       ├── MessageBubble.kt
    │       ├── InputBar.kt
    │       ├── ImagePickerSheet.kt
    │       └── ClarifyChips.kt
    ├── candidate/
    │   ├── CandidateCard.kt
    │   ├── CandidateCarousel.kt
    │   └── CandidateSkeleton.kt
    ├── citation/
    │   └── CitationPanel.kt
    └── common/
        ├── UploadProgressBar.kt
        ├── ErrorBanner.kt
        └── LoadingIndicator.kt
```

---

## 3. 架构与数据流

### 3.1 分层架构

采用标准 MVVM 三层架构：

```
┌──────────────────────────────────────────────────────┐
│                     UI Layer                          │
│  Compose 组件树，唯一职责是渲染 UiState 并上报事件     │
│  通过 collectAsStateWithLifecycle() 订阅状态变更       │
│  不持有业务逻辑，不直接调用网络层                      │
├──────────────────────────────────────────────────────┤
│                   ViewModel Layer                     │
│  持有 MutableStateFlow<UiState>，驱动 UI 刷新          │
│  协调多数据源：控制上传 → 创建会话 → 订阅 SSE 的时序   │
│  通过 viewModelScope 管理协程生命周期                  │
│  处理中断、重试等交互意图                             │
├──────────────────────────────────────────────────────┤
│                   Data Layer                          │
│  Repository 封装对 ApiService + SseClient 的调用       │
│  暴露 Flow<T> 供 ViewModel collect                   │
│  Repository 之间不互相依赖，由 ViewModel 编排          │
└──────────────────────────────────────────────────────┘
```

### 3.2 核心数据流

以下描述一次完整的"拍照 → 获取推荐"流程：

```
① 用户拍照/选图
   │
   ├── 图片压缩（尺寸 ≤ 1080px，文件 ≤ 512KB）
   │
   ├── 写入消息列表：MessageState.UserImage(status = Uploading)
   │
   ├── UploadRepository.upload(file) → POST /v1/upload/image
   │   └── 回调进度 → 更新 UserImage.uploadStatus
   │
   ├── ChatRepository.createChat(sessionId, imageId) → POST /v1/chat
   │   └── 返回 { stream_url }
   │
   ├── 写入消息列表：MessageState.Assistant(status = Streaming)
   │
   └── ChatRepository.streamChat(streamUrl) → GET /v1/chat/stream
       └── SSE 事件循环，每收到一个事件执行：
           ├── candidates  → 更新 Assistant.candidates（触发卡片渲染）
           ├── delta_text  → 追加到 Assistant.text（触发文字增量渲染）
           ├── citations   → 更新 Assistant.citations（触发引用面板）
           ├── clarify     → 标记 isClarify + 写入 clarifyQuestion
           └── final       → status = Completed（释放输入栏）
```

### 3.3 消息状态机

所有消息共享以下状态流转规则：

```
UserText:                       SENT（静态，无后续状态变化）

UserImage:  PENDING → UPLOADING(progress) ─→ SUCCESS
                  └──→ FAILED ─→ (重试回 UPLOADING)

Assistant:  STREAMING ─→ COMPLETED
                         ─→ INTERRUPTED（用户主动停止）
                         ─→ FAILED（网络异常，可重试）
```

### 3.4 SSE 事件处理时序约束

**重要**：SSE 各事件的到达顺序对 UI 体验有直接影响。客户端必须按以下预期处理：

```
事件到达顺序（按时间线）:
   candidates (0-1次) → delta_text (0-n次) → citations (0-1次) → final (1次)

或异常路径:
   clarify (1次) → final (1次)

UI 渲染顺序:
   ① candidates → 展示骨架屏（收到前）/ 候选卡片（收到后）
   ② delta_text → 逐段追加到文本区（打字机效果）
   ③ citations → 文本尾部附加引用面板（默认折叠）
   ④ final → 停止加载指示器，释放输入交互
   clarify → 渲染澄清气泡 + 快捷回复 Chips
```

**约束**：`candidates` 必须在首个 `delta_text` 之前或同时到达。如果后端无法保证此顺序，客户端应缓存首个 `delta_text` 直到 `candidates` 到达后再渲染。

---

## 4. 核心功能规格

### 4.1 图片采集与压缩

#### 4.1.1 采集

- 通过 FAB 触发 BottomSheet 提供"拍照"和"从相册选择"两个入口
- 拍照：调用系统相机 Intent，照片写入 App 私有缓存目录（FileProvider 对外暴露 URI）
- 相册：使用 `ActivityResultContracts.PickVisualMedia()`，无需声明 `READ_EXTERNAL_STORAGE`（Android 13+）
- 权限被拒时：Dialog 引导前往系统设置

#### 4.1.2 压缩

| 参数 | 阈值 |
|------|------|
| 最大宽边 | 1080px |
| 最大高边 | 1920px |
| 最大文件 | 512KB |
| 格式 | JPEG |

压缩策略：先按尺寸缩放，再按质量压缩。如果质量压缩至 50% 后仍超 512KB，则继续降级压缩到 10%，若仍超则报错提示用户选择较小图片。

### 4.2 图片上传

- 压缩完成后自动触发上传，无需用户二次确认
- 上传进度通过 OkHttp 自定义 RequestBody 回调，驱动 UserImage 消息内的进度条更新
- 上传失败：消息状态置为 UPLOAD_FAILED，显示错误原因 + 重试按钮
- 重试行为：重新执行上传全流程，不保留已失败的上传任务

### 4.3 聊天会话

#### 4.3.1 消息列表

- `LazyColumn` 按时间倒序展示，以消息 ID 作为 `key`，确保列表项稳定复用
- 用户消息右对齐（蓝色气泡），助手消息左对齐（灰色气泡）
- 新消息到达时自动滚动到底部；若用户已上滑浏览历史，则暂停自动滚动并显示"回到底部"按钮

#### 4.3.2 输入栏

| 状态 | 表现 |
|------|------|
| 空闲 | 输入框 + 拍照按钮 + 发送按钮 |
| 流式接收中 | 输入框禁用 + 显示停止按钮（红色方块图标） |
| 澄清等待中 | 输入框正常 + 输入框上方显示快捷回复 Chips |

#### 4.3.3 中断

- 用户点击停止 → 取消当前 SSE 订阅协程 → 消息状态置为 INTERRUPTED
- 已累积的文本和候选卡片保留
- 中断消息底部显示"重新生成"入口

### 4.4 流式文字渲染

- 每次 delta_text 到达，ViewModel 将增量追加至 `Assistant.text`，StateFlow 自动触发 UI 重组
- 重组不可阻塞主线程；文字量增长不应引入卡顿或 ANR
- 消息完整后才计算引用面板位置，避免引用随文字增长跳动

### 4.5 候选商品卡片

- 布局：横向滑动 LazyRow，卡片宽度约屏幕宽度 45%
- 每张卡片展示：商品图、标题、相似度百分比、价格
- 骨架屏：candidates 到达前显示 3 张灰色占位（带 shimmer 动画），到达后平滑替换为实际卡片
- 点击卡片：弹窗 / 跳转查看商品完整信息
- 空结果：骨架屏变为"未找到相似商品"状态

### 4.6 引用面板

- 默认折叠显示条目数（"引用 (n)"）
- 点击展开，显示每条引用的片段文字、来源、SKU ID
- 展开/收起带有平滑高度过渡动画
- 位置：锚定在助手消息文本下方

### 4.7 澄清交互

- clarify 事件到达时，将当前 Assistant 消息标记为澄清类型
- 对话中渲染为"提问气泡 + 快捷回复 Chips"
- 快捷回复内容由后端 `clarify.question` 语义决定，客户端不做硬编码
- 用户点击 Chip 后，该文本作为正常文本消息发送，触发新一轮处理

---

## 5. 前后端接口契约

> 本章是 Android 与后端联调的唯一依据。接口路径、字段名、类型如有变更，双方同步更新本文档。

### 5.1 上传图片

```
POST /v1/upload/image
Content-Type: multipart/form-data

请求体:
  file: Binary（JPEG/PNG，建议客户端压缩至 512KB 以内）

成功 200:
{
    "image_id": "string",
    "url": "string"
}

错误码:
  400 { "error": "image_too_large", "message": "string" }
  400 { "error": "invalid_format", "message": "string" }
  413 { "error": "payload_too_large", "message": "string" }
  500 { "error": "internal_error", "message": "string" }
```

### 5.2 创建会话

```
POST /v1/chat
Content-Type: application/json

请求体:
{
    "session_id": "string",    // 新会话传空字符串
    "text": "string",          // 用户附加文字，可为空
    "image_id": "string"       // 上传返回的 image_id
}

成功 200:
{
    "session_id": "string",
    "message_id": "string",
    "stream_url": "string"     // 相对路径，如 "/v1/chat/stream?message_id=xxx"
}
```

### 5.3 流式读取（SSE）

```
GET /v1/chat/stream?message_id={message_id}
Accept: text/event-stream
```

#### 事件定义

| event | data 字段 | 基数 | 说明 |
|-------|----------|------|------|
| candidates | `{ "candidates": [...] }` | 0..1 | 候选商品列表，详见 Candidate |
| delta_text | `{ "delta": "string" }` | 0..N | AI 回复文字增量片段 |
| citations | `{ "citations": [...] }` | 0..1 | 引用来源列表，详见 Citation |
| clarify | `{ "question": "string" }` | 0..1 | 低置信度时发送，替代 candidates 路径 |
| final | `{}` | 1 | 流结束标志 |

#### Candidate

```json
{
    "sku_id": "string",
    "score": 0.0-1.0,
    "title": "string",
    "image_url": "string",
    "attrs": { "string": "string" },
    "price": "number | null"
}
```

#### Citation

```json
{
    "sku_id": "string",
    "chunk_id": "string",
    "snippet": "string",
    "source": "string"
}
```

### 5.4 环境配置约定

- Android 客户端通过 `AppConfig.baseUrl` 控制所有请求的 base URL
- 模拟器访问宿主机：`http://10.0.2.2:{port}`
- 真机调试：替换为宿主机局域网 IP
- Android 9+ 明文 HTTP 需要在 `AndroidManifest.xml` 设置 `android:usesCleartextTraffic="true"`
- 联调阶段后端应绑定 `0.0.0.0` 而非 `127.0.0.1`

---

## 6. 团队协作与联调流程

### 6.1 开发节奏

```
Week 1:  UI 骨架 + 图片全链路（选图→压缩→上传→进度→失败重试）
Week 2:  SSE 接入 + 流式渲染 + 候选卡片 + 引用 + 中断
Week 3:  澄清交互 + 异常兜底全覆盖 + 联调 + 演示录屏
```

### 6.2 联调流程

```
① 后端确保接口可用，Android 用 curl 验证:
   curl -X POST http://{host}/v1/upload/image -F "file=@test.jpg"

② Android 端先用 MockWebServer 完成 UI 开发与自测

③ 关闭 Mock，指向真实后端开始联调

④ 问题沟通模板:
   问题: [接口] 返回 [错误]
   请求: [curl 命令或请求体]
   响应: [实际返回]
   期望: [文档约定的返回]
```

### 6.3 日志规范

排查问题时需提供以下信息：

- `message_id` 和 `session_id`（每条消息必须携带）
- SSE 原始事件日志（OkHttp LoggingInterceptor BODY 级别）
- 错误堆栈与设备信息（Android 版本、机型、网络类型）

---

## 7. 验收标准

### 7.1 Week 1 验收

| 检查项 | 操作 | 通过条件 |
|--------|------|---------|
| 拍照入口 | 点击 FAB → 拍照 | 系统相机正常启动，拍照后返回缩略图 |
| 相册入口 | 点击 FAB → 从相册选 | 可正常选择图片返回 |
| 权限拒绝 | 拒绝后重试 | Dialog 引导去设置 |
| 图片压缩 | 选 4K 图片 | 压缩后 ≤ 512KB |
| 上传进度 | 上传中观察 | 进度条 0→100% |
| 上传失败重试 | 断网后上传 | 显示错误 + 重试后成功 |
| 消息展示 | 发送图片 | 消息列表中右对齐显示图片 |

### 7.2 Week 2 验收

| 检查项 | 通过条件 |
|--------|---------|
| 骨架屏 | 上传后先显示骨架屏 |
| 候选卡片 | 骨架屏过渡到横滑卡片列表 |
| 流式文字 | 卡片下方文字逐段出现，无卡顿 |
| 停止生成 | 停止后文字停止增长，已收内容保留 |
| 引用面板 | 默认折叠，可展开查看引用 |
| 断线重连 | 3 次内自动恢复，超出显示失败状态 |

### 7.3 Week 3 验收

| 检查项 | 通过条件 |
|--------|---------|
| 澄清交互 | 低置信度触发澄清 + 快捷回复 |
| 网络异常 | 无网络时消息列表顶栏提示 |
| 超时兜底 | 连接超时显示友好提示 |
| 全链路联调 | 三个演示路径稳定复现 |
| 录屏稳定性 | 连续操作 10 次，无崩溃/ANR |

---

## 8. 附录：关键决策记录

### ADR-1：SSE 优于 WebSocket

**状态**：已采纳  
**理由**：后端 README 方案天然支持 SSE；OkHttp 提供 EventSource 原生实现，客户端无需引入额外依赖。SSE 的 unidirectional 模型已覆盖本场景所有需求（无需客户端向流内发送消息）。

### ADR-2：卡片优先于文字渲染

**状态**：已采纳  
**理由**：用户体验研究显示，用户在等待 AI 生成文字时先看到候选商品，能显著降低感知等待时间。此要求已约束后端事件发送顺序。

### ADR-3：不使用 DI 框架

**状态**：已采纳（PoC 阶段）  
**理由**：项目规模小，依赖层级浅，手动构造成本可控。若后续模块膨胀可引入 Hilt。

### ADR-4：压缩阈值 512KB

**状态**：已采纳，联调后可根据后端限制调整  
**理由**：平衡移动端上传速度与图片清晰度。后端限制通常在 5MB，客户端压缩至 512KB 留有足够余量。
