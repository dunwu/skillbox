#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试框架核心：加载用例、执行断言、生成报告。"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any


def load_cases(rules_dir: Path) -> List[Dict[str, Any]]:
    """加载所有规则测试用例。"""
    cases = []
    for json_file in sorted(rules_dir.glob("rules_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for case in data.get("cases", []):
                case["_source_file"] = json_file.name
                cases.append(case)
    return cases


def eval_regex_present(pattern: str, output: str) -> bool:
    """评估 regex_present 断言。"""
    try:
        return bool(re.search(pattern, output, re.MULTILINE | re.DOTALL))
    except re.error as e:
        print(f"  [WARN] 正则表达式错误: {e}")
        return False


def eval_regex_absent(pattern: str, output: str) -> bool:
    """评估 regex_absent 断言。"""
    try:
        return not bool(re.search(pattern, output, re.MULTILINE | re.DOTALL))
    except re.error as e:
        print(f"  [WARN] 正则表达式错误: {e}")
        return False


def eval_local_judge(assertion: Dict[str, Any], output: str) -> bool:
    """
    本地规则引擎判断，替代 llm_judge。
    支持多种检查条件，全部通过才算 pass。
    """
    checks = assertion.get("checks", {})
    
    # must_contain: 必须包含任一关键词
    must_contain = checks.get("must_contain", [])
    if must_contain:
        if not any(kw in output for kw in must_contain):
            return False
    
    # must_contain_all: 必须包含全部关键词
    must_contain_all = checks.get("must_contain_all", [])
    if must_contain_all:
        if not all(kw in output for kw in must_contain_all):
            return False
    
    # must_not_contain: 不能包含任一关键词
    must_not_contain = checks.get("must_not_contain", [])
    if must_not_contain:
        if any(kw in output for kw in must_not_contain):
            return False
    
    # must_match: 必须匹配任一正则
    must_match = checks.get("must_match", [])
    if must_match:
        if not any(re.search(pat, output, re.MULTILINE | re.DOTALL) for pat in must_match):
            return False
    
    # must_not_match: 不能匹配任一正则
    must_not_match = checks.get("must_not_match", [])
    if must_not_match:
        if any(re.search(pat, output, re.MULTILINE | re.DOTALL) for pat in must_not_match):
            return False
    
    return True


def eval_assertion(assertion: Dict[str, Any], output: str) -> bool:
    """评估单个断言。"""
    kind = assertion.get("kind")
    if kind == "regex_present":
        return eval_regex_present(assertion["pattern"], output)
    elif kind == "regex_absent":
        return eval_regex_absent(assertion["pattern"], output)
    elif kind == "local_judge":
        return eval_local_judge(assertion, output)
    elif kind == "llm_judge":
        # llm_judge 需要模型端点，暂时跳过
        return None
    else:
        print(f"  [WARN] 未知断言类型: {kind}")
        return False


def eval_case(case: Dict[str, Any], output: str) -> Dict[str, Any]:
    """评估单个测试用例。"""
    results = []
    for assertion in case.get("assertions", []):
        result = eval_assertion(assertion, output)
        results.append({
            "kind": assertion.get("kind"),
            "pattern": assertion.get("pattern"),
            "criterion": assertion.get("criterion"),
            "passed": result,
            "desc": assertion.get("desc", ""),
        })
    
    # 统计通过情况
    total = len(results)
    passed = sum(1 for r in results if r["passed"] is True)
    failed = sum(1 for r in results if r["passed"] is False)
    skipped = sum(1 for r in results if r["passed"] is None)
    
    return {
        "case_id": case.get("id"),
        "subdomain": case.get("subdomain"),
        "rule_type": case.get("rule_type"),
        "source": case.get("source"),
        "rule": case.get("rule"),
        "prompt": case.get("prompt"),
        "assertions": results,
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "success_rate": (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0,
    }


def build_report(eval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """构建测试报告。"""
    total_cases = len(eval_results)
    total_assertions = sum(r["total"] for r in eval_results)
    total_passed = sum(r["passed"] for r in eval_results)
    total_failed = sum(r["failed"] for r in eval_results)
    total_skipped = sum(r["skipped"] for r in eval_results)
    
    # 按子领域统计
    by_subdomain = {}
    for r in eval_results:
        sd = r["subdomain"]
        if sd not in by_subdomain:
            by_subdomain[sd] = {"cases": 0, "passed": 0, "failed": 0, "skipped": 0}
        by_subdomain[sd]["cases"] += 1
        by_subdomain[sd]["passed"] += r["passed"]
        by_subdomain[sd]["failed"] += r["failed"]
        by_subdomain[sd]["skipped"] += r["skipped"]
    
    return {
        "summary": {
            "total_cases": total_cases,
            "total_assertions": total_assertions,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "success_rate": (total_passed / (total_assertions - total_skipped) * 100) if (total_assertions - total_skipped) > 0 else 0,
        },
        "by_subdomain": by_subdomain,
        "details": eval_results,
    }


def write_report(report: Dict[str, Any], output_file: Path):
    """写入测试报告。"""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 报告已写入: {output_file}")
