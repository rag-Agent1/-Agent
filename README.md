# Android 拍照识图 + RAG 电商导购 Agent (PoC)

> **项目宪法**：本手册用于对齐 3 人小团队的核心目标与分工。技术细节（API、各模块手册）已拆分为独立文档。

---

## 0. 交付目标
- **输入**：Android 端拍照/选图 +（可选）用户文本问题。
- **输出**：Top-k 相似商品卡片 + 流式导购回答 + 知识引用。
- **核心体验**：P95 响应 < 500ms，低置信度时自动触发澄清问题。

---

## 1. 团队分工与责任边界

### 1.1 Android 工程 (Owner: 客户端)
- **职责**：UI 交互、图片采集上传、SSE 流式渲染、商品卡片组件。
- **文档**：`android/DEVELOPMENT_GUIDE.md` (待创建)

### 1.2 后端工程 (Owner: 编排)
- **职责**：接口编排、会话管理、数据转发、日志观测。
- **文档**：[api_spec.md](file:///d:/Trae%20CN%20Work/Rag-Agent/api_spec.md) (核心契约)

### 1.3 RAG/多模态工程 (Owner: 质量)
- **职责**：多模态检索、知识库构建、Prompt 策略、检索评测。
- **文档**：[RAG_DEVELOPMENT_GUIDE.md](file:///d:/Trae%20CN%20Work/Rag-Agent/rag/RAG_DEVELOPMENT_GUIDE.md) (模块手册)

---

## 2. 关键里程碑 (Week 1 - 3)

| 阶段 | 核心交付物 | 验收标准 |
| :--- | :--- | :--- |
| **Week 1** | 数据闭环 | 抓取李宁羽毛球鞋高清数据，完成向量入库。 |
| **Week 2** | 最小链路 | 打通 `上传 -> 检索 -> 生成 -> 手机端展示` 完整流程。 |
| **Week 3** | 策略优化 | 上线低置信度澄清策略，产出 50 条测试集评测指标。 |

---

## 3. 协作规范

### 3.1 Git 工作流
- **主分支**：`main` (仅用于发布正式版本)。
- **开发分支**：`develop` (团队合并分支)。
- **个人分支**：`feature/{name}/{task-description}`。
- **流程**：所有代码变更必须通过 **Pull Request** 合并至 `develop`，严禁直接推送主分支。

### 3.2 文档修改建议
- **API 变更**：必须先修改 [api_spec.md](file:///d:/Trae%20CN%20Work/Rag-Agent/api_spec.md) 并通知其他两方，方可开始代码实现。
- **任务追踪**：使用 GitHub Projects/Issues 追踪具体任务，README 不再记录静态 Checklist。

---

## 4. 快速启动
- RAG 模块：参考 [RAG_DEVELOPMENT_GUIDE.md](file:///d:/Trae%20CN%20Work/Rag-Agent/rag/RAG_DEVELOPMENT_GUIDE.md)。
- 后端服务：运行 `main.py` (待实现)。

---
*Last Updated: 2026-05-20*
