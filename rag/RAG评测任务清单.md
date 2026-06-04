# RAG 评测任务清单

## 1. 评测目标定义

- 明确评测层级：检索层、引用层、端到端回答层。
- 固化验收指标：`Top-1`、`Top-3`、`P95 latency`、`clarify rate`、`citation consistency`、`answer usefulness`。
- 给每个指标设阈值，并与项目现有 README 和 RAG 开发手册对齐。

## 2. 评测数据集建设

- 新建固定评测集文件，不再使用随机抽样。
- 样本字段至少包含：`test_id`、`image_path`、`query_text`、`gold_sku_id`、`gold_topk`、`should_clarify`、`expected_citations`、`difficulty`。
- 按场景分桶：同款识别、近似替代、低置信度澄清、知识问答。
- 补齐本地测试图片覆盖，解决当前图片样本不足的问题。

## 3. 检索评测改造

- 改造 `rag/scripts/evaluate_performance.py`，从固定数据集读取 case。
- 支持分别评测 `image_search`、`text_search`、`hybrid_search`。
- 增加分桶统计：按类别、难度、是否有图、是否含文本。
- 输出 `Top-1`、`Top-3`、`Recall@K`、`MRR`、`P50`、`P95`。

## 4. 澄清策略评测

- 为 `need_clarify` 建立金标样本。
- 统计 TP、FP、FN，避免“该问不问”或“乱问”。
- 把阈值 `T1/Tgap` 调参纳入评测回归。

## 5. 引用质量评测

- 检查返回的 `citations` 是否命中 gold SKU。
- 检查引用片段是否支持回答要点。
- 先做规则版校验：`sku_id` 一致、片段非空、来源可追踪。

## 6. 端到端回答评测

- 从后端流式接口或 orchestrator 跑完整链路。
- 评测最终回答的可用率、是否幻觉、是否与引用一致。
- 先用人工标注表，后续再接入 LLM-as-a-judge。

## 7. 报告与归档

- 评测结果输出成 `json`、`csv`、`markdown` 报告。
- 保存每次运行时间、代码版本、数据集版本、参数配置。
- 建立最近一次基线报告，补齐评测结果复现记录。

## 8. 回归与自动化

- 把评测脚本接入 CI，或至少接入本地回归命令。
- 数据更新、阈值调整、embedding 模型变更后自动跑回归。
- 区分“快速冒烟评测”和“完整基线评测”。

## 9. 工程收尾

- 去掉评测脚本中的硬编码路径，改为基于项目根目录或环境变量解析。
- 统一评测脚本入口和输出目录。
- 把评测使用说明补充进 `rag/RAG_DEVELOPMENT_GUIDE.md`。
