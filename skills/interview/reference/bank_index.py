#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bank_index.py — 面试题库索引与统计维护工具

配套 interview skill「模式二：题库索引与统计维护」子能力，规约见 reference/answer.md。

题库架构约定：
- 源文档：每题形如 ``### 【难度】题目标题⭐⭐``，难度 ∈ 简单/中等/困难，
  星级 1-5 表重要度；章节标题为 ``## xxx``。
- 索引表：``docs/99.面试`` 下的汇总清单，每个板块以 ``### 板块名`` 起头，
  内含六列表格：| 分类 | 题目 | 难易度 | 重要度 | 掌握度 | 评估 |。

子命令：
- audit  一致性审计：源文档为唯一事实源，双向核对索引表。
         报告缺失题、孤儿行、题面/难度/重要度失配、格式违规、重复题。
         存在差异时退出码为 1，便于纳入校验流水线。
- stats  统计重算：按板块聚合题数、难易度分布、重要度分布与全局汇总。
- render 渲染统计块：输出可直接粘入索引文件的
         ``::: note **统计**`` 块与 mermaid 难易度饼图。

用法示例：
    python bank_index.py audit  --index docs/99.面试/JavaCore面试.md --src docs/01.Java/JavaCore/面试
    python bank_index.py stats  --index docs/99.面试/JavaCore面试.md --src docs/01.Java/JavaCore/面试
    python bank_index.py render --index docs/99.面试/JavaCore面试.md

设计约束：
- 零第三方依赖，仅使用标准库（兼容 Python 3.7+）。
- 只读：本工具永不修改任何文件，修改动作由 agent 依据报告执行。
- Windows 控制台兼容：强制 stdout 使用 UTF-8。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# 常量与正则
# ---------------------------------------------------------------------------

DIFFICULTIES: Tuple[str, ...] = ("简单", "中等", "困难")
STAR_LABELS: Tuple[str, ...] = ("一星", "二星", "三星", "四星", "五星")
STAR = "\u2b50"  # ⭐

# 源文档题目：### 【难度】标题⭐⭐
SOURCE_Q_RE = re.compile(r"^###\s+【(简单|中等|困难)】(?P<title>.+?)%s{1,5}\s*$" % STAR)
# 题目标题中的难度前缀与尾部星级（归一化用）
TITLE_META_RE = re.compile(r"^【(简单|中等|困难)】|%s{1,5}\s*$" % STAR)
# 索引表数据行：| 分类 | 题目 | 难易度 | 重要度 | 掌握度 | 评估 |（允许尾部多余列）
INDEX_ROW_RE = re.compile(
    r"^\|\s*(?P<category>[^|]*?)\s*\|\s*(?P<title>[^|]+?)\s*\|\s*(?P<difficulty>简单|中等|困难)\s*\|"
    r"\s*(?P<importance>%s+?)\s*\|\s*(?P<mastery>[^|]*?)\s*\|\s*(?P<assessment>[^|]*?)\s*\|" % STAR
)
SECTION_RE = re.compile(r"^###\s+(?P<name>.+?)\s*$")
HEADING2_RE = re.compile(r"^##\s+(?P<name>.+?)\s*$")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class SourceQuestion:
    """源文档中的一道题目。"""

    title: str
    difficulty: str
    importance: int
    file: Path
    line_no: int
    heading: str = ""  # 所属 ## 章节


@dataclass
class IndexRow:
    """索引表中的一行题目。"""

    section: str
    category: str
    title: str
    difficulty: str
    importance: int
    line_no: int


@dataclass
class Finding:
    """一条审计差异。"""

    kind: str  # missing / orphan / title_mismatch / diff_mismatch / imp_mismatch / dup / bad_format
    location: str
    detail: str


