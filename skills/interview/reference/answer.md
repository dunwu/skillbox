# Interview Answer Writing Rules

This document is the execution standard for the interview skill sub-capability 「面试答案编写/优化」. Writing, rewriting, or reviewing any interview answer MUST follow these rules.

**Template structure and reference example**: see [template/answer.md](../template/answer.md). When these rules are ambiguous, the actual format of the reference example wins.

## Design Goals

One answer serves several reader profiles and prep horizons at once; each reader stops at their own level:

| Dimension | Tier | Reading scope |
| -------- | ------------------ | ---------------------------------------------------------------------- |
| Reader seniority | ≤3 years (target L2) | 💎 关键结论 + ⚡记忆卡片 + 📖 核心知识 |
|          | 3-5 years (target L3) | the above + 🔬 扩展知识 【L3】 layer + 🔀 发散问题 |
|          | 5-10 years (target L4) | everything, focused on the 【L4】 layer and 🏭 实战场景 |
|          | 10 years+ (target L4+) | everything, focused on cross-sectional comparison, version evolution, cross-domain links; can feed the answer back as material for posing interview questions |
| Prep time | Short sprint (1-2 weeks) | only 💎 关键结论 + ⚡记忆卡片; for 发散问题 read titles only |
|          | Medium term (1-2 months) | + 📖 核心知识 (able to narrate it fully) + short answers to 发散问题 |
|          | Long term (ongoing) | full close reading; export 记忆卡片 to Anki for spaced repetition |

## Template Structure

Module order is fixed and MUST NOT be reordered. See [template/answer.md](../template/answer.md) for the skeleton and reference example.

## Per-Module Writing Requirements

### 0. Question Header Metadata

- Format: a blockquote immediately after the question title, with fixed field order: `🎯 目标等级 ｜ ⏱ 建议用时 ｜ 🏷 标签`.
- A question's difficulty and importance follow its title, and **MUST stay consistent with the question bank index table (`questionBankDir`, configured in config.json)**. For the importance rating methodology (five-dimension weighted model, star bands, decision rules R1–R7, derived rules A/B/C) see [reference/importance-rubric.md](importance-rubric.md).
- Target grade reference: 简单 → L2, 中等 → L2-L3, 困难 → L3-L4.

### 1. 💎 关键结论

- The 30-second spoken script that opens the interview, **≤100 字**, pure spoken language, readable aloud as-is.
- Word-count convention: count natural characters in mixed Chinese/English — each Chinese character or punctuation mark counts as 1; a consecutive English word, number string, or code identifier counts as 1 as a whole (e.g. `binlog`, `8.0.17` each count as 1).
- Conclusion first, then a one-sentence reason; never list details.

### 2. ⚡记忆卡片

- Mind the heading spelling: there is **no space** between `⚡` and 「记忆卡片」.
- Three fixed fields, none optional: **口诀** (homophone / parallel phrasing / short sentence), **关键词** (separated by the full-width slash `／`), **链路** (causal or process arrows).
- The 链路 field for compare-and-classify questions (no causal chain): organize as "major category → members → each one's responsibility" (e.g. 「Server 层 4 日志 → InnoDB 层 redo/undo → 复制与崩溃恢复各司其职」); never invent causality just to fill arrows.
- This module is the data source for Anki cards; field names and structure MUST NOT change.

### 3. 📖 核心知识

- The L2 baseline full answer: cover the question's basic points, structured into bullets, 3-5 points maximum.
- Written but speakable; prefer tables and mermaid flowcharts for comparisons and process-type content.
- Cases and sample code always go into a **titled** `::: details 案例名称` fold to keep the main text clean.

### 4. 🔬 扩展知识

- Fixed structure: a `#### 🔬 扩展知识` heading outside + **untitled** `::: details` folded content.
- Tag content by sub-layer: 【L3】 = principle deep dive, quantitative analysis, source-code localization; 【L4】 = critical analysis, cross-sectional comparison, version evolution.
- 【L3】 before 【L4】; 1-3 items per layer, MUST go beyond 核心知识, no repetition.
- The in-container layout rules **apply only to this section and 🏭 实战场景**: the titled case containers in 📖 核心知识 and the ⚠️ 常见误区 container follow normal formatting and do not use the line-split form below.
- When expanded the reader is skimming, so never cram a whole argument into one list item written as a continuous run. Each item starts with a question alone on the first line `- 【L3】<问句>？` (that line ends without body text), then a blank line, then the body indented 2 spaces to align with the list item's text start column, split semantically into 1-3 short paragraphs with blank lines between them.
- Blank lines follow **paragraph boundaries**, not **list items**: structurally identical self-contained one-line bullets sit **directly adjacent with no blank line**, however long; add a blank line only when an item carries an indented body paragraph, or when the neighbors are paragraphs / `>` blockquotes / tables / code blocks.
  Counter-example (wrong):
  ```text
  - 消费取消时批量处理，减少 DB 交互。

  - 扫表兜底每 5 分钟扫描一次。
  ```
  Correct example (right):
  ```text
  - 消费取消时批量处理，减少 DB 交互。
  - 扫表兜底每 5 分钟扫描一次。
  ```
