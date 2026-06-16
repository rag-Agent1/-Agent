# RAG 检索评测报告

- Run ID: `20260616-103252`
- Dataset: `/home/user/projects/AgentProject/Agent/rag/eval/datasets/rag_eval_dataset.jsonl`（15 条）
- Top K: `5` | 耗时: `27.032s`

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
| 延迟 P50 / P95 | 474.3 / 893.0 ms |
| 澄清 TP/FP/FN | 2/2/1 |

### text 分场景指标

| 场景 | 用例数 | Top-1 | Top-3 | 澄清率 | 延迟P95(ms) |
|------|--------|-------|-------|--------|-------------|
| 同款识别 | 3 | 100.00% | 100.00% | 0.00% | 1004.6 |
| 近似替代 | 4 | 50.00% | 75.00% | 25.00% | 458.8 |
| 低置信澄清 | 3 | 0.00% | 0.00% | 66.67% | 563.0 |
| 知识问答 | 2 | 100.00% | 100.00% | 50.00% | 740.0 |

## 失败样例归因（Top 3）

### case-004 [近似替代]
- 输入: gold=`lining_003`
- 实际: top1=`lining_021`, top3=`['lining_021', 'lining_003', 'lining_018']`, status=`ok`
- 归因: [检索] BGE-M3 向量区分度不足或 query 与 gold 描述差异大
- 改进: 优化产品描述关键词 / 调 RRF 权重 / 加 reranker 精排

### case-005 [近似替代]
- 输入: gold=`lining_001`
- 实际: top1=`lining_021`, top3=`['lining_021', 'lining_016', 'lining_003']`, status=`ok`
- 归因: [检索] BGE-M3 向量区分度不足或 query 与 gold 描述差异大
- 改进: 优化产品描述关键词 / 调 RRF 权重 / 加 reranker 精排

### case-008 [低置信澄清]
- 输入: gold=`lining_001`
- 实际: top1=`lining_003`, top3=`['lining_003', 'lining_022', 'lining_016']`, status=`ok`
- 归因: [检索] BGE-M3 向量区分度不足或 query 与 gold 描述差异大
- 改进: 优化产品描述关键词 / 调 RRF 权重 / 加 reranker 精排
