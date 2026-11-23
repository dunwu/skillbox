# Interview Question Importance Rubric

> The sole scoring basis for Mode 5 (Importance Rating). **Scoring without reading this file is forbidden**; never hand out star suggestions from memory or impression.
>
> Baseline: Java backend **senior technical expert / architect** at a top-tier company (Alibaba P8, ByteDance 2-2, Tencent T10, 15+ years).
> Non-Java-mainline topics (big data, AI, DevOps) are rated only on "**relevance importance to this role**", not on depth within their own specialty.

---

## 1. Five-Dimension Weighted Model

| Dimension | Name | Weight | What it measures | Scoring points |
| --- | --- | --- | --- | --- |
| **D1** | Interview heat (P8 bar) | **35%** | How often this knowledge point is actually probed in P8/2-2/T10 interviews at top-tier companies over the past 2 years | 5=almost always asked; 4=high frequency; 3=regularly asked; 2=occasionally asked; 1=rare/outdated. **This is the P8 bar, not the campus-recruiting bar**—items mandatory in campus hiring but no longer asked separately at P8 (e.g. `==` vs `equals`) get D1 1-2 |
| **D2** | Knowledge foundationality | **20%** | Whether it is an unavoidable underlying principle in the field, without which the layers above cannot be understood | 5=bedrock level (the whole block collapses without it); 3=important but skippable; 1=corner-case knowledge point |
| **D3** | Architecture-decision relevance | **25%** | Whether the knowledge point directly supports decisions to "pick a technology / size capacity / diagnose failures / weigh options" | **Key dimension added under the P8 bar**. 5=a wrong answer leads to a wrong architecture decision; 3=affects implementation quality; 1=pure knowledge recall, unrelated to decisions |
| **D4** | Practical value | **10%** | Whether it maps to real production scenarios, pitfalls, tuning, incident troubleshooting | 5=production-incident-grade experience; 3=useful in daily development; 1=pure theory |
| **D5** | Discrimination | **10%** | Whether it separates "memorized" from "truly understood", and how much follow-up room it offers | 5=can be probed 3+ layers deep and every layer filters candidates; 3=one layer of follow-up room; 1=answered in one sentence |

**Weighted score** = D1×0.35 + D2×0.20 + D3×0.25 + D4×0.10 + D5×0.10 (keep two decimals)

### Why D3 must be an independent dimension at 25%

Authoritative-site research conclusion: in P8-level interviews, **pure knowledge quizzing accounts for only about 25%**; the rest is project deep-dive ~30%, technical decisions ~25%, influence ~15%; in ByteDance backend round 2, system design is ~45% and deep principles ~35%.

The old four-dimension model (missing D3) skewed results toward "knowledge breadth", misaligned with what P8 actually probes—plenty of questions with "broad knowledge but no bearing on any decision" were overrated, while questions that "directly determine architecture selection" were underrated.

---

## 2. Star Bands

| Star | Weighted-score range | Semantics |
| --- | --- | --- |
| ⭐ | ≤ 1.55 | Marginal/outdated/pure recall; P8 interviews basically never ask |
| ⭐⭐ | 1.56 – 2.70 | Low-frequency or shallow: warm-up questions, command-detail questions |
| ⭐⭐⭐ | 2.71 – 3.50 | Commonly asked; must state the principle but not reach decision level |
| ⭐⭐⭐⭐ | 3.51 – 4.49 | High-frequency and strongly tied to architecture decisions; a P8 must be able to answer deeply |
| ⭐⭐⭐⭐⭐ | ≥ 4.50 **and R4 holds** | Must-ask + decision-level + deep follow-up possible; core asset of the question bank |

**Five stars is a scarce resource**: across the whole bank, five-star items should stay within 5%–10%. If a section exceeds 20% five-star, it is almost certainly inflation; re-check whether R4 really holds.

---

## 3. Decision Rules R1–R7

Rules **take precedence over** weighted-score bands. On conflict, adjudicate in the order R1/R4 (floor) > R2 (cap) > weighted-score band.