- One paragraph ≤ 3 sentences, one line ≤ 120 字; when exceeded, break the paragraph or switch to a table / code block: use a Markdown table when one group of objects has ≥ 3 comparable attributes, and a code block with line comments for instruction reordering / execution flow / state transitions; indent tables and code blocks 2 spaces (aligned with the owning list item's text start column) with one blank line before and after.
- Extension-reading links go at the end inside details as a `> 📚 延伸阅读：` blockquote.

### 5. 🏭 实战场景

- Enabled only for high-frequency hard questions; structure same as 扩展知识 (heading + untitled details).
- MUST contain quantitative information (scale, parameters, effect numbers); never fabricate production data — well-known industry cases or reasoned projections MUST be labeled as such.
- In-container layout follows the line-split form of Section 4: a single case splits into standalone lines per 「现象 → 排查 → 根因 → 修复」 (those four labels apply only to failure/incident cases; design-type cases use 「背景 → 方案 → 要点」), with quantitative data on its own line or in a small table, never buried in a hundreds-of-characters paragraph.
- Blank lines between case narrative paragraphs follow paragraph boundaries; if a paragraph is followed by several one-line points (e.g. the bullet list after 「分析要点：」), those points sit directly adjacent with no blank lines (blank-line rule of Section 4).

### 6. ⚠️ 常见误区

- Container structure same as 扩展知识 (heading outside + untitled `::: details`), but **does not** use the Q/A line-split form of Section 4.
- Each entry: `❌ "错误说法" → 纠正与原因`.
- Sources: high-frequency misconceptions, trap questions, past pitfalls (e.g. mis-ranking EXPLAIN `type` as `const > system`, 查询缓存 already removed in 8.0).

### 7. 🔀 发散问题

- **Does not** use `::: details` folds; content sits directly under the `#### 🔀 发散问题` heading.
- **Layout uses the Q/A line-split form**: `- **Q：<问题>？**` alone on one line, then a blank line, then `  → <简答>` indented 2 spaces to align with the question text start column; **question and answer MUST NOT share a line**.
- Each follow-up question gets a 2-3 sentence short answer and **MUST be self-answerable**.
- Follow-up directions: drill into details, related domains, upstream/downstream knowledge.
- When the target question already exists in this document, cite it as `见本文档「题目名」`; verify that the question actually exists before citing.

## Module Pruning Matrix

● required　◐ optional　— omitted

| Module | 简单⭐ | 简单⭐⭐⭐ | 中等⭐⭐+ | 困难⭐⭐⭐+ |
| ----------- | :----: | :--------: | :-------: | :---------: |
| 题头元信息 | ● | ● | ● | ● |
| 💎 关键结论 | ● | ● | ● | ● |
| ⚡记忆卡片 | ● | ● | ● | ● |
| 📖 核心知识 | ● | ● | ● | ● |
| 🔬 扩展知识 | — | ◐ | ● | ● |
| 🏭 实战场景 | — | — | ◐ | ● |
| ⚠️ 常见误区 | — | ◐ | ◐ | ● |
| 🔀 发散问题 | ◐ | ● | ● | ● |

Column semantics: the `+` in 「中等⭐⭐+」「困难⭐⭐⭐+」 means "and above" (i.e. importance ≥2 stars / ≥3 stars). When importance falls between two columns (e.g. 简单⭐⭐), **take the lower column** (conservative pruning, avoid over-modularizing); if you need an ◐ module that the column omits, the user must explicitly ask for it.

## Content Quality Red Lines

1. **Factual accuracy**: version-dependent conclusions MUST state the version (e.g. "MySQL 8.0 已移除查询缓存"); never write anything uncertain.
2. **Layered, no repetition**: 扩展知识 MUST NOT restate 核心知识; 关键结论 MUST NOT copy paragraphs from 核心知识.
3. **Format compliance**: zero Prettier warnings; fold containers only use `::: details` (vuepress-theme-hope syntax); `::: warning` and other containers MUST NOT host module content.
4. **Index consistency**: a question title's difficulty and importance MUST match the question bank index table (`questionBankDir`, configured in config.json); newly added questions MUST be registered in the index table.
5. **Effective follow-ups**: questions referenced by 发散问题 MUST really exist; short answers MUST be self-consistent and stand on their own.
6. **No information loss**: before rewriting, enumerate the existing answer's knowledge points; after rewriting, check them one by one; every omitted point MUST be filed into the matching module, or its omission reason (e.g. the fact is wrong, unrelated to the topic) stated in the delivery note.
7. **Layout not dense**: 🔬 扩展知识 and 🏭 实战场景 follow the in-container layout requirements of Sections 4/5 — question alone on the first line, body split into paragraphs, one paragraph ≤ 3 sentences, one line ≤ 120 字, multi-dimensional comparisons in tables, step sequences in code blocks; 🔀 发散问题 follows the Q/A line-split form. Never cram a whole argument into one list item written as a continuous run.

## Writing / Rewriting Workflow

1. Locate the question: confirm difficulty, importance, and owning topic document from the question bank index table (`questionBankDir`, the question bank root directory configured in config.json). When adding or adjusting importance, follow the scale in [reference/importance-rubric.md](importance-rubric.md).
2. Determine the enabled modules per the pruning matrix.
3. Verify the factual accuracy of existing content (especially version-related statements); fix errors before applying the template.
4. Organize content in module order, checking each module against its writing requirements.
5. Self-check when done: Prettier format, `::: details` container pairing, existence of 发散问题 references, index table consistency, no information loss (against the existing answer's knowledge-point list), and in-container layout of 🔬 扩展知识 and 🏭 实战场景 per Sections 4/5 (question alone on the first line, one paragraph ≤ 3 sentences, one line ≤ 120 字).

## Question Bank Index and Statistics Maintenance

Applies to question bank index updates, statistics recalculation, and audits of index/source consistency. Trigger words: 更新题库索引、题库统计、索引审计、统计重算、同步索引.

### Architecture Conventions

- **Source documents (single source of truth)**: each question looks like `### 【难度】题目标题⭐⭐` (难度 ∈ 简单/中等/困难, star rating 1-5 represents importance), section headings are `## xxx`.
- **Index table**: the summary list under `questionBankDir` (the question bank root directory configured in config.json); each section starts with `### 板块名` and contains a six-column table `| 分类 | 题目 | 难易度 | 重要度 | 掌握度 | 评估 |` (category / question / difficulty / importance / mastery / assessment).
- On conflict, always **fix the index to match the source documents**; but deletion-type actions MUST follow the CHECKPOINT-B protocol and MUST NOT run silently.

### Index Statistics Block Format (baseline: question bank index documents, e.g. `数据库面试.md`)

Each section contains three pieces before the question table, in order:

1. A `::: tip **题库**` container: lists the section's source document links.
2. A `::: note **统计**` block: total question count + difficulty distribution + importance distribution, fixed format:

   ```markdown
   ::: note **统计**：共 **N** 题

   - 难易度：| 简单 **a** 题 | 中等 **b** 题 | 困难 **c** 题 |
   - 重要度：| 一星 **n1** 题 | 二星 **n2** 题 | 三星 **n3** 题 | 四星 **n4** 题 | 五星 **n5** 题 |

   :::
   ```

3. mermaid difficulty pie chart: `pie title 板块名 - 难易度分布`, listing only non-zero entries.

At the top of the document, the overall statistics are a blockquote containing the total question count and each difficulty's count and percentage (1 decimal place).

### Tool: `script/bank_index.py`

Zero-dependency standard-library script (Python 3.7+), read-only, never modifies files. Three subcommands:

| Subcommand | Purpose | Key behavior |
| -------- | ---------- | -------------------------------------------------------------------------------------------------------- |
| `audit` | consistency audit | source documents are the source of truth, cross-check both ways; reports missing questions / orphan rows / question-prompt mismatches / difficulty mismatches / importance mismatches / duplicate questions / format violations; exit code 1 when differences exist |
| `stats` | statistics recalculation | aggregate question counts and difficulty/importance distributions per section, output global summary and shares |
| `render` | render statistics blocks | output `::: note` blocks and mermaid pie charts ready to paste into the index |

`audit` / `stats` support `--json` output for programmatic use. Usage:

```bash
python script/bank_index.py audit  --index <索引文件> --src <源文档目录或文件…>
python script/bank_index.py stats  --index <索引文件>
python script/bank_index.py render --index <索引文件>
```

### Workflow

1. **Audit**: run `audit`, get a difference report.
2. **Fix**: work through the report item by item —
   - Missing question: extract difficulty/importance from the source document's question header, add the index row (into the correct category).
   - Orphan row: verify whether the question was deleted from the source document; if deletion is confirmed, delete the index row in sync; if in doubt, list it to the user for a ruling.
   - Question prompt / difficulty / importance mismatch: fix the index to match the source documents; if the source document itself is wrong, fix the source first, then sync the index.
   - Format violation: fix per the `### 【难度】标题⭐` convention; trim extra columns in index rows down to 6.
   - Duplicate question: hand over to the "Question Deduplication and Merging" flow, obeying CHECKPOINT-B.
3. **Statistics recalculation**: after fixes, run `stats`; write results into the top overall statistics, each section's `::: note` block, and the mermaid pie chart (the `render` output can be used directly).
4. **Final verification**: re-run `audit`; it MUST be `NO FINDINGS` (exit code 0); also check that the sum of per-section statistics equals the global total.

### Execution Red Lines

1. **Single source of truth**: statistics and audits always follow the source documents; never fill numbers from memory or stale statistics.
2. **Consistent double-write**: additions/deletions/corrections MUST update both index and source documents; never change only one side.
3. **Controlled deletion**: before cleaning orphan rows or deleting duplicates, output a list for user confirmation (CHECKPOINT-B); never delete without confirmation.
4. **Self-consistent statistics**: before delivery verify three alignments — "sum of sections = global total", "note-block numbers = mermaid numbers = actual table row count".
5. **Tools first**: audits and statistics MUST run `bank_index.py`; no manual estimation; humans only execute the fix actions in the report.

## Question Deduplication and Merging

Applies to identifying, merging, deleting, and trimming duplicate questions in the question bank.

### Identifying Duplicates

Scan the index table and source files, group into three types:

| Type | Criterion | Example |
| ---------- | ---------------------------- | ---------------------------------------------------------------------------- |
| Exact duplicate | question text identical within the same source file | the RabbitMQ dead-letter question appears twice in the same file |
| Cross-topic overlap | different topics asking the same knowledge point | 「什么是 CAP 定理？」 vs 「什么是 CAP 理论？BASE 理论又是什么？」 |
| Subset relation | one question's knowledge points are part of another's | 「Zab 和 Paxos 有什么区别？」 is a subset of 「Paxos、Raft、ZAB 有什么区别与联系？」 |

Output: a grouped duplicate list (each group with questions, topic, difficulty, star rating, overlap analysis).

### Handling Decisions

For each group, pick the keeper by priority: **has images > higher star rating > more complete content > compliant structure**. Then choose one of three actions:

- **Delete outright**: content fully covered by the keeper, with no unique information points at all.
- **Merge then delete**: the doomed question has exclusive gems (unique angle, comparison table, 发散问题, quantitative data, pitfalls); merge them into the keeper's matching template modules (🔬 扩展知识 / ⚠️ 常见误区 / 🔀 发散问题) first, then delete.
- **Rephrase and keep**: the two questions each cover half of the knowledge points; rewrite the question boundaries so they complement each other (e.g. split 「什么是 CAP 理论？BASE 理论又是什么？」 out and rephrase it as a pure BASE question).

### Execution Red Lines

1. **Image red line**: before deleting, read the doomed question in full; if the question contains images (including mermaid and external-link images), the images MUST first be merged into the keeper; if they cannot be placed, keep the question and explain to the user.
2. **Consistent double-write**: the index table and source file MUST be deleted in sync; never delete only one side.
3. **Boundary protection**: when deleting a question block from a source file, check start/end boundaries line by line (from the header `### 【` to the next question/section), never damaging adjacent section headings (`##`/`###`).
4. **Reference repair**: after deletion, search the whole text for references to the deleted question (`本文档『题目名』`, `详见本文档`), replace them with references to the keeper; cross-document ones become `《xxx面试》『题目名』`; if no keeper can be referenced, remove that reference — never leave a dead link.
5. **Statistics sync**: recalculate and update the index's topic statistics (question count / difficulty / importance), charts, and overview statistics (run `bank_index.py stats` + `render`).

### Final Verification

- Source-file question count (`^### 【` count) matches the index row count of the matching topic (running `bank_index.py audit` MUST be NO FINDINGS).
- `::: details` container open/close tags are paired.
- Zero Prettier warnings.
- Full-text search shows no residue of deleted questions (titles, references).
