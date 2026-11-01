#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""java-backend-dev-guide 中英双语一致性门禁。

只收「机械可判定」的 6 项检查——语义保真度无法用正则判定，它由 test/BACKTRANSLATION_AUDIT.md
记录的盲译回译流程负责。本脚本的目的是防止已经修过的缺陷随后续编辑重新长回来。

检查项：
  1. fence        围栏块（代码块）内容中英逐字节一致；围栏内保留中文是既定约定
  2. shape        结构形状：标题层级数 / 围栏标记数 / 表格行数 / 总行数
  3. number       逐行数字量级一致（万/亿 与 K/M/billion 归一后比较）
  4. ref          跨文件 § 引用可解析 + 裸 § 引用不得在本文件与 SKILL.md 同号不同题
  5. identifier   纯 ASCII 的行内代码 token 必须在中英两侧同频出现（占位符对译豁免）
  6. term         术语黑名单：指定中文术语必须译成指定英文，禁止的译法出现即失败

用法：
    python test/bilingual_audit.py              # 全量检查，失败退出码 1
    python test/bilingual_audit.py --selftest   # 注入式负控：逐条确认每个检查都能抓到人造缺陷
    python test/bilingual_audit.py --quiet      # 只输出结论行
"""
import argparse
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
EXEMPT_PAIR = {
    "test/README.md",                    # 测试框架说明，不属译文镜像范围
    "test/BACKTRANSLATION_AUDIT.md",     # 审计方法论记录，仅中文
}

# 检查 6：中文术语 -> 允许出现的英文写法（正则）/ 禁止出现的写法
TERM_RULES = [
    ("阻断", r"Blocking|STOP", r"\bhalt(?:ing)?\b|\bartificial stop\b"),
    ("治理", r"Mitigation|Governance", r"\bhandling of\b"),
    ("线上", r"[Pp]roduction|going live", r"\bonline\b"),
    ("知识生成", r"[Kk]nowledge generation", r"\bcapture\b"),
    ("灰度", r"gray-?release|Gray-?[Rr]elease", r"\bcanary\b"),
    ("脱敏", r"[Mm]ask(ing|ed|ing rules)?", r"\bdesensitiz"),
    ("身份证", r"ID card", r"\bID numbers?\b"),
    ("内存使用率", r"memory usage ratio|usage percentage", r"\bmonitor memory usage\b"),
    ("建表", r"[Cc]reation|[Cc]reate", r"Table Design Standards"),
    ("鉴权", r"authorization|permission", r"\bauthentication\b"),
    ("错误码", r"[Ee]rror code", r"[Ee]xception code"),
]


def read(p):
    return io.open(p, encoding="utf-8").read()


def pairs(root):
    out = []
    for zh in sorted(root.rglob("*.md")):
        rel = zh.relative_to(root).as_posix()
        if rel.endswith(".en.md") or rel in EXEMPT_PAIR:
            continue
        en = zh.with_name(zh.stem + ".en.md")
        if en.exists():
            out.append((rel, zh, en))
    return out


def fence_blocks(text):
    blocks, cur, infence = [], None, False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            if not infence:
                cur, infence = [], True
            else:
                blocks.append("\n".join(cur))
                cur, infence = None, False
            continue
        if infence:
            cur.append(line)
    return blocks


def nonfence_lines(text):
    out, infence = [], False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            infence = not infence
            continue
        if not infence:
            out.append(line)
    return out


def headings(text):
    d = {}
    for line in text.split("\n"):
        m = re.match(r"^#{2,6}\s+([0-9]+(?:\.[0-9]+)*)[.\s]*(.*)$", line.strip())
        if m:
            d[m.group(1)] = m.group(2).strip()
    return d


def shape(text):
    ls = text.split("\n")
    return (
        sum(1 for l in ls if re.match(r"^#{2,6}\s", l)),
        sum(1 for l in ls if l.strip().startswith("```")),
        sum(1 for l in ls if re.match(r"^\s*\|", l)),
        len(ls),
    )


UNIT = {"万": 1e4, "亿": 1e8, "K": 1e3, "k": 1e3, "M": 1e6, "m": 1e6,
        "B": 1e9, "b": 1e9, "billion": 1e9, "million": 1e6, "thousand": 1e3}
NUMRE = re.compile(r"(\d+(?:\.\d+)?)\s*(万|亿|[KkBb](?![A-Za-z])|billion|million|thousand)?")
# 编程标识符形态：snake_case / camelCase / PascalCase / @注解 / 方法调用；
# 刻意排除 {占位符}（占位符按约定对译成英文）、纯大写缩写（中文「接口」译成 API 属正常）
IDRE = re.compile(
    r"(?:(?<![\w])@[A-Z][A-Za-z0-9]+(?![\w])"
    r"|(?<![\w])[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?![\w])"
    r"|(?<![\w])[a-z]+[A-Z][A-Za-z0-9]*(?![\w])"
    r"|(?<![\w])[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*(?![\w])"
    r"|(?<![\w][.?])(?<=[a-zA-Z0-9_])\.[a-z][A-Za-z0-9]+(?![\w]))")
CODE_SPAN = re.compile(r"`([^`]+)`")
STOP_TOKENS = {"true", "false", "null", "the", "and", "or", "if", "in", "no", "ok", "id", "a", "b", "c"}


def numbers(line):
    """归一化数量级：X 万 -> X*1e4，X 亿 -> X*1e8，100K -> 1e5，2.1 billion -> 2.1e9。
    带单位的数值只计入换算结果，避免 500 万 与 5 million 因裸数字 500/5 不等而误报。"""
    vals = set()
    for m in NUMRE.finditer(line):
        v = float(m.group(1))
        u = m.group(2) or ""
        vals.add(round(v * UNIT[u], 2) if u in UNIT else v)
    return vals


def code_tokens(text):
    """行内代码标识符集合（只看是否出现，不比次数——译文重组句子是常态）。"""
    found = set()
    for line in nonfence_lines(text):
        for s in CODE_SPAN.finditer(line):
            span = re.sub(r"\{[^{}]*\}", " ", s.group(1))
            for tok in IDRE.findall(span):
                tok = tok.strip(".@")
                if len(tok) > 2 and tok.lower() not in STOP_TOKENS:
                    found.add(tok if not tok.startswith(".") else tok[1:])
    return found


def check(psz, pen, zh_t, en_t, root):
    fails = []
    fz, fe = fence_blocks(zh_t), fence_blocks(en_t)
    if len(fz) != len(fe) or any(a != b for a, b in zip(fz, fe)):
        fails.append(("fence", f"围栏块不一致（zh {len(fz)} 块 / en {len(fe)} 块）"))

    sz, se = shape(zh_t), shape(en_t)
    if sz != se:
        fails.append(("shape", f"结构形状不一致 zh={sz} en={se}"))

    for i, (a, b) in enumerate(zip(nonfence_lines(zh_t), nonfence_lines(en_t)), 1):
        if numbers(a) != numbers(b):
            fails.append(("number", f"第 {i} 行数量级不一致：{sorted(numbers(a))} vs {sorted(numbers(b))}"))
            break

    cz, ce = code_tokens(zh_t), code_tokens(en_t)
    only = sorted({k for k in (cz - ce) | (ce - cz)})
    if only:
        fails.append(("identifier", f"行内代码标识符不对齐：{only[:8]}"))

    own_z, own_e = headings(zh_t), headings(en_t)
    sk_z = headings(read(root / "SKILL.md"))
    sk_e = headings(read(root / "SKILL.en.md"))
    bare = re.compile(r"[（(]\s*§\s*([0-9]+(?:\.[0-9]+)*)\s*[）)]")
    for f, own, sk in ((psz, own_z, sk_z), (pen, own_e, sk_e)):
        for n in bare.findall(zh_t if f == psz else en_t):
            if (n in own and n in sk and own[n].lower() != sk[n].lower()) or (n not in own and n not in sk):
                fails.append(("ref", f"裸 §{n} 就近解析会落到本文件同号章节（本文件={own.get(n, '-')!r} / SKILL={sk.get(n, '-')!r}）"))
                break

    for term, allow, forbid in TERM_RULES:
        zl, el = zh_t.split("\n"), en_t.split("\n")
        for i in range(min(len(zl), len(el))):
            if term in zl[i] and re.search(forbid, el[i]):
                fails.append(("term", f"第 {i + 1} 行「{term}」应译作 {allow}，实际：{el[i].strip()[:90]}"))
                break
    return fails


def run(root):
    res, n = [], 0
    for rel, zh, en in pairs(root):
        n += 1
        for code, msg in check(rel, Path(en).name, read(zh), read(en), root):
            res.append(f"FAIL[{code}] {rel}: {msg}")
    for zh in sorted(root.rglob("*.md")):
        rel = zh.relative_to(root).as_posix()
        if rel.endswith(".en.md") or rel in EXEMPT_PAIR:
            continue
        if not zh.with_name(zh.stem + ".en.md").exists():
            res.append(f"FAIL[orphan] {rel} 缺 .en.md 对端")
    for en in sorted(root.rglob("*.en.md")):
        if not en.with_name(en.stem + ".md").exists():
            res.append(f"FAIL[orphan] {rel if False else en.relative_to(root).as_posix()} 缺中文对端")
    return n, res


# ---------------- 注入式负控 ----------------

SNIPPETS = {
    "fence": ("## 1. X\n\n```java\n// 中文注释\nint a = 1;\n```\n", "## 1. X\n\n```java\n// chinese comment\nint a = 1;\n```\n"),
    "shape": ("## 1. A\n### 1.1 B\n", "## 1. A\n"),
    "number": ("单表超过 5 万行需分表\n", "Single table beyond 5,000 rows needs sharding\n"),
    "identifier": ("必须使用 `pageIndex` 分页\n", "Must use `pageIndexIndex` for paging\n"),
    "ref": ("## 1. A\n### 1.3 主动澄清\n\n见（§1.3）。\n", "## 1. A\n### 1.3 Questions\n\nSee (§1.3).\n"),
    "term": ("【推荐】热点 Key 治理\n", "[Recommended] Hot key handling of governance\n"),
}


def _wt(path, content):
    io.open(str(path), "w", encoding="utf-8", newline="").write(content)


def selftest(root):
    """人造缺陷必须被对应检查抓到；抓到才算仪器有效。"""
    tmp = root / "test" / "_selftest_tmp"
    (tmp / "references").mkdir(parents=True, exist_ok=True)
    skill_zh = tmp / "SKILL.md"
    skill_en = tmp / "SKILL.en.md"
    _wt(skill_zh, "## 1. A\n### 1.3 阶段阻断规则\n")
    _wt(skill_en, "## 1. A\n### 1.3 Stage Blocking Rules\n")
    bad = 0
    for code, (z, e) in SNIPPETS.items():
        if code == "ref":
            _wt(skill_zh, "## 1. A\n### 1.3 主动澄清的问题\n")
            _wt(skill_en, "## 1. A\n### 1.3 Questions To Clarify\n")
        _wt(tmp / "references" / "x.md", z)
        _wt(tmp / "references" / "x.en.md", e)
        hits = [m for m in run(tmp)[1] if m.split("[")[1].split("]")[0] == code]
        print(f"  negative-control {code:10s}: {'DETECTED' if hits else 'MISSED  <<< 仪器失效'}")
        if not hits:
            bad += 1
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="运行注入式负控")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--root", default=str(SKILL_ROOT))
    a = ap.parse_args()
    root = Path(a.root)

    if a.selftest:
        print("== bilingual_audit selftest ==")
        bad = selftest(root)
        print("selftest:", "PASS" if bad == 0 else f"FAIL（{bad} 项检查抓不到人造缺陷）")
        return 0 if bad == 0 else 1

    n, res = run(root)
    if not a.quiet:
        for r in res:
            print(r)
    print(f"bilingual_audit: 配对文件 {n} 组，失败 {len(res)} 项 ->", "PASS" if not res else "FAIL")
    return 0 if not res else 1


if __name__ == "__main__":
    sys.exit(main())