| No. | Rule | Effect |
| --- | --- | --- |
| **R1** | **Floor**: D1 ≥ 4 **and** D2 ≥ 4 | Star MUST NOT be lower than ⭐⭐⭐⭐ |
| **R2** | **Cap**: D1 ≤ 2 | Star MUST NOT be higher than ⭐⭐⭐, no matter how deep the content is |
| **R3** | **Discrimination compensation**: D5 ≥ 4 and the weighted score falls within ±0.15 of a band's upper bound | May move up one band |
| **R4** | **Decision relevance**: D3 ≥ 4 ⇒ star ≥ ⭐⭐⭐⭐; **and** D1 ≥ 4 ⇒ ⭐⭐⭐⭐⭐ | Necessary condition for five stars |
| **R5** | **Downgrade cap**: pure recall / warm-up / obsolete technology / pure command-and-config detail | Star ≤ ⭐⭐ |
| **R6** | **AI-topic timeliness basis**: D1 takes the **trend value, not the historical value**, judged by 2025-2026 heat | See §5 trichotomy |
| **R7** | **Non-mainline relevance basis**: for non-Java-mainline topics, assign D1/D3 by "depth of relevance to the Java backend architect role" | See §5 whitelist |

---

## 4. Derived Rules A / B / C (globally binding)

### Rule A: difficulty–star hard constraint (with double validation)

A question tagged 【困难】 **and** targeted at L3-L4 ⇒ star **floor ⭐⭐⭐⭐**; anything lower counts as "**gradient inversion**".

**Double validation MUST be stacked**: Rule A fires **and** the weighted score is ≥ 3.5 before any upgrade is allowed.

If Rule A fires but the weighted score is < 3.5, the **【困难】 label is inflated**; the correct handling is to **recommend recalibrating the difficulty label** (down to 【中等】), not to mechanically raise the star. Without this check, five-star inflation spreads across the whole bank.

Known instances: Shenandoah (weighted 2.00), CMF (2.55), AOT (2.35)—all should have the difficulty label lowered rather than the star raised.

### Rule A's symmetric ceiling: reverse inversion

Rule A only constrains "hard questions must not be low-star"; a ceiling is also required: **a question with a lower difficulty label or shallower content MUST NOT be rated higher than deeper questions in the same section**.

When reverse inversion is found, fix it by **lowering the shallow question**, not by raising the deep one.

Instance: in `并发（一）`, among the first 24 questions, the 【简单】/L2 "concurrency vs parallelism" and "blocking vs non-blocking" items outrank deeper 【中等】/L2-L3 items, and 【中等】 has 5 five-star items > 【困难】's 3 four-star items.

### Rule B: content depth must not inflate heat

Deep content counts **only** toward **D5**; it **MUST NOT** raise D1 / D3 judgments.

The reverse holds too—excellent content with low question-prompt value should still be downgraded, but **the rationale MUST state that "downgrading the star does not deny content quality"**.

Instance: "ArrayList 和 LinkedList 有什么区别" covers 64-byte cache lines, L1/L3/RAM access cycles, and a 10–40× quantified comparison—very high quality, yet the weighted score is only 2.35, so it still drops from ⭐⭐⭐⭐⭐ to ⭐⭐⭐.

### Rule C: cross-file consistency

When the same topic has conflicting stars across different source files, **it MUST be flagged**, giving both titles and current stars; the adjudication basis is "**the side with higher architecture-decision value wins**". If the two perspectives genuinely differ (e.g. one is principles, one is ops), keep the difference but declare the division of labor in the body text.

---

## 5. Dedicated Bases for Non-Mainline and AI Topics

### R7 Non-mainline topics

Docker / K8S / Hadoop / Hive / HBase / big data and other non-Java-mainline topics are rated only on "relevance importance to the Java backend architect role".

- Pure commands, pure YAML, pure syntax, pure deployment/O&M steps: D1 1-2, R5 caps at ⭐⭐
- Only questions inside the following "**Java intersection whitelist**" may get D3 4-5:

**Docker whitelist**: JVM containerization adaptation (`UseContainerSupport`, cgroup v1/v2 quota awareness, `MaxRAMPercentage` replacing `-Xmx`, container OOMKilled vs JVM OOM, off-heap memory headroom), Namespace/Cgroups isolation principles, image layering and UnionFS impact on build and autoscaling efficiency, container vs VM security boundary.

**K8S whitelist**: declarative API and Reconcile Loop (level-triggered vs edge-triggered, a general distributed design pattern), request/limit and the three QoS tiers matched to JVM memory, the probe trio and slow Java app startup / graceful online-offline, HPA/VPA/CA metric selection and scaling flapping, Informer and List-Watch, Service Mesh vs client-side governance trade-offs.

### R6 AI-topic trichotomy