@dataclass
class SectionStats:
    """板块统计结果。"""

    name: str
    total: int = 0
    difficulty: Dict[str, int] = field(default_factory=dict)
    importance: Dict[int, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------


def normalize_title(title: str) -> str:
    """归一化题目标题用于匹配：去难度前缀、尾部星级、反引号与全部空白。

    有意保留全角/半角标点差异——标点不一致本身即需报告的失配项。
    """
    title = TITLE_META_RE.sub("", title)
    title = title.replace("`", "")
    return re.sub(r"\s+", "", title)


def count_stars(text: str) -> int:
    return text.count(STAR)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_code_free(lines: Sequence[str]) -> Iterable[Tuple[int, str]]:
    """逐行产出 (行号, 行内容)，跳过 ``` 围栏代码块内部。"""
    in_fence = False
    for i, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield i, line


def expand_sources(srcs: Sequence[str]) -> List[Path]:
    """把文件/目录参数展开为 .md 源文件列表（目录递归，按名称排序）。"""
    files: List[Path] = []
    for s in srcs:
        p = Path(s)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        elif p.is_file():
            files.append(p)
        else:
            raise FileNotFoundError("源路径不存在: %s" % p)
    return files


def parse_source_file(path: Path) -> Tuple[List[SourceQuestion], List[Finding]]:
    """解析单个源文档，返回题目列表与格式违规项。"""
    questions: List[SourceQuestion] = []
    findings: List[Finding] = []
    heading = ""
    for line_no, line in iter_code_free(read_text(path).splitlines()):
        m = HEADING2_RE.match(line)
        if m:
            heading = m.group("name")
            continue
        if line.startswith("### "):
            m = SOURCE_Q_RE.match(line)
            if m:
                questions.append(
                    SourceQuestion(
                        title=m.group("title").strip(),
                        difficulty=m.group(1),
                        importance=count_stars(line),
                        file=path,
                        line_no=line_no,
                        heading=heading,
                    )
                )
            elif count_stars(line) > 0:
                findings.append(
                    Finding(
                        "bad_format",
                        "%s:%d" % (path.name, line_no),
                        "题目标题不符合 ### 【难度】标题⭐ 规范: %s" % line.strip(),
                    )
                )
    return questions, findings


def parse_index(path: Path) -> Tuple[List[IndexRow], List[Finding]]:
    """解析索引文件，返回题目行列表与格式违规项（多余列等）。"""
    rows: List[IndexRow] = []
    findings: List[Finding] = []
    section = "(未分节)"
    for line_no, line in iter_code_free(read_text(path).splitlines()):
        m = SECTION_RE.match(line)
        if m:
            section = m.group("name")
            continue
        if not line.startswith("|"):
            continue
        m = INDEX_ROW_RE.match(line)
        if not m:
            continue
        row = IndexRow(
            section=section,
            category=m.group("category"),
            title=m.group("title"),
            difficulty=m.group("difficulty"),
            importance=count_stars(m.group("importance")),
            line_no=line_no,
        )
        rows.append(row)
        if line.rstrip().count("|") > 7:
            findings.append(
                Finding(
                    "bad_format",
                    "%s:%d" % (path.name, line_no),
                    "索引行存在多余列（应为 6 列）: %s" % row.title,
                )
            )
    return rows, findings


# ---------------------------------------------------------------------------
# 审计
# ---------------------------------------------------------------------------


def audit(index_path: Path, source_files: Sequence[Path]) -> List[Finding]:
    """以源文档为事实源，双向核对索引表。"""
    findings: List[Finding] = []

    source_questions: List[SourceQuestion] = []
    for f in source_files:
        qs, fmt = parse_source_file(f)
        source_questions.extend(qs)
        findings.extend(fmt)

    index_rows, idx_fmt = parse_index(index_path)
    findings.extend(idx_fmt)

    # 源文档内部重复题
    seen_src: Dict[str, SourceQuestion] = {}
    for q in source_questions:
        key = normalize_title(q.title)
        if key in seen_src:
            prev = seen_src[key]
            findings.append(
                Finding(
                    "dup",
                    "%s:%d" % (q.file.name, q.line_no),
                    "源文档重复题「%s」（首次出现 %s:%d）" % (q.title, prev.file.name, prev.line_no),
                )
            )
        else:
            seen_src[key] = q

    # 索引内部重复题
    seen_idx: Dict[str, IndexRow] = {}
    for r in index_rows:
        key = normalize_title(r.title)
        if key in seen_idx:
            findings.append(
                Finding(
                    "dup",
                    "%s:%d" % (index_path.name, r.line_no),
                    "索引重复行「%s」（首次出现第 %d 行）" % (r.title, seen_idx[key].line_no),
                )
            )
        else:
            seen_idx[key] = r

    # 源有索引无：缺失题；以及元数据失配
    for q in source_questions:
        key = normalize_title(q.title)
        row = seen_idx.get(key)
        if row is None:
            findings.append(
                Finding(
                    "missing",
                    "%s:%d" % (q.file.name, q.line_no),
                    "索引缺失题目「%s」（%s）" % (q.title, q.difficulty),
                )
            )
            continue
        if row.title.strip() != q.title:
            findings.append(
                Finding(
                    "title_mismatch",
                    "%s:%d" % (index_path.name, row.line_no),
                    "题面不一致：索引「%s」≠ 源「%s」" % (row.title, q.title),
                )
            )
        if row.difficulty != q.difficulty:
            findings.append(
                Finding(
                    "diff_mismatch",
                    "%s:%d" % (index_path.name, row.line_no),
                    "难度失配「%s」：索引 %s ≠ 源 %s" % (q.title, row.difficulty, q.difficulty),
                )
            )
        if row.importance != q.importance:
            findings.append(
                Finding(
                    "imp_mismatch",
                    "%s:%d" % (index_path.name, row.line_no),
                    "重要度失配「%s」：索引 %d 星 ≠ 源 %d 星" % (q.title, row.importance, q.importance),
                )
            )

    # 索引有源没有：孤儿行
    for r in index_rows:
        if normalize_title(r.title) not in seen_src:
            findings.append(
                Finding(
                    "orphan",
                    "%s:%d" % (index_path.name, r.line_no),
                    "索引孤儿行（源文档无此题）「%s」" % r.title,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------


def bump(counter: Dict, key, delta: int = 1) -> None:
    counter[key] = counter.get(key, 0) + delta


def compute_stats(index_path: Path) -> "OrderedDict[str, SectionStats]":
    """按索引板块聚合难易度与重要度分布（事实源为索引表本身）。"""
    rows, _ = parse_index(index_path)
    sections: "OrderedDict[str, SectionStats]" = OrderedDict()
    for r in rows:
        st = sections.get(r.section)
        if st is None:
            st = sections[r.section] = SectionStats(name=r.section)
        st.total += 1
        bump(st.difficulty, r.difficulty)
        bump(st.importance, r.importance)
    return sections


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------


def fmt_distribution(counter: Dict[str, int], labels: Sequence[str]) -> str:
    """按固定标签顺序输出非零分布项，如：简单 **54** 题 | 中等 **53** 题"""
    parts = ["%s **%d** 题" % (label, counter[label]) for label in labels if counter.get(label)]
    return " | ".join(parts)


def render_note_block(st: SectionStats) -> str:
    """渲染单个板块的 ::: note 统计块。"""
    imp = {STAR_LABELS[i - 1]: st.importance.get(i, 0) for i in range(1, 6)}
    return "\n".join(
        [
            "::: note **统计**：共 **%d** 题" % st.total,
            "",
            "- 难易度：| %s |" % fmt_distribution(st.difficulty, DIFFICULTIES),
            "- 重要度：| %s |" % fmt_distribution(imp, STAR_LABELS),
            "",
            ":::",
        ]
    )


def render_pie(st: SectionStats) -> str:
    """渲染单个板块的难易度 mermaid 饼图。"""
    lines = ["```mermaid", "pie title %s - 难易度分布" % st.name]
    for label in DIFFICULTIES:
        n = st.difficulty.get(label, 0)
        if n:
            lines.append('    "%s(%d)" : %d' % (label, n, n))
    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

KIND_LABELS = {
    "missing": "缺失题",
    "orphan": "孤儿行",
    "title_mismatch": "题面失配",
    "diff_mismatch": "难度失配",
    "imp_mismatch": "重要度失配",
    "dup": "重复题",
    "bad_format": "格式违规",
}


def print_findings(findings: Sequence[Finding], as_json: bool) -> None:
    if as_json:
        payload = [
            {"kind": f.kind, "kind_label": KIND_LABELS[f.kind], "location": f.location, "detail": f.detail}
            for f in findings
        ]
        print(json.dumps({"findings": payload, "total": len(findings)}, ensure_ascii=False, indent=2))
        return
    if not findings:
        print("NO FINDINGS：索引与源文档完全一致。")
        return
    by_kind: "OrderedDict[str, List[Finding]]" = OrderedDict()
    for f in findings:
        by_kind.setdefault(f.kind, []).append(f)
    for kind, items in by_kind.items():
        print("== %s (%d) ==" % (KIND_LABELS[kind], len(items)))
        for f in items:
            print("  [%s] %s" % (f.location, f.detail))
    print("\n共 %d 处差异。" % len(findings))


def print_stats(sections: "OrderedDict[str, SectionStats]", as_json: bool) -> None:
    total = sum(st.total for st in sections.values())
    merged_diff: Dict[str, int] = {}
    merged_imp: Dict[int, int] = {}
    for st in sections.values():
        for k, v in st.difficulty.items():
            bump(merged_diff, k, v)
        for k, v in st.importance.items():
            bump(merged_imp, k, v)

    if as_json:
        payload = {
            name: {
                "total": st.total,
                "difficulty": {k: st.difficulty[k] for k in DIFFICULTIES if st.difficulty.get(k)},
                "importance": {STAR_LABELS[i - 1]: st.importance[i] for i in sorted(st.importance)},
            }
            for name, st in sections.items()
        }
        payload["TOTAL"] = {
            "total": total,
            "difficulty": {k: merged_diff[k] for k in DIFFICULTIES if merged_diff.get(k)},
            "importance": {STAR_LABELS[i - 1]: merged_imp[i] for i in sorted(merged_imp)},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    for st in sections.values():
        print("== %s ==（共 %d 题）" % (st.name, st.total))
        print("  难易度：%s" % fmt_distribution(st.difficulty, DIFFICULTIES))
        imp = {STAR_LABELS[i - 1]: st.importance.get(i, 0) for i in range(1, 6)}
        print("  重要度：%s" % fmt_distribution(imp, STAR_LABELS))
    print("== 全局 ==（共 %d 题）" % total)
    print("  难易度：%s" % fmt_distribution(merged_diff, DIFFICULTIES))
    for d in DIFFICULTIES:
        if merged_diff.get(d):
            print("    %s占比：%.1f%%" % (d, merged_diff[d] * 100.0 / total))
    imp_all = {STAR_LABELS[i - 1]: merged_imp.get(i, 0) for i in range(1, 6)}
    print("  重要度：%s" % fmt_distribution(imp_all, STAR_LABELS))


def print_render(sections: "OrderedDict[str, SectionStats]") -> None:
    for st in sections.values():
        print("<!-- 板块：%s -->" % st.name)
        print(render_note_block(st))
        print()
        print(render_pie(st))
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bank_index.py",
        description="面试题库索引与统计维护工具（audit / stats / render）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser, need_src: bool) -> None:
        p.add_argument("--index", required=True, help="索引文件路径，如 docs/99.面试/JavaCore面试.md")
        if need_src:
            p.add_argument(
                "--src",
                required=True,
                nargs="+",
                help="源文档文件或目录（目录递归扫描 *.md），可多个",
            )
        p.add_argument("--json", action="store_true", help="以 JSON 输出（仅 audit/stats）")

    p_audit = sub.add_parser("audit", help="一致性审计：源文档 vs 索引表")
    add_common(p_audit, need_src=True)
    p_stats = sub.add_parser("stats", help="按索引板块重算统计分布")
    add_common(p_stats, need_src=False)
    p_render = sub.add_parser("render", help="渲染 ::: note 统计块与 mermaid 饼图")
    add_common(p_render, need_src=False)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    args = build_parser().parse_args(argv)
    index_path = Path(args.index)
    if not index_path.is_file():
        print("索引文件不存在: %s" % index_path, file=sys.stderr)
        return 2

    if args.command == "audit":
        findings = audit(index_path, expand_sources(args.src))
        print_findings(findings, args.json)
        return 1 if findings else 0
    if args.command == "stats":
        print_stats(compute_stats(index_path), args.json)
        return 0
    if args.command == "render":
        print_render(compute_stats(index_path))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
