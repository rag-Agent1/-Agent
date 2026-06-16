# RAG 检索评测报告

- Run ID: `20260616-102211`
- Dataset: `/home/user/projects/AgentProject/Agent/rag/eval/datasets/rag_eval_dataset.jsonl`（15 条）
- Top K: `5` | 耗时: `49.775s`

## text 模式

| 指标 | 值 |
|------|----|
| 用例数 / 可用数 | 15 / 12 |
| 可用率 | 80.00% |
| Top-1 命中率 | 58.33% |
| Top-3 命中率 | 66.67% |
| Recall@K | 63.89% |
| MRR | 0.7500 |
| 澄清率 | 33.33% |
| Citation 一致性 | 66.67% |
| 延迟 P50 / P95 | 500.6 / 2411.7 ms |
| 澄清 TP/FP/FN | 2/2/1 |

### text 分场景指标

| 场景 | 用例数 | Top-1 | Top-3 | 澄清率 | 延迟P95(ms) |
|------|--------|-------|-------|--------|-------------|
| 同款识别 | 3 | 100.00% | 100.00% | 0.00% | 3576.9 |
| 近似替代 | 4 | 50.00% | 75.00% | 25.00% | 740.5 |
| 低置信澄清 | 3 | 0.00% | 0.00% | 66.67% | 521.3 |
| 知识问答 | 2 | 100.00% | 100.00% | 50.00% | 535.0 |

## 失败样例归因（Top 3）

### case-013 [图片同款(占位)]
- 输入: gold=`lining_001`
- 实际: top1=`None`, top3=`[]`, status=`skipped`
- 归因: [数据/环境] missing query_text or embedding generation failed
- 改进: 补齐输入数据（图片/文本）或检查 embedding 加载

### case-014 [图片同款(占位)]
- 输入: gold=`lining_003`
- 实际: top1=`None`, top3=`[]`, status=`skipped`
- 归因: [数据/环境] missing query_text or embedding generation failed
- 改进: 补齐输入数据（图片/文本）或检查 embedding 加载

### case-015 [图片同款(占位)]
- 输入: gold=`lining_005`
- 实际: top1=`None`, top3=`[]`, status=`skipped`
- 归因: [数据/环境] missing query_text or embedding generation failed
- 改进: 补齐输入数据（图片/文本）或检查 embedding 加载