D1 takes the **trend value, not the historical value**, judged by 2025-2026 heat:

1. **AI application engineering architecture** → D1/D3 4-5: Agent orchestration (ReAct / Plan-Execute), RAG system design, tool calling and MCP, context engineering, inference service governance, token cost optimization, evaluation systems, prompt injection defense
2. **Pure model internals** → for a Java architect, D1 only 2-3: attention mechanism math derivation, backpropagation, BPE implementation
3. **Pure framework API usage** → R5 caps at ⭐⭐

---

## 6. Actionable Criteria for Five-Star Inflation

Even if the topic is a P8 must-ask hot item such as volatile / synchronized, if **all three** of the following hold, ⭐⭐⭐⭐⭐ should drop to ⭐⭐⭐⭐:

1. The body is extremely short (on the order of tens of lines)
2. No 🏭 `实战场景` section
3. Content duplicates other questions in the same file

Instance: `并发（一）` "volatile vs synchronized" (52-line body), "synchronized 有什么作用" (37 lines).

---

## 7. Section-Level Rebaseline

When a section shows **any one** of the following, stop per-question hard-tuning and switch to the section-level rebaseline process:

| Trigger condition | Meaning |
| --- | --- |
| A star band is **entirely empty** | e.g. no ⭐⭐⭐⭐ anywhere in the whole Kafka bank |
| **≥50%** of questions fall in the same star band | floor effect or ceiling effect |
| Up/down direction is **one-way ≥80%** | the whole section's baseline is systematically shifted |

Terminology:
- **Floor effect**: ≥50% of a section's questions fall in the same low star band
- **Ceiling effect**: a section's top star is suppressed below the band its content depth warrants
- **Gradient inversion**: questions labeled deeper/harder get lower stars instead

Post-trigger flow: first output the section-level gap list and rebaseline plan → wait for user confirmation → then execute; **never batch-rewrite on your own**.

---

## 8. Handling Discipline for Metadata Defects

The "target level" field in several source files was batch-written wrong (known: all 31 distributed-theory questions marked L2, all three Dubbo files marked L2, the last 42 Spring questions all L1/L2), contradicting the actual content of 【困难】 + L3/L4.

**When evaluating such files, do not rely on the "target level" field; judge the L level yourself from actual content depth**, and report the metadata distortion ratio quantitatively in the systematic observations.

---

## 9. Execution Discipline and Boundary Principles

1. **Prove each question individually; batch formula recalculation is forbidden**. The user has explicitly rejected batch rating corrections. Every star suggestion must carry that question's own evidence (quote actual argumentation from the answer body as depth evidence); formulaic handling such as "whole section +1 star" is not allowed.
2. **Keep the adjustment rate within 15%** as the healthy range. Beyond that, either the rubric or the original bank baseline is systematically wrong—re-check before acting.
3. **The evaluation list has four mandatory elements**: current star → suggested star + triggered rule number + weighted score + 2-4 sentences of rationale.
4. **Downgrades need full justification too**, and must distinguish "low question-prompt value" from "poor content quality"—Rule B requires stating that the downgrade does not deny content quality.
5. **🔴 CHECKPOINT-D**: before applying star adjustments, first output the complete evaluation list and wait for user confirmation; when the user explicitly says 「直接调整/无需确认」, it may be skipped within this batch task. The same applies to section-level rebaseline.
6. **Cross-file consistency check (Rule C) must not be skipped**, otherwise same-topic star conflicts across source files lurk indefinitely.
7. **No rubric, no scoring**; if the rubric file is missing, stop the evaluation and tell the user—never output from memory.

---

## 10. Output Format

### Single-question evaluation entry

```
- 【难度】题目原文标题
  - 当前 ⭐⭐⭐ → 建议 ⭐⭐⭐⭐
  - 五维：D1=4 / D2=4 / D3=4 / D4=3 / D5=4，加权 3.85
  - 触发规则：R1（D1≥4 ∧ D2≥4）、R4（D3≥4）
  - 理由：<2-4 句，必须引用答案正文的实际论述作为深度证据，不得只复述标题>
```

### Section summary entry

```
| 源文件 | 深读题数 | 评级合理 | 建议上调 | 建议下调 | 调整率 | 星级分布（当前） |
```

Adjustment rate = (upgrades + downgrades) / questions read in depth. If "rating reasonable + adjustments" does not equal questions read in depth, the cause of the difference MUST be disclosed item by item in the basis notes—never silently swallowed.
