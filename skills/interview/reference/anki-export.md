# Mode 4 · Anki Card Generation Details

> This document is a submodule of the interview skill "Mode 4: Anki Export": triggers, execution flow, AnkiDroid import steps, CHECKPOINT-C, failure branches, execution counter-examples, and the Catppuccin Mocha palette spec.
>
> ⚠️ Path portability: this document and every script invocation use the `<skill根目录>` placeholder or relative paths, resolved and joined by the agent at runtime for the current environment; never hard-code any absolute path in the docs or command examples.

Export unmastered questions from the question bank as AnkiDroid-importable cards.

## Triggers

Activate this capability when the user expresses any of the following intents:

- "生成 Anki" / "导出 Anki" / "anki 卡片" / "做成 anki"
- "把没掌握的题导出"
- English: generate anki / export to anki

## Execution Flow

**Step 1: Determine the question scope**

1. Read `questionBankPath` from `config.json` to get the question-bank index file
2. Scan the index table and filter questions whose mastery is 🟡 (追问即卡) or 🔴 (讲不出主线); to also export 🔵 pending-fixation items, use `ANKI_MASTERY=pending,failed,degraded`
3. If the user names a specific section (e.g. "只要并发部分"), filter further

**Step 2: Match answers** (the extraction/matching logic below is built into `gen_anki.py`; do not run it by hand—it only explains and verifies script output)

1. Read the source files linked from the bank index (`docs/01.Java/JavaCore/面试/[JavaCore][面试]*.md`)
2. Extract each question's answer content by `###` heading
3. Match index questions to source answers by exact question title
4. Record match failures and report them to the user

**Step 3: Generate the CSV**

Run the script (resolve to an absolute path before execution; always use the `.csv` extension for output files):

```
python <skill根目录>/script/gen_anki.py <题库索引文件> <源文档目录> <输出路径.csv>
```

Example: `python <skill根目录>/script/gen_anki.py docs/99.面试/JavaCore面试.md docs/01.Java/JavaCore/面试 anki_cards.csv` (the index file comes from `config.json`'s `questionBankPath`/`questionBankDir`; join it into an accessible path for the actual environment before running). The script does the filtering, answer matching, and CSV generation; it defaults to mastery 🟡/🔴, overridable with the `ANKI_MASTERY` env var—the script only recognizes English keywords: `failed`=🔴, `degraded`=🟡 (the old name `warning` is still accepted), `pending`=🔵, `mastered`=🟢, `empty`=unmarked, combinable with commas (e.g. `pending,failed`); PowerShell: `$env:ANKI_MASTERY='failed'; python ...` (never pass emoji directly—filtering yields 0 rows).

Output format requirements:

| Requirement | Description |
| --- | --- |
| Delimiter | Tab `\t` (no clash with HTML content) |
| Encoding | UTF-8 with BOM (`utf-8-sig`) |
| Front | Category badge + difficulty color marker + question title |
| Back | Pure HTML (Catppuccin Mocha dark theme + left-aligned) |
| Code block | `<pre>` deep blue-gray background `#1e1e2e` + pale yellow text `#f9e2af` + left color bar + `<br>` preserving line breaks |
| Inline code | `<code>` background `#313244` + pink text `#f38ba8` |
| Table | Zebra stripes (alternating row `#262637`) + rounded corners + header background `#313244` |
| Blockquote | `>` and `::: tip` become colored callout boxes (left color bar + background color) |
| Bold text | Pale blue `#89b4fa` emphasis |
| Headings | Purple `#cba6f7` + left color bar |
| Outer container | `<div style="text-align:left;line-height:1.6">` forces left alignment + line height |
| Back module scope | Only 💎 关键结论, ⚡记忆卡片, 📖 核心知识 (including `::: details` cases) are kept; every other module is never exported |

**Step 4: Report results**

Report to the user:

- Number of cards generated
- List of match failures (if any)
- AnkiDroid import steps

## AnkiDroid Import Steps

1. 将 CSV 文件传到手机
2. AnkiDroid → 菜单 → 导入文件
3. 选择 CSV 文件
4. **分隔符选择 Tab**
5. 勾选 **允许 HTML**
6. 字段映射：第 1 列 → 正面，第 2 列 → 背面

## 🔴 Anki Checkpoint (STOP — you must stop and execute)

- 🔴 **CHECKPOINT-C 生成 CSV 前**：必须先输出「候选题目清单（分类/题面/难度/掌握度）+ 卡片总数 + 输出路径」，待用户确认后再运行脚本；用户明确说“直接导出/无需确认”时，本次任务内可跳过；未输出清单就生成文件 = 违反协议。清单样例行：`| 并发 | synchronized 和 ReentrantLock 的区别？ | 中等 | 🔴 |`，末行输出 `共 N 张 → <输出路径.csv>`。

## Anki Failure Branches (any trigger → handle per the table; never skip silently)

| Trigger condition | First-line fix | Fallback if still failing |
| --- | --- | --- |
| `python` command not found | Retry with `python3` or `py` | Tell the user Python 3.7+ is required; pause the export |
| config.json missing or questionBankPath empty | Handle as Mode 1 Step 0: ask the user for the index path and write it into config.json | If the user provides no path, pause the export; never guess or use a default path |
| Index has no 🟡/🔴 marked questions | Report that filtering returned empty and ask whether to loosen the conditions (e.g. name a section, difficulty, or add `ANKI_MASTERY=pending`) | No export without user confirmation; exporting the whole bank by default is forbidden |
| Filtering returns 0 rows after the `ANKI_MASTERY` override | Report no matches under that keyword and confirm whether to switch keywords or drop the override and rerun | Never silently produce an empty CSV; generate no file before user confirmation |
| A question's answer cannot be found in the source file | Record the failure and keep generating the remaining cards | Output the full failure list at the end; never fabricate answer content |
| Script error or CSV write failure | Verify the output directory exists and is writable, fix and rerun | Report the raw script error to the user and pause the export |
| Malformed index (no six-column table) | Handle as the Mode 1 fallback table: prompt the user to reconfigure the index file | If the conservative strategy fails, pause the export; never treat a non-index file as the question bank |

## Anki Execution Counter-Examples (don't)

- ❌ Generate the CSV without outputting the candidate question list (skipping CHECKPOINT-C)
- ❌ Use a `.txt` extension for the output file (always `.csv`; internal format unchanged: tab-separated + UTF-8 BOM)
- ❌ When mastery markers are missing, treat the whole bank as unmastered and export it without confirmation
- ❌ Keep content beyond the three modules on the card back, or hand-edit HTML/palette away from the Catppuccin Mocha spec
- ❌ Discard questions whose match failed without listing them in the report

## Palette (Catppuccin Mocha dark theme)

| Element | Background | Text color |
| --- | --- | --- |
| Code block | `#1e1e2e` | `#f9e2af` (pale yellow) |
| Inline code | `#313244` | `#f38ba8` (pink) |
| Table header | `#313244` | `#cdd6f4` |
| Table alternating row | `#262637` | `#cdd6f4` |
| Blockquote | `#1a1a2e` | `#a6e3a1` (pale green) |
| tip callout | `#1a2e1a` | `#a6e3a1` |
| Bold text | - | `#89b4fa` (pale blue) |
| Heading | - | `#cba6f7` (pale purple) |

Difficulty color markers: 简单 `#a6e3a1` (green) | 中等 `#f9e2af` (yellow) | 困难 `#f38ba8` (red)

## Reference Script

- [script/gen_anki.py](../script/gen_anki.py) — general Anki card generation script, Catppuccin Mocha dark theme, supports custom bank paths and output files
