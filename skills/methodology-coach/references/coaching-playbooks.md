# Coaching Playbooks

> This file is the execution template for Mode ② "Guided Coaching". Each script defines: applicable scenario, entry question, turn-by-turn steps (coach action + user input + advance condition), completion criteria, and common failure modes.
>
> Universal rules: present only the current step each turn; when user input doesn't meet the advance condition, stay and fill the gap, don't skip; method details follow the corresponding section of [methodology.md](methodology.md).

## Script 1: PDCA Loop Card

**Fits**: continuous-improvement goals (cut failure rate, boost efficiency, quality governance) that need multiple spiral rounds. For single-event closeout, use Script 2.

**Entry question**: "What do you want to improve? What's the current baseline number?"

| Turn | Coach action | User input | Advance condition |
| --- | --- | --- | --- |
| Plan | Guide analyzing the current state, finding the main cause, setting measures; validate the goal with SMART | Baseline data, main cause, measures | A measurable goal + a measure list produced |
| Do | Confirm the execution plan; remind process supervision to keep actions undistorted | Execution records | Measures executed with process records |
| Check | Require comparing results against goals with data, listing each gap | Result data | Gaps vs. goals quantified; **no data, no advance** |
| Act | Guide separating what worked from what failed; carry leftovers into the next round | Effective/ineffective list | A standard document or a next-round list produced |

**Completion criteria**: Act produces either a "solidified standard" or a "next-round list"; otherwise the loop isn't closed.

**Common failure**: skipping the data-driven Check, collapsing the loop into "Plan-Do-Plan again"; on spotting this, return to the Check turn and backfill data.

## Script 2: AAR Four Questions

**Fits**: closing a single event or project (incident, release, campaign, interview). For ongoing loop improvement, use Script 1.

**Entry question**: "Which event are we reviewing? First send me the expected goal at the time and the actual result data."

| Turn | Coach action | User input | Advance condition |
| --- | --- | --- | --- |
| 1 Expect | Probe the original goal; fill fuzziness with SMART | Expected goal | Expectation is judgeable (has a standard or number) |
| 2 Actual | Accept only facts and data; strip adjectives and guesses | What actually happened | Facts uncontested; disputes first need evidence |
| 3 Diff | Guide cause attribution, issue not person; if facts unaligned, return to turn 2 | Reasons for the difference | Each reason backed by a fact |
| 4 Change | Require each conclusion to land on action + owner + deadline | Change list | Each change has all three elements |

**Completion criteria**: every change has an action, owner, and deadline; conclusions should feed PDCA to solidify into standards and roll into the next cycle.

**Common failure**: starting the review before facts align, degrading into blame arguments or a witch hunt — the coach calls a halt at the first sign of argument and returns to turn 2 to align data; stating only conclusions without owners and changes is the same as no review.

## Script 3: Learning Loop Plan

**Fits**: learning a new field, exam prep, systematic skill-building. Output is an executable weekly schedule.

**Entry question**: "What are you learning? What's the goal (exam / output / capability)? How many hours per week?"

| Turn | Coach action | User input | Advance condition |
| --- | --- | --- | --- |
| 0 Set goal | Rewrite the fuzzy wish with SMART; add "step one this week" | Goal, deadline, weekly hours | Goal verifiable, first step clear |
| 1 Study section | Design the single-session structure: active-recall preview → Feynman self-test per section → flashcards for facts | Study material list | Each link has a method, no overlap, no gap |
| 2 Practice section | Mix question types (interleaving); a mock exam every 2 weeks locates the weak sub-skill (deliberate + feedback) | Question bank / practice resources | Practice rhythm and error-attribution mechanism clear |
| 3 Schedule | Hand flashcards to spaced repetition, clear due daily; set a weekly review time | Available time slots | A weekly schedule produced |

**Completion criteria**: the weekly schedule contains four elements — goal, study-section structure, practice rhythm, review schedule.

**Key handoff**: understanding → Feynman, memory → spaced repetition, application → interleaving and deliberate practice — no overlap, no gap; active recall serves both preview (activating old knowledge) and review (retrieval practice).

**Common failure**: copying whole passages onto flashcards (should be atomic); interleaving before the foundation is built (block first, then interleave); input only, no output.

**Extension**: if the goal isn't passing an exam but curating a reusable knowledge asset (article / talk / course), add Zettelkasten and output-driven input, and switch to Script 6.

## Script 4: Decision Chain

**Fits**: complex project kickoff, multi-option comparison, major decisions. Output is the chosen option + risk list + execution handoff.

**Entry question**: "What are you deciding? What candidate options are there? What are the criteria?"

| Turn | Coach action | User input | Advance condition |
| --- | --- | --- | --- |
| 1 Define | Answer all seven 5W2H questions, Why first (worth doing?) | Topic and seven answers | No fuzzy item; Why holds |
| 2 Compare | Decision matrix: list options → set criteria → **weights fixed in advance** → score → sensitivity check | Options, criteria, weights | Weighted conclusion passes the sensitivity check |
| 3 Rehearse | Pre-mortem: assume it failed, independently exhaust causes → rank → countermeasures + monitoring signals | Failure-cause list | High-probability causes have countermeasures, signals, owners |
| 4 Handoff | Hand execution to the daily flow (quadrants → SMART → Pomodoro/time-block → AAR) | Execution arrangement | Risk list wired into the task queue, not left on paper |

**Completion criteria**: the chosen option has a weighted score and sensitivity-check record; every risk has a countermeasure, monitoring signal, and owner.

**Common failure**: adjusting weights afterward to flatter a preset conclusion — on discovery, declare the matrix void and redo it; swapping or merging the decision matrix with the pre-mortem (the former compares candidates, the latter only pre-rehearses an already-chosen plan).

