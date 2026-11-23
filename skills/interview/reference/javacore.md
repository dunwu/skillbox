# Java Core Interview Knowledge Dimensions

## Question Bank Index

Before the interview, read the question bank index file and confirm which questions have already been assessed (questions whose grade and assessment columns are not empty are not asked again):

**Path source**: read the `questionBankPath` field in `config.json`.

If `config.json` is missing or the path is invalid, follow the "Step 0: First-Time Setup + Background Confirmation" flow in [interview-deep.md](interview-deep.md).

---

## Grading Rubric

**Scoring hard rule: compare item by item against the "MUST hit" content. Missing any key item → drop one grade.**
**Design principle of "MUST hit": memorized interview-experience answers cannot hit it; real production scars or source-code reading experience are required.**

### 1. Type System and Memory Model

| Grade | Grading criteria | MUST hit |
| ---- | -------- | -------- |
| L1 Fail | Mixes `==` vs `equals` with no awareness | — |
| L2 Marginal pass | Knows `Integer.valueOf` caches `-128~127` | Can state the behavioral difference of `==` at the cache boundary values |
| L3 Pass | Can quantitatively analyze the memory impact | **MUST hit at least 2 items:** ① the `-XX:AutoBoxCacheMax` flag name and a clear explanation of how it takes effect (affects `Integer` only, not the default upper bound of `Long`) ② how to estimate the object allocation rate of Long boxing under high concurrency (QPS × bytes per boxing × object header overhead) ③ the in-heap data structure of the wrapper cache (`Integer.cache[]`, allocated at class initialization) |
| L4 Excellent | Can critically analyze the design cost of Java's type system | **MUST hit at least 1 item:** ① the core goals of Project Valhalla Value Types (eliminate object headers + flat memory layout + eliminate Identity semantics) ② the escape-analysis gap vs the stack allocation strategies of Go/Rust ③ the initialization constraints of autoboxing under GraalVM AOT |

### 2. OOP and Design Paradigms

| Grade | Grading criteria | MUST hit |
| ---- | -------- | -------- |
| L1 | Interfaces vs abstract classes stop at "single inheritance vs multiple implementation" | — |
| L2 | Knows `default method`, can cite `List.sort` | — |
| L3 | Can analyze design decisions | **MUST hit at least 2 items:** ① `default method` guarantees Binary Compatibility — class files compiled earlier link against the new interface without recompilation ② a selection framework for interface default methods vs abstract classes at SDK extension points (state or not, constructor needed or not, `protected` members needed or not) ③ the Bootstrap process of `invokedynamic` under Lambda (`LambdaMetafactory` generates an anonymous class at runtime rather than at compile time) |
| L4 | Can critically analyze across languages | **MUST hit at least 1 item:** ① the design compromise that `default method` cannot hold state (compare Scala trait `val` members) ② the expressiveness of Sealed Classes + Pattern Matching for algebraic data types (ADT) ③ the evolution of encapsulation boundaries seen through JPMS `exports` granularity (package level → module level) |

### 3. Exception Handling and Performance Cost

