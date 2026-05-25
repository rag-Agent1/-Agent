# Android 项目手册

> 基于 README.md + API 接口文档实现的 Android 拍照识图 + RAG 电商导购 Agent（PoC）

---

## 一、项目概述

**目标**：Android 端拍照/选图 → 上传 → 获取 top-k 候选商品 → 流式导购回答 + 引用展示

**技术栈**：
| 选型 | 说明 |
|------|------|
| Kotlin + Jetpack Compose | UI 框架 |
| Material 3 | Material Design 3 |
| Retrofit + OkHttp | HTTP / SSE 流式通信 |
| Coil | 异步图片加载 |
| GetContent + TakePicture | 相册选图 + 相机拍照 |
| DataStore | 本地会话持久化 |
| Coroutines + Flow | 异步 & 响应式状态管理 |

---

## 二、项目结构

```
android/
├── build.gradle.kts                    # 根构建脚本
├── settings.gradle.kts                 # 项目设置
├── gradle.properties                   # Gradle 属性
├── gradle/
│   ├── libs.versions.toml              # 版本目录（统一依赖版本）
│   └── wrapper/gradle-wrapper.properties
│
└── app/
    ├── build.gradle.kts                # 模块构建脚本
    ├── proguard-rules.pro              # 混淆规则
    └── src/main/
        ├── AndroidManifest.xml         # 清单（权限、FileProvider、Activity）
        ├── res/
        │   ├── values/strings.xml      # 字符串资源
        │   ├── values/themes.xml       # XML 主题
        │   ├── xml/file_paths.xml      # FileProvider 路径配置
        │   ├── drawable/               # 启动图标矢量图
        │   └── mipmap-anydpi-v26/      # 自适应启动图标
        └── java/com/agent/android/
            ├── AgentApp.kt             # Application 类
            ├── MainActivity.kt         # 单 Activity 入口（ChatScreen ↔ SettingsScreen）
            │
            ├── data/                   # 数据层
            │   ├── model/
            │   │   └── Models.kt       # 所有数据模型 + SSE 事件密封类
            │   ├── api/
            │   │   ├── ApiService.kt       # Retrofit 接口定义（5 个 API）
            │   │   ├── RetrofitClient.kt   # Retrofit 单例（支持动态切换地址）
            │   │   └── SseClient.kt        # OkHttp SSE 流式客户端（Flow 封装）
            │   ├── repository/
            │   │   └── ChatRepository.kt   # 仓库层（封装 API 调用）
            │   ├── ImageCompressor.kt      # 图片压缩（尺寸 + 质量）
            │   └── SessionManager.kt       # DataStore 会话持久化
            │
            ├── viewmodel/
            │   └── ChatViewModel.kt        # 核心状态管理 ViewModel
            │
            └── ui/                     # UI 层
                ├── theme/
                │   ├── Color.kt        # 颜色定义
                │   ├── Type.kt         # 排版
                │   └── Theme.kt        # Material3 主题（支持 Dynamic Color）
                ├── chat/
                │   ├── ChatScreen.kt   # 聊天主界面（含所有组件）
                │   └── SettingsScreen.kt # 设置页（切换后端地址）
                └── components/
                    └── ImagePicker.kt  # 拍照/相册选择对话框
```

---

## 三、环境要求

| 工具 | 版本 |
|------|------|
| Android Studio | Ladybug 2024.3+ |
| Gradle | 8.9 |
| AGP | 8.7.3 |
| Kotlin | 2.0.21 |
| Compose BOM | 2024.12.01 |
| Min SDK | 26（Android 8.0） |
| Target SDK | 36（Android 16） |

> Gradle 使用腾讯镜像加速下载：`https://mirrors.cloud.tencent.com/gradle/gradle-8.9-bin.zip`
>
> Maven 依赖使用阿里云镜像：`https://maven.aliyun.com/repository/public`

---

## 四、快速开始

### 4.1 打开项目

用 Android Studio 打开 `android/` 目录，等待 Gradle 同步完成。

### 4.2 运行

1. **模拟器**：默认连接 `http://10.0.2.2:8000/`（模拟器 → 宿主机 localhost）
2. **真机**：在设置页将地址改为电脑局域网 IP，例如 `http://192.168.1.100:8000/`

### 4.3 前置条件

确保后端服务已启动（详见后端部署文档），可通过健康检查接口验证：
```
GET http://<host>:8000/api/v1/health
```

---

## 五、后端 API 契约

基础地址：`http://<host>:8000/api/v1`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/upload/image` | 上传图片（multipart），返回 image_id |
| POST | `/chat` | 发起会话，返回 stream_url |
| GET | `/chat/stream` | SSE 流式读取回答 |
| POST | `/chat/stop` | 中断生成 |
| GET | `/health` | 健康检查 |

详细接口定义见 `02-API接口文档.md`。

---

## 六、SSE 事件流处理时序

```
Android                              Backend
  │                                      │
  │── POST /upload/image ──────────────→ │
  │← { image_id } ───────────────────── │
  │                                      │
  │── POST /chat (image_id + text) ────→ │
  │← { session_id, stream_url } ──────── │
  │                                      │
  │── GET /chat/stream ────────────────→ │
  │← SSE event: candidates              │  ← 立即渲染商品卡片
  │← SSE event: delta_text (N 次)       │  ← 逐段追加流式文本
  │← SSE event: citations               │  ← 显示引用来源
  │← SSE event: final                   │  ← 结束 / 澄清
