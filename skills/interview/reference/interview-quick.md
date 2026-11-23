# Mode 1 · Quick Review Details

> This document is the quick-review sub-module of the interview skill's "Mode 1: Mock Interview": the question flow, the five-section output format, the reference example (user-finalized), and execution anti-patterns.
>
> For mode-selection rules and an overview of the two review styles, see the "Review Modes" section of SKILL.md; quick review compares against the question bank source-document answer as the blueprint and does not enter multi-turn follow-up probes.

## Quick Review: Posing Questions

1. **Scan and select**: read the question bank index and scope the review range (default: questions whose mastery ≠ 🟢; filter by section / star rating / mastery as the user specifies). Advance section by section in order, and do not enter the next section until the current one is fully reviewed; within a section, selection priority = higher importance first ＞ 🔴 before 🟡 ＞ same priority in index-table order.
2. **Batch posing**: 5 questions per batch by default (the user may set the batch size). For the question prompt format see "Question Presentation Format" in SKILL.md — the number stands on its own line, and the next line is `**【难度】【星级】题目原文**`; write importance in Chinese numerals and never use the ⭐ symbol. The presentation format is fixed (first review or repeat review alike, the question prompt carries no category or mastery field):

   > **题 1**
   >
   > **【困难】【四星】Java 8 的 Stream API 的核心操作有哪些？**

3. **Evaluate question by question**: take the existing answer for that question in the question bank source document as the blueprint (the 💎 关键结论 + 📖 核心知识 key-point list) and compare which key points the answer hits:
   - most key points hit → judge 【可复述】🔵 (pending consolidation)
   - partially hit → 🟡, list every missed key point
   - mostly missed → 🔴, attach a key-point crib for review
   - the candidate explicitly gives up or says they don't know → judge 🔴 directly and attach a key-point crib; do not probe
4. **Sync the index**: write the mastery column of the index table back question by question with 🔵 / 🟡 / 🔴; sync the same markers into the assessment column only when it is empty, and never overwrite rows that already carry an L1-L4 grade — a deep-review grade outranks a quick-review marker.
5. **Progress snapshot**: after each batch, print the section progress (X/Y questions reviewed, mastery changes in this batch); once a section is done, move to the next one.

> 🔴 **This mode only produces 🔵 / 🟡 / 🔴 and never writes 🟢.** Hitting the key points in a single review is only D7-level evidence; 🟢 mastery MUST be granted by the learning-plan ledger at the D30 / D60 recheck. Writing a review result straight to 🟢 = bypassing the double gate.
>
> ✓ / ✗ under "Analysis" mean only "hit / missed", not a mastery state; do not mix them up when writing back.

## Quick Review: Output Format

Every per-question result MUST follow the structure below and omit no part:

```markdown
## **题 N**

**【难度】【星级】题目原文**

**回答**：

> [候选人回答内容原文]

**评测**：🔵 / 🟡 / 🔴（只写这三个）

**分析**：

- ✓ **命中要点**：命中说明（每条一个要点）
- ✗ **遗漏要点**：逐条列出未命中内容
- ✗ **事实错误**：指出错误并纠正（无错误则省略本条）

**参考**：

> **💎 关键结论**：[源文档原文]
>
> **⚡ 记忆卡片**：
>
> - 口诀：[源文档原文]
> - 关键词：[源文档原文]
> - 链路：[源文档原文]
>
> **📖 核心知识**：
>
> - [提炼核心要点，逐条列出，每条约 1-2 行]
>
> 📎 原文：[文件名 · L行号](绝对路径) → 「题目原文」
```

**Where the reference answer comes from**:

- 💎 关键结论：quote the source-document text verbatim
- ⚡ 记忆卡片：quote the source-document text verbatim
- 📖 核心知识：distill from the source document's 📖 核心知识 module (not verbatim copying; MUST be condensed into a key-point list)

#### Reference Example (user-finalized)

> ### **题 4**
>
> **【困难】【五星】如何设计异地多活/容灾架构？**
>
> **回答**：
>
> > 无状态应用简单，多机房部署+负载均衡切流量。有状态应用以一个机房为主，MQ 实时同步到其他机房，故障时手动或 Raft 自动选主。
>
> **评测**：🔵
>
> **分析**：
>
> - ✓ **区分有状态/无状态**：无状态简单切流，有状态需数据同步
> - ✓ **覆盖同步机制**：MQ 实时同步
> - ✓ **覆盖故障切换**：手动或 Raft 自动选主
> - ✗ **遗漏要点**：容灾等级演进、RTO/RPO 指标、单元化设计、流量调度 GSLB、容量规划 N/(N-1)、切流演练
>
> **参考**：
>
> > **💎 关键结论**：容灾按等级演进：冷备 → 同城双活 → 异地多活，核心指标是 **RTO（多久恢复）与 RPO（丢多少数据）**。异地多活根本难点是跨城同步延迟，解法是**单元化**——按用户维度把流量和数据封闭在单元内闭环。没演练过的容灾等于没有容灾。
> >
> > **⚡ 记忆卡片**：
> >
> > - 口诀：单元闭环写，全局单点写，容量 N/(N-1)，演练才作数
> > - 关键词：RTO ／ RPO ／ 单元化 ／ GSLB ／ 切流演练
> > - 链路：冷备 → 同城双活 → 异地多活 → 单元化闭环 → 定期切流演练
> >
> > **📖 核心知识**：
> >
> > - **容灾等级**：冷备（小时级）→ 同城双活（分钟级，RPO≈0）→ 异地多活（秒级切换）
> > - **同城双活**：两机房<2ms 延迟，数据库同步/半同步复制，应用无状态双部署
> > - **异地多活难点**：跨城延迟 30ms+，解法是单元化（按 userId 取模封闭流量和数据）
> > - **流量调度**：GSLB + 网关层按路由规则导入对应单元
> > - **容量规划**：N 个单元需承担 N/(N-1) 倍容量（挂一个后其余能承接全量）
> > - **实践建议**：先同城双活，再异地冷备，最后核心链路单元化；定期切流演练

## Quick Review Anti-patterns (Do Not Do)

- ❌ The question prompt uses the ⭐ symbol instead of the Chinese star rating
- ❌ The question prompt uses the pipe-field form `| 分类 | 难度 | 星级 | 题目` instead of `**【难度】【星级】题目**`
- ❌ The question prompt shows a 「掌握度」 field
- ❌ Scoring from impression instead of against the question bank source-document answer blueprint
- ❌ Outputting questions from multiple sections at once, or exceeding the user-specified batch size
- ❌ Forgetting to write the mastery column back to the index after evaluating
- ❌ Review output deviating from the five-part structure "heading → answer → evaluation → analysis → reference", or omitting the reference
- ❌ Rewriting the 💎/⚡ modules in the reference answer instead of quoting the source document verbatim
