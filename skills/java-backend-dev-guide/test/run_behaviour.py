#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""行为层实测求值：用已录制的模型输出跑 test/cases/rules/*.json 的确定性断言。

录制方式（`.en.md` 单一规范源）：让 executor **只读** SKILL.en.md 及其路由的
references/*.en.md（禁读中文原文），逐条回答 test-prompts.json 的 prompt，
汇总为 JSON：{ "<prompt id>": "<模型输出全文>" }。

用法：
    python test/run_behaviour.py                                  # 用仓库内默认 fixture
    python test/run_behaviour.py --outputs-file <json>            # 指定录制文件
    python test/run_behaviour.py --output test/results/behaviour-report.json

断言求值复用 test/lib/harness.py（与 run_rules.py 同一套语义）。llm_judge 需要
模型端点，本脚本记为 skip，不计入通过率。
"""
import argparse
import difflib
import io
import json
import os
import re
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR / "lib"))
from harness import eval_case  # noqa: E402

MATCH_THRESHOLD = 0.75


def norm(s):
    """去掉空白与中英文标点差异，让 prompt 比对不受排版影响。"""
    return re.sub(r"[\s。．，,、：:；;（）()]+", "", s)


def load_cases():
    cases = []
    for p in sorted((TEST_DIR / "cases" / "rules").glob("*.json")):
        cases.extend(json.loads(io.open(str(p), encoding="utf-8").read())["cases"])
    return cases


def match_cases(cases, prompt):
    target = norm(prompt)
    return [c for c in cases
            if difflib.SequenceMatcher(None, norm(c["prompt"]), target).ratio() >= MATCH_THRESHOLD]


DEFAULT_OUTPUTS = str(TEST_DIR / "results" / "behaviour-outputs-en.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs-file", default=DEFAULT_OUTPUTS)
    ap.add_argument("--output", default=None, help="把逐条结果写为 JSON")
    args = ap.parse_args()

    cases = load_cases()
    prompts = json.loads(io.open(str(TEST_DIR.parent / "test-prompts.json"), encoding="utf-8").read())
    recorded = json.loads(io.open(args.outputs_file, encoding="utf-8").read())

    kind_count = {}
    failures = []
    covered = set()
    records = []

    for pr in prompts:
        output = recorded.get(str(pr["id"]))
        if output is None:
            print(f"[{pr['id']}] 缺录制输出")
            continue
        matched = match_cases(cases, pr["prompt"])
        print(f"[{pr['id']}] 命中 {len(matched)} 条用例：{', '.join(c['id'] for c in matched) or '（无规则用例，仅定性判定）'}")
        for c in matched:
            covered.add(c["id"])
            res = eval_case(c, output)
            records.append(res)
            for a in res["assertions"]:
                kind_count[a["kind"]] = kind_count.get(a["kind"], 0) + 1
                if a["passed"] is False:
                    failures.append((pr["id"], c["id"], a["kind"], a["desc"]))
                    print(f"    [FAIL] {c['id']} {a['kind']} — {a['desc']}")

    total_cases = len(cases)
    kinds = ", ".join(f"{k}={v}" for k, v in sorted(kind_count.items()))
    print()
    print(f"规则用例 {total_cases} 条，本批行为层覆盖 {len(covered)} 条；未覆盖 {total_cases - len(covered)} 条")
    print(f"确定性断言求值 {sum(kind_count.values())} 条（{kinds}），FAIL {len(failures)} 条")
    for f in failures:
        print(f"  {f[0]} / {f[1]} / {f[2]}：{f[3]}")

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        io.open(args.output, "w", encoding="utf-8", newline="").write(json.dumps({
            "outputs_file": args.outputs_file,
            "cases_total": total_cases,
            "cases_covered": sorted(covered),
            "assertion_counts": kind_count,
            "failures": failures,
            "results": records,
        }, ensure_ascii=False, indent=2))
        print(f"报告已写入 {args.output}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
