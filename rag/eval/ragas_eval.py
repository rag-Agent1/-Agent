"""RAGAS 评估流水线：四维指标计算"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # rag/eval/
_RAG_DIR = os.path.dirname(_SCRIPT_DIR)  # rag/
_PROJECT_DIR = os.path.dirname(_RAG_DIR)  # Agent/
sys.path.insert(0, _PROJECT_DIR)

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI

from rag.eval.config import ragas_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_dataset(path: str) -> list[dict]:
    """加载 JSONL 评测数据集"""
    cases = []
    if not os.path.exists(path):
        logger.warning("Dataset not found: %s", path)
        return cases
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def convert_to_ragas_format(cases: list[dict]) -> dict:
    """将评测用例转换为 RAGAS 需要的格式"""
    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for c in cases:
        questions.append(c.get("query_text", ""))
        answers.append(c.get("answer", ""))
        contexts.append(c.get("retrieved_contexts", []))
        ground_truths.append(c.get("gold_sku_id", ""))

    return {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }


def run_ragas_eval(dataset_path: str, output_dir: str) -> dict:
    """执行 RAGAS 评估"""
    # 1. 加载数据集
    cases = load_dataset(dataset_path)
    if not cases:
        logger.error("No cases loaded, aborting")
        return {"error": "empty dataset"}

    logger.info("Loaded %d evaluation cases", len(cases))

    # 2. 转换格式
    data = convert_to_ragas_format(cases)
    dataset = Dataset.from_dict(data)

    # 3. 配置 LLM-as-Judge
    eval_llm = ChatOpenAI(
        model=ragas_settings.eval_llm_model,
        api_key=ragas_settings.eval_llm_api_key,
        base_url=ragas_settings.eval_llm_base_url,
        temperature=0.1,
    )
    # 包装为 LangchainLLMWrapper
    evaluator_llm = LangchainLLMWrapper(eval_llm)

    # 4. 计算指标
    metrics = [faithfulness, answer_relevancy, context_recall, context_precision]
    result = evaluate(dataset, metrics=metrics, llm=evaluator_llm)

    # 5. 输出报告
    os.makedirs(output_dir, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    report = {
        "run_id": run_id,
        "dataset": dataset_path,
        "metrics": {
            "faithfulness": float(result["faithfulness"]),
            "answer_relevancy": float(result["answer_relevancy"]),
            "context_recall": float(result["context_recall"]),
            "context_precision": float(result["context_precision"]),
        },
        "num_cases": len(cases),
    }

    report_path = os.path.join(output_dir, f"ragas_report_{run_id}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 可读报告
    md_lines = [
        f"# RAGAS 评估报告 ({run_id})",
        "",
        f"| 指标 | 得分 | 说明 |",
        f"|------|------|------|",
        f"| **Faithfulness** | {report['metrics']['faithfulness']:.3f} | 答案忠于检索内容的程度 |",
        f"| **Answer Relevancy** | {report['metrics']['answer_relevancy']:.3f} | 答案相关性 |",
        f"| **Context Recall** | {report['metrics']['context_recall']:.3f} | 检索覆盖率 |",
        f"| **Context Precision** | {report['metrics']['context_precision']:.3f} | 排序质量 |",
        "",
        f"测试用例数: {report['num_cases']}",
    ]
    md_path = os.path.join(output_dir, f"ragas_report_{run_id}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    logger.info("Report saved to %s", report_path)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAGAS Evaluation Runner")
    parser.add_argument("--dataset", default=ragas_settings.eval_dataset)
    parser.add_argument("--output-dir", default=ragas_settings.output_dir)
    args = parser.parse_args()
    run_ragas_eval(args.dataset, args.output_dir)