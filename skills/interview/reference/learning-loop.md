# Mode 6 · Learning Loop Details

> Lock "quiz → verdict → learn/consolidate → key-point output → recall check → write the ledger entry" into one repeatable session.
>
> This document is the single specification for Mode 6; SKILL.md keeps only routing and a summary. It corresponds to §5.4 / §5.5 of the learning plan: the plan owns scheduling, this mode owns single-session execution.

## 1. Triggers and Inputs

**Trigger words**: 开始学习、学固、学习闭环、按要点讲、讲解这题、巩固一下、过一遍这题。

**Required inputs**:

| Input | Source | When missing |
| :--- | :--- | :--- |
| Target question / unit | user-specified, or the ledger's to-learn queue | ask the user which one; never start batch teaching on your own |
| Unit id and current status | ledger / question bank index | without a ledger, use the question prompt + index mastery |
| Source path | question bank source file (with the answer section) | follow "Failure Branch · Missing Source" |
| Whether it is currently "已测未学" or "未测" | ledger "最近结果" | treat as untested by default; test first |

## 2. Seven-Step Flow

```
0 Locate → 1 Test → 2 Verdict → 3 Disposition → 4 Key points → 5 Recall → 6 Ledger
```

| Step | Action | Duration | Output |
| :--- | :--- | ---: | :--- |
| 0 Locate | Read the index row + source section + ledger row; confirm the status and whether it was already tested | 1min | unit context |
| 1 Test | Blind answer, no reference material; if you cannot explain it, just say 「不会」 | 5–8min | raw answer |
| 2 Verdict | Compare against the source key points, mark ✓ hit / ✗ missed / ✗ wrong; decide 🔴/🟡/🔵/🟢 | 2–3min | verdict + gap list |
| 3 Disposition | Pick 学 / 补 / 固 per the "Graded Disposition Table" | — | disposition type |
| 4 Key points | Give 3 key points + 1 trap + source link per "Output Format" | 3min | study material |
| 5 Recall | User recalls for 30–60 seconds; if it fails, re-teach, at most 2 times | 2min | pass / leech |
| 6 Ledger | Write back question bank mastery + ledger D1/D3 + latest result | 1min | traceable record |

**Hard rule**: one session handles exactly **one unit**. Test and learn MUST happen in the same session; never split them across days.

## 3. Graded Disposition Table

| Verdict | Disposition | What to give | Duration | Ledger ceiling |
| :--- | :---: | :--- | ---: | :---: |
| 🔴 cannot explain / cannot remember | **学** | 3 key points + 1 trap → close read → recall → blank-page output → make cards | ~80min | 🔵 (valid only after a D7 recheck) |
| 🟡 partially hit | **补** | only the missing key points + 1 trap → recall → blank-page output | ~30min | 🔵 |
| 🔵 able to recall | **固** | 3 key points + 1 trap; no re-teaching | ~5min | 🔵 (no upgrade) |
| 🟢 mastered | **固** | one-line confirmation + 1 trap; **fail to rebut the trap = downgrade to 🟡** | ~3min | 🟢 granted only by D30 |
| blank | **学** | same as 🔴, but allow 2 minutes on the headings first to build a skeleton | ~80min | 🔵 |

> 🟢 is never granted by this mode. This mode records the status as 🔵 at most; 🟢 MUST wait for the ledger's D30 / D60 recheck.

## 4. Output Format (Single Template)

```markdown
### 块 N · 单元ID 题目（🔴 学 / 🟡 补 / 🔵 固 / 🟢 固）

1. **机制名**：一句话讲清是什么、为什么这样设计。
2. **机制名**：……
3. **机制名**：……

> 【**陷阱**】触发条件 → 后果 → 正确做法。

> 【**答案**】[文件名 · L行号](绝对路径) → 「题目原文」
```

Four constraints:

1. **Exactly 3 key points**, each starting with a bolded mechanism name. Fewer than 3 means it was not digested; more than 3 means it was not distilled.
2. **The trap MUST be actionable**: state under what condition it is triggered, what happens when it is, and the correct approach; never write only “注意 XX”.
3. **Answer links use absolute paths** so they open directly; inside the ledger keep relative paths.
4. **Line numbers drift**, so treat them as rough pointers only; the link points at the file, and searching by heading once inside is the most reliable.

## 5. Checkpoints

- 🔴 **CHECKPOINT-L1 (after testing → before key points)**: MUST output the verdict and the gap list before giving key points. Explaining while testing makes the test inaccurate. Example output: `判定：🟡｜命中 3/8，缺：AOP 代理、缓存职责`.
- 🔴 **CHECKPOINT-L2 (key points output → before ledger)**: MUST stop and wait for the user's recall; never write the ledger directly. No recall = loop not closed.
- 🔴 **CHECKPOINT-L3 (before ledger)**: confirm three things — which table and which row the mastery is written back to, the D1/D3 dates, and whether the status was wrongly upgraded to 🟢.

## 6. Failure Branches

| Trigger | First-line fix | Fallback if still failing |
| :--- | :--- | :--- |
| Source missing or the answer is extremely thin | mark 「待补答案」 and teach the key points from the knowledge-dimension file or construct them on the spot | tell the user plainly “本单元暂无原文，要点为现场提炼”, and queue the answer writing |
| User asks to “直接讲，不用测” | allow it | the status MUST NOT be upgraded; record the current status at most; state “未测，不进 D 梯” |
| User fails recall 2 times in a row | split into smaller units and re-teach (treat as leech) | stop the card, register it as leech, re-enter on another day |
| User only wants key points, no recall | allow it | do not record D1 and leave the status unchanged; state plainly “没有复述，这轮不算闭环” |
| The same unit was already tested today | skip step 1 and start from verdict/disposition | if the verdict information is insufficient, test again |

## 7. Anti-patterns (Do Not Do)

- ❌ Covering multiple units in one session, batching the 「测」 step, or pushing 「学」 to the next day
- ❌ Giving hints while testing, which inflates the verdict
- ❌ More than 3 key points, piling up definitions, no trap
- ❌ No source link, or a link pointing at the wrong file
- ❌ Writing the ledger before recall passes, or recording 🔵 as 🟢
- ❌ Omitting D1/D3 in the ledger entry, so the ledger cannot drive reviews
- ❌ Upgrading the status along the way when the user says “直接讲”

## 8. Integration with the Plan / Ledger

| Artifact of this mode | Written to |
| :--- | :--- |
| Mastery (🔴/🟡/🔵) | question bank index "掌握度" column |
| L1–L4 grade (if deep follow-up was done) | question bank index "评估" column, only when empty |
| First-study week / D1 / D3 / latest result | knowledge unit ledger |
| Answer to be filled | ledger status or a separate list |

**Every round of D1 / D3 / D7 / D15 / D30 reruns steps 1–6 of this mode** (test → verdict → supplement or consolidate → recall → ledger). Review is not “看一眼答案”; it is running the same loop again.