```

### 客户端处理逻辑

```
① 收到 candidates → 渲染商品卡片 LazyRow（含相似度标签 + 骨架屏）
② 收到 delta_text → 逐段追加到当前助手消息气泡
③ 收到 citations → 在文本下方显示折叠引用面板
④ 收到 final →
   - need_clarify=false → 正常结束
   - need_clarify=true → 弹出澄清输入框 → 用户回答后重调 /v1/chat
```

---

## 七、核心数据模型

定义在 `data/model/Models.kt`：

| 模型 | 用途 |
|------|------|
| `UploadData` | 上传返回 `{image_id, url, width, height, size}` |
| `ChatRequest` | 发起会话请求体 |
| `ChatData` | 发起会话返回 `{session_id, message_id, stream_url}` |
| `Candidate` | 候选商品 `{sku_id, score, title, image_url, attrs, price}` |
| `Citation` | 引用 `{sku_id, chunk_id, snippet, source}` |
| `FinalEvent` | SSE final 事件 `{need_clarify, clarify_question}` |
| `SseEvent` | SSE 事件密封类（Candidates / DeltaText / Citations / Final / Error） |
| `ChatMessage` | UI 聊天消息模型 |
| `ConnectionStatus` | 连接状态枚举（CONNECTED / DISCONNECTED / CHECKING） |

---

## 八、功能清单

### Phase 1：项目基建
- [x] Gradle 配置 + 版本目录（统一依赖管理）
- [x] Material3 主题（支持 Dynamic Color / 深色模式）
- [x] 网络层（Retrofit + OkHttp + SSE 客户端）
- [x] 所有数据模型定义

### Phase 2：核心功能
- [x] 聊天界面（消息列表 + 输入框 + 发送/重试/停止）
- [x] 图片采集（相机拍照 + 相册选图 + 权限适配）
- [x] 图片压缩（最长边 ≤ 1920px，质量 ≤ 4MB）
- [x] 图片上传（进度条 + 失败重试按钮）
- [x] SSE 流式渲染（卡片 → 文本 → 引用 → 结束）
- [x] 候选商品卡片（横滑 + 相似度标签 + 骨架屏占位 + 详情 BottomSheet）
- [x] 引用展示（折叠/展开）

### Phase 3：体验增强
- [x] 停止生成（撤回对话、图片回待发送区、无弹窗）
- [x] 异常兜底（弱网/超时/后端报错/图片不合规，友好提示+重试按钮）
- [x] 自动健康检查（每 30 秒检测，绿/红指示灯）
- [x] 会话管理（新建 / 续对话 / 30 分钟超时提示）
- [x] 会话持久化（DataStore 存储 session_id）
- [x] 环境切换（设置页动态切换后端地址）

---

## 九、关键依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| androidx.compose:compose-bom | 2024.12.01 | Compose UI 框架 |
| com.squareup.retrofit2:retrofit | 2.11.0 | HTTP 请求 |
| com.squareup.okhttp3:okhttp-sse | 4.12.0 | SSE 流式解析 |
| io.coil-kt:coil-compose | 2.7.0 | 图片加载 |
| androidx.activity:activity-compose | 1.10.0 | GetContent 相册选图 + TakePicture 拍照 |
| androidx.datastore:datastore-preferences | 1.1.3 | 键值持久化 |

完整依赖清单见 `gradle/libs.versions.toml`。

---

## 十、常见问题

### Q: 编译报 `@mipmap/ic_launcher` 找不到？
确保 `res/mipmap-anydpi-v26/ic_launcher.xml` 存在且正确引用了 `drawable/ic_launcher_background` 和 `ic_launcher_foreground`。如果使用真机 API 26 以下（极少），需补充对应 mipmap 目录的 PNG。

### Q: 拍照闪退？
- 确认 `AndroidManifest.xml` 中 `FileProvider` 配置正确
- 确认 `res/xml/file_paths.xml` 存在

### Q: SSE 连接不上？
- 检查后端地址是否正确（模拟器用 `10.0.2.2`，真机用电脑局域网 IP）
- 检查后端是否已启动且健康检查通过
- 确认 `android:usesCleartextTraffic="true"` 已配置（开发阶段 HTTP 可行）

### Q: 图片上传失败？
- 确认图片压缩后 ≤ 4MB（接口限制 10MB，客户端留余量）
- 检查后端 `/upload/image` 接口是否正常返回

---

## 十一、与后端联调指南

1. **后端启动后**，先调 `/health` 确认连通
2. **上传图片** → 确认返回 `image_id`
3. **发起会话** → 确认返回 `stream_url`
4. **读取 SSE 流** → 检查事件顺序：`candidates` → `delta_text`* → `citations` → `final`
5. **中断测试** → 发送中调 `/stop`，确认流关闭
6. **澄清测试** → 让后端返回 `need_clarify=true`，确认客户端弹出澄清输入框

### 验收标准

- [ ] 拍照/选图 → 上传 → 看到候选商品卡片
- [ ] 流式文本逐段渲染，可中断
- [ ] 引用可展开查看
- [ ] 低置信度时触发澄清交互
- [ ] 弱网/超时/报错有友好提示
- [ ] 录屏不崩溃、不卡死

---

> 本文档与 `02-API接口文档.md`、`../README.md` 配合使用。