| Grade | Grading criteria | MUST hit |
| ---- | -------- | -------- |
| L1 | Knows only `try-catch-finally` | — |
| L2 | Checked vs Unchecked classification, `try-with-resources` | — |
| L3 | Can quantify the performance cost of exceptions | **MUST hit at least 2 items:** ① `Throwable.fillInStackTrace()` is the core bottleneck — it must walk the current thread's call stack frames to build the `StackTraceElement[]` ② mitigations: override `fillInStackTrace()` as an empty method / reuse a static exception instance ③ the full causal chain from an exception storm to Full GC: high-frequency exceptions → massive `StackTraceElement[]` arrays → old generation fills fast → CMS Concurrent Mode Failure / G1 Full GC |
| L4 | Can analyze at the JVM implementation level | **MUST hit at least 1 item:** ① the JVM Exception Table — the `exception_table` structure in the `Code` attribute (`start_pc/end_pc/handler_pc/catch_type`), and the "zero-cost exception" design philosophy (zero overhead when no exception is thrown vs C++'s table-driven approach) ② the defer stack-unwinding mechanism and cost difference vs Go `panic/recover` ③ how JEP 358 Helpful NPE works (embeds the variable name in the NPE message by analyzing the bytecode) |

### 4. Collections Framework and Hardware-Level Performance

| Grade | Grading criteria | MUST hit |
| ---- | -------- | -------- |
| L1 | Stops at the API level | — |
| L2 | Has read HashMap source, knows resize and treeification | — |
| L3 | Can quantitatively analyze performance bottlenecks | **MUST hit at least 2 items:** ① the full cost of `ArrayList` growth — `Arrays.copyOf` memory copy + the old array becomes garbage → without `ensureCapacity`, growing from the default capacity 10 to 1 million elements takes about 17 resizes and copies about 1.9 million elements cumulatively ② the CPU spike from `HashMap` rehash on resize + the JDK 8 optimization (`(e.hash & oldCap) == 0` splitting into high/low halves, avoiding re-hashing) ③ scheme selection for large data volumes: ArrayList (pre-allocated) vs sharded List vs streaming |
| L4 | Hardware-level / cross-language view | **MUST hit at least 1 item:** ① the performance difference that CPU Cache Line (64 bytes) prefetching makes on contiguous memory (ArrayList) vs linked lists (LinkedList) — not "a bit faster" but an order of magnitude (sequential traversal of ArrayList can be 10-50× faster than LinkedList) ② the impact of False Sharing inside concurrent collections — `ConcurrentHashMap`'s `CounterCell` padding with the `@Contended` annotation ③ how Go slice growth (< 256 doubles / ≥ 256 about 1.25×) differs from Java ArrayList (1.5×), and the design considerations behind it |

### 5. Concurrency Primitives and Virtual Threads

| Grade | Grading criteria | MUST hit |
| ---- | -------- | -------- |
| L1 | Basic usage of `synchronized` and `Thread` | — |
| L2 | Rough lock escalation flow, has used `ReentrantLock` | — |
| L3 | Can explain the implementation mechanism clearly | **MUST hit at least 3 items:** ① the CLH-variant queue structure of AQS (`Node.prev/next/waitStatus`, head node is a dummy node) ② the difference between fair and non-fair locks in `tryAcquire` — the fair lock adds a `hasQueuedPredecessors()` check ③ why JDK 15 deprecated biased locking (JEP 374 — maintenance cost far exceeds benefit, modern apps are mostly multi-threaded contended scenarios, and biased lock revocation is expensive) ④ the full `synchronized` lock escalation path (no lock → biased → lightweight CAS spin → heavyweight monitor enter) and the trigger condition of each stage |
| L4 | OS level + virtual threads in depth | **MUST hit at least 2 items:** ① the `synchronized` heavyweight lock relies on Linux `futex` underneath — user mode → kernel mode switch, each context switch about 1-5μs ② the virtual thread Pinning problem — when blocking IO runs inside a `synchronized` block or a native method, the Carrier Thread cannot unmount → the platform thread pool is exhausted → throughput drops instead. Fix: replace `synchronized` with `ReentrantLock` ③ detecting Pinning: `-Djdk.tracePinnedThreads=short` or the JFR `jdk.VirtualThreadPinned` event ④ the problem domain of Structured Concurrency (JEP 453) — subtask lifecycles are bound to the parent task, preventing thread leaks |

### 6. Class Loading and Modular Isolation

| Grade | Grading criteria | MUST hit |
| ---- | -------- | -------- |
| L1 | Knows only the name "parent delegation" | — |
| L2 | Knows parent delegation can be broken, can cite SPI/Tomcat | — |
| L3 | Can implement a custom isolation scheme | **MUST hit at least 2 items:** ① Tomcat `WebAppClassLoader`'s isolation strategy — try loading it itself first (`findClass`), delegate to the parent loader only when not found, the reverse of standard parent delegation ② the correct way for a custom ClassLoader to break parent delegation — override `loadClass()` rather than `findClass()` (the former controls the delegation logic, the latter only the lookup logic) ③ the actual behavior of Spring Boot `LaunchedURLClassLoader` — it does not fully break parent delegation but extends the load path |
| L4 | Evolution view + scheme comparison | **MUST hit at least 1 item:** ① the OSGi → Jigsaw/JPMS evolution, analyzing the core tension of modularity (runtime dynamism vs compile-time determinism, OSGi's Bundle hot deployment vs JPMS's static module graph) ② the principle of Maven Shade Plugin bytecode Relocation — ASM rewrites package references in bytecode; limits: cannot handle SPI config files or reflective strings ③ GraalVM Native Image's restriction on dynamic class loading (`Class.forName` requires registration in `reflect-config.json`) and mitigation strategies |

### 7. JVM Memory and GC Tuning

| Grade | Grading criteria | MUST hit |
| ---- | -------- | -------- |
| L1 | Knows only heap and stack | — |
| L2 | Knows the generational model, can explain the Young GC / Full GC difference | — |
| L3 | Can analyze GC logs and propose a tuning plan | **MUST hit at least 2 items:** ① G1's Region partitioning and RSet maintenance cost — each Region's RSet takes about 5-10% of the heap, and the choice of Region size 1-32MB affects memory and performance ② the full causal chain of CMS Concurrent Mode Failure — the old generation fills up during concurrent marking → degrades to Serial Old → long STW ③ the three paths of object promotion to the old generation (age threshold / dynamic age determination / large objects promoted directly) and the actual impact of `-XX:PretenureSizeThreshold` |
| L4 | Can analyze at the level of GC algorithm design philosophy | **MUST hit at least 1 item:** ① the multi-view mapping principle of ZGC Colored Pointers — how the Marked0/Marked1/Remapped views use the low 4 bits of the 44-bit address space ② the write barrier difference between generational ZGC (JDK 21) and single-generation ZGC — the generational design adds the double overhead of SATB write barrier + store barrier ③ how Go GC's hybrid write barrier (Yuasa-style + Dijkstra-style) compares with Java SATB, and the design trade-offs |

### 8. Thread Pools and Async Task Orchestration

| Grade | Grading criteria | MUST hit |
| ---- | -------- | -------- |
| L1 | Only uses `Executors` factory methods | — |
| L2 | Knows the 7 core parameters, can construct `ThreadPoolExecutor` manually | — |
| L3 | Can quantitatively design thread pool parameters for a business scenario | **MUST hit at least 2 items:** ① the thread count estimation formula — CPU-bound N+1 / IO-bound N×(1+W/C), and can explain why IO-bound multiplies by (1+W/C) ② a complete scheme for dynamic thread pool tuning — runtime limits of `setCorePoolSize`/`setMaximumPoolSize` (queue capacity cannot be changed at runtime), how Hippo4j/Dynamic TP implement it ③ thread pool monitoring metrics — collecting `activeCount`/`queueSize`/`completedTaskCount`/`rejectedCount` and setting alert thresholds |
| L4 | Can compare cross-language concurrent scheduling models | **MUST hit at least 1 item:** ① the design-philosophy gap between Go `GOMAXPROCS` and Java `ForkJoinPool` parallelism — P's local queue in Go's GMP model vs Java's work-stealing deque ② structured concurrency (JEP 453) vs Kotlin Coroutine structured concurrency — `StructuredTaskScope`'s `ShutdownOnFailure`/`ShutdownOnSuccess` vs Kotlin's `coroutineScope`/`supervisorScope` ③ why the virtual thread carrier thread pool (ForkJoinPool) defaults to a parallelism equal to the CPU core count — why it is not allowed to scale dynamically like Go |

---

## Scenario Bank

The scenarios below are all adapted from real production incidents / technical decisions. **Never dump all questions at once.**
Each scenario includes **Design intent** (for the interviewer only, never shown to the candidate).

### Dimension 1: Type System and Memory Model

**L2 lead-in**: 包装类型的缓存机制了解么？

> "一个风控服务，QPS 峰值 2 万，JDK 17，堆 4G，G1。某天 YGC 频率从每分钟 2 次飙升到每秒 3 次，但业务量没有明显变化，`jmap -histo` 显示 `java.lang.Long` 实例数排进了前三。代码里没有显式 `new Long()`。你的排查思路？"

**Design intent**:

- Expected path: autoboxing → `Long.valueOf` caches `-128~127` only by default → business IDs fall outside the cache range → every boxing allocates a `new Long()` → 20k QPS × 24B each (16B object header + 8B data) → about 480KB of new objects per second → Eden fills fast → YGC becomes frequent
- L3 candidates should produce the quantitative estimate above
- L4 candidates should mention that `-XX:AutoBoxCacheMax` has no effect on `Long` (only `Integer` is configurable)

### Dimension 2: OOP and Design Paradigms

**L2 lead-in**: 接口的默认方法冲突如何解决？

> "你要设计一个支付网关的 SPI 扩展点，让各银行渠道方接入。要求：① 新增渠道不改框架代码 ② 渠道方不能误用框架内部类导致升级 breaking ③ 未来加新能力时不能 breaking change ④ 有能力下线某个渠道。JDK 17 环境。你怎么设计这个扩展体系？"

**Design intent**:

- Expected path: interface (`default method` provides the default implementation → new capabilities are non-breaking) → `sealed` restricts the implementation scope → JPMS `exports` precisely controls visible packages → `ServiceLoader` or Spring SPI for loading
- L3 candidates should draw a clear interface hierarchy and package structure
- L4 candidates should discuss the limits of `default method` (cannot hold state) and give a compensating design

### Dimension 3: Exception Handling and Performance Cost

**L2 lead-in**: 如何使用 `try-with-resources` 代替 `try-catch-finally`？

> "一个网关服务，逻辑很薄——校验、路由、转发。但高峰期 Full GC 频繁。MAT 分析发现 `Object[]` 占了 40% 堆，追溯引用链发现大量是 `Throwable.stackTrace` 数组。业务代码没有显式 `new Exception`。什么场景会触发？怎么解？"

**Design intent**:

- Expected path: upstream service timeout → many `SocketTimeoutException` / `ConnectException` → the JVM runs `fillInStackTrace()` on every exception creation → each exception carries a full stack frame array → deep request thread stack → a single exception's `StackTraceElement[]` may hold 100+ elements → the arrays enter the old generation → the old generation fills fast → Full GC
- L3 candidates should derive the full causal chain above
- L4 candidates should mention the JVM exception table's "zero-cost" design philosophy (zero overhead when no exception is thrown), and why that philosophy backfires into a trap in an exception-storm scenario

### Dimension 4: Collections Framework and Hardware-Level Performance

**L2 lead-in**: `ArrayBlockingQueue` 和 `LinkedBlockingQueue` 有什么区别？

> "数据同步任务：从上游拉取 100 万条记录到内存做聚合计算。测试环境 1 秒完成（1 万条数据），生产环境 10 分钟超时。生产数据量是测试的 100 倍，但 CPU 只有 30%。你怀疑什么？给出一个具体的数字估算来支撑你的判断。"

**Design intent**:

- Expected path: no `ensureCapacity` → starts from default capacity 10 → about 17 resizes → about 1.9 million elements copied cumulatively → the old array (about 1.3 million element slots) becomes garbage → if Eden is not large enough, the large array is promoted straight to the old generation → frequent YGC or even Full GC → STW tanks throughput
- L3 candidates should give estimates of the resize count and copy volume
- L4 candidates should mention the GC policy that promotes large objects straight to the old generation (`-XX:PretenureSizeThreshold`), and the architectural option of streaming instead of loading everything

### Dimension 5: Concurrency Primitives and Virtual Threads

**L2 lead-in**: Java 传统线程和虚拟线程有什么区别？

> "老系统从 JDK 8 升到 JDK 21，某些接口用了虚拟线程后发现：吞吐量不升反降。`jstack` 看到大量载体线程（Carrier Thread）BLOCKED 在 `sun.nio.ch.SocketChannelImpl.read`，而虚拟线程数（`Thread.ofVirtual` 创建）远超载体线程数。发生了什么？怎么解？"

**Design intent**:

- Expected path: when a virtual thread performs blocking IO wrapped in `synchronized` → Pinning → the carrier thread cannot unmount → the carrier thread pool (default = CPU cores) is exhausted → subsequent virtual threads cannot be scheduled → throughput drops instead
- L3 candidates should state the Pinning concept and its relation to `synchronized`
- L4 candidates should give: ① the detection flag `-Djdk.tracePinnedThreads=short` ② the fix (`synchronized` → `ReentrantLock`) ③ the JFR event `jdk.VirtualThreadPinned`

### Dimension 6: Class Loading and Modular Isolation

**L2 lead-in**: 有哪些场景破坏了双亲委派模型？

> "微服务 A 引入了一个三方风控 SDK，该 SDK 内部 shade 了 Jackson 2.9，而主应用用的是 Jackson 2.15。运行时发现：主应用的某个 Controller 返回 JSON 序列化结果异常——`@JsonInclude(NON_NULL)` 没生效，null 字段被序列化了。你没有权限修改三方 SDK 的 shade 配置。怎么办？"

**Design intent**:

- Expected path: parent delegation → the parent loader loaded the SDK's Jackson 2.9 → the new `@JsonInclude` behavior in the app's Jackson 2.15 does not take effect → options: ① Maven Shade relocation of your own code ② custom ClassLoader isolation ③ exclude the SDK's Jackson dependency (if the SDK does not rely on Jackson-specific API)
- L3 candidates should explain the actual load order of Spring Boot `LaunchedURLClassLoader`
- L4 candidates should discuss the limits of Shade Relocation (SPI config files and reflective strings are not relocated)

### Dimension 7: JVM Memory and GC Tuning

**L2 lead-in**: Java 中的 Young GC、Old GC、Full GC 和 Mixed GC 的区别是什么？

> "一个订单服务，JDK 17，G1，堆 8G。日常 YGC 平均 50ms，每隔 2-3 天出现一次 2-3 秒的 STW。GC 日志显示这次是 Full GC，触发原因是 `G1 Evacuation Pause` 阶段 `to-space exhausted`。业务侧没有明显流量突增。你怎么排查和解决？"

**Design intent**:

- Expected path: `to-space exhausted` = G1 lacks target Region space during evacuation → possible causes: objects promoted too fast / Humongous objects occupying too many Regions / old generation fragmentation → investigation directions: `jmap -histo` for large objects / GC log for promotion rate / tune `-XX:G1HeapRegionSize` or raise `-XX:G1ReservePercent`
- L3 candidates should explain what `to-space exhausted` means and its common triggers
- L4 candidates should mention the `G1ReservePercent` mechanism (default 10%), and G1's special handling of Humongous objects (occupying a whole Region or several consecutive Regions)

### Dimension 8: Thread Pools and Async Task Orchestration

**L2 lead-in**: Java 线程池的核心线程会被回收吗？

> "一个营销活动系统，大促期间 QPS 从 500 飙升到 5000。现有线程池配置：`corePoolSize=10, maxPoolSize=50, queueCapacity=200, AbortPolicy`。大促开始 5 分钟后，大量请求被拒绝，但 CPU 只有 40%，内存正常。你怎么分析和调整？"

**Design intent**:

- Expected path: 5000 QPS × per-request latency (say 20ms) = about 100 concurrent threads needed → current maxPoolSize=50 is not enough → once the 200-slot queue fills, requests are rejected outright → but CPU at 40% means there is room to scale → options: raise maxPoolSize / switch to CallerRunsPolicy for degradation / dynamic tuning
- L3 candidates should give the quantitative estimate (QPS × response time = required concurrent threads)
- L4 candidates should mention dynamic thread pool schemes (Hippo4j/Dynamic TP) and analyze how well virtual threads fit this scenario

---

## Trap Probes

For trap probe timing, see the SKILL.md「陷阱追问」(trap probes) section: in dimensions 5-7 (the core deep-dive / high-pressure zone), deliberately give 1 false premise to test the candidate's error-correction ability and how genuine their source-code knowledge is.

| Dimension | Trap example | Correct understanding |
| ---- | -------- | -------- |
| 并发 (concurrency) | "我听说 `ConcurrentHashMap` JDK 8 里还是 Segment 分段锁，对吧？" | JDK 8 already switched to CAS + synchronized locking the Node head |
| 集合 (collections) | "`HashMap` 树化阈值是 6，链表化阈值是 8，对吧？" | Reversed — treeify threshold 8, untreeify threshold 6 |
| 虚拟机 (JVM) | "G1 的 Young GC 是并发执行的，不 STW，对吧？" | G1 Young GC is still STW; only the pause time is controllable |
| 类型 (type system) | "`Long` 的缓存上限可以用 `-XX:AutoBoxCacheMax` 调大，对吧？" | That flag only works for `Integer`; `Long` is fixed at 127 |