## Script 5: Deep Output

**Fits**: high-cognition tasks needing a whole focus block (writing proposals / code / research), symptom "busy all day, nothing produced".

**Entry question**: "What do you need to produce? What time of day is your energy peak? What currently interrupts you?"

| Turn | Coach action | User input | Advance condition |
| --- | --- | --- | --- |
| 0 Locate energy | Guide logging a one-week energy curve (score every 2h), find the personal peak | Energy curve | Peak window identified |
| 1 Set deep blocks | Time blocking: place 1–3 ninety-minute deep blocks first, keep a 20%–30% buffer | This week's calendar | Each deep block has a clear task and duration |
| 2 Build the ritual | Deep work: fix the place, clear each interruption source, define the entry ritual | Ritual and interruption-clearance plan | Every interruption source has a handling |
| 3 Execute & shut down | Single-task in-block; log a breakpoint instead of switching when stuck; end with a 3-minute shutdown ritual | Execution record and breakpoints | Shutdown ritual yields breakpoint + next step |
| 4 Close | KISS review: continue / stop / start, landing on next-week verifiable actions | Three KISS lines | Each line has a verifiable action |

**Completion criteria**: at least one deep block run through + a breakpoint record + three KISS lines with actions.

**Common failure**: overpacking crashes the schedule (keep a buffer); scrolling the phone right after an interruption (the shutdown ritual backstops this); simplifying energy management to "sleep early, rise early" while ignoring individual peak differences.

## Script 6: Knowledge Curation

**Fits**: turning what you've read into a reusable knowledge asset and output (article / talk / course), symptom "read a lot but can't write anything".

**Entry question**: "What topic do you want to curate? What's the deliverable (article/talk/course)? By when?"

| Turn | Coach action | User input | Advance condition |
| --- | --- | --- | --- |
| 0 Fix topic & deliverable | Output-driven input: fix the deliverable first, then work backward to the gaps | Topic + deliverable + deadline | Deliverable has a real audience and acceptance standard |
| 1 Input | Syntopical reading / SQ3R: fix the question, filter books, build a position table | Book list and question list | A position-comparison table, not a pile of book notes |
| 2 Curate | Zettelkasten: one atomic note per section (own words + source) | Atomic notes | Notes are atomic and stand alone |
| 3 Retrieve | Active-recall self-test + fact-type content into spaced repetition | Self-test gaps and cards | Gaps re-studied |
| 4 Output | Assemble expression notes → publish/share → collect feedback → feed back into notes | Finished piece + feedback | Feedback returned to the notes |

**Completion criteria**: one deliverable produced, and feedback has flowed back into the notes.

**Common failure**: collect but never process (the second brain becomes a landfill — force output as the backstop); cards become excerpts (force your own words); three months with no expression note = the system is idling.

## Script 7: Habit Building

**Fits**: wanting to persist long-term but always quitting halfway (exercise / writing / study / review), symptom "know what to do but can't stick to it".

**Entry question**: "What habit do you want to build? Why isn't it sticking now — hard to start, hard to continue, or the reward is too far away?"

| Turn | Coach action | User input | Advance condition |
| --- | --- | --- | --- |
| 0 Fix identity | Atomic habits: fix "who I want to be", not "what I want to achieve" | Identity statement | Identity is specific and falsifiable |
| 1 Minimal action | Two-minute rule: design a starting version too small to fail | Minimal action | Action is too small to fail |
| 2 Bind & cue | Attach after an existing habit; design the environment so the cue is obvious | Attachment point + environment change | Cue visible in the environment |
| 3 Immediate reward | Tick off, track the streak; miss one don't make up, two weeks off restart | Reward mechanism | Has immediate satisfaction |
| 4 Breakthrough | Deliberate practice on the weakest sub-skill + a feedback source | Practice task + feedback source | Has a stable feedback source |
| 5 Solidify | Write stable, effective practices into a personal SOP; set a quarterly review node | SOP + review node | Has a quarterly review time |

**Completion criteria**: a full loop of identity + minimal action + binding + reward, plus a quarterly review set.

**Common failure**: goal too big ("lose 20 pounds") — shrink to the two-minute version; citing "21 days to build a habit" — state the median is about 66 days and promise no specific number; treating the 1% compound-interest story as a promise breeds frustration.

## Script 8: Root Cause

**Fits**: problems that recur, or get worse the more you fix them, symptom "treats symptoms, not the cause".

**Entry question**: "What problem keeps recurring? Do you have data? How did you handle it last time?"

| Turn | Coach action | User input | Advance condition |
| --- | --- | --- | --- |
| 0 Define | 5W2H to define the problem, Why first (worth solving?) | Seven answers | Problem quantifiable |
| 1 Decompose | MECE decomposition (by time / space / process / factor) | Decomposition structure | No overlap, no gap |
| 2 Root cause | 5 Whys down to the changeable mechanism layer; multiple causes → fishbone diagram | Root-cause chain | Root cause points to a system element, not "people careless" |
| 3 Structure | Systems thinking: draw causal loops, mark delays, find leverage points | Causal loop diagram | Supported by data or time series, not pure storytelling |
| 4 Countermeasure | Decision matrix to choose the option + pre-mortem to pre-install risks | Option + risk list | Risks have countermeasures, signals, owners |

**Completion criteria**: the root cause lands on a changeable system element, and the countermeasure has been compared and risk pre-installed.

**Common failure**: chasing a single line while ignoring multiple causes (switch to a fishbone); a system diagram with no data (backfill a time series); reaching "people are bad / careless" (keep drilling into process or incentive).
