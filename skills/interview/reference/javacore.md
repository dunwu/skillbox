# Java 核心面试知识维度

## 题库索引

面试前需读取题库索引文件，确认已考察题目（等级和评估列不为空的不再重复出）：

**路径来源**：读取 `config.json` 中的 `questionBankPath` 字段。

如果 `config.json` 不存在或路径无效，按 SKILL.md "第零步：首次配置检查" 流程处理。

---

## 评测尺度对标表

**评分铁律：逐条比对"必须命中"的内容。缺失任意关键项，降一级处理。**
**"必须命中"的设计原则：背诵面经无法命中，必须有真实踩坑或源码精读经验。**

### 1. 类型系统与内存模型

| 等级 | 判定标准 | 必须命中 |
| ---- | -------- | -------- |
| L1 不通过 | `==` vs `equals` 混用无感知 | — |
| L2 勉强通过 | 知道 `Integer.valueOf` 缓存 `-128~127` | 能说出缓存边界值上 `==` 的行为差异 |
| L3 通过 | 能定量分析内存影响 | **至少命中 2 项：** ① `-XX:AutoBoxCacheMax` 参数名且能说清其生效机制（仅影响 `Integer`，不影响 `Long` 的默认上限） ② 高并发下 Long 装箱的对象分配速率估算方法（QPS × 每次装箱字节数 × 对象头开销） ③ 包装类缓存在堆中的数据结构（`Integer.cache[]`，类初始化时分配） |
| L4 优秀 | 能批判性分析 Java 类型系统设计代价 | **至少命中 1 项：** ① Project Valhalla Value Types 的核心目标（消除对象头 + 扁平化内存布局 + 消除 Identity 语义） ② 对比 Go/Rust 栈分配策略的逃逸分析差异 ③ 自动装箱在 GraalVM AOT 场景下的初始化限制 |

### 2. 面向对象与设计范式

| 等级 | 判定标准 | 必须命中 |
| ---- | -------- | -------- |
| L1 | 接口 vs 抽象类只停留在"单继承 vs 多实现" | — |
| L2 | 知道 `default method`，能举 `List.sort` | — |
| L3 | 能分析设计决策 | **至少命中 2 项：** ① `default method` 保证二进制兼容性（Binary Compatibility）——旧编译的 class 文件无需重编译即可链接到新接口 ② 接口 default method vs 抽象类在 SDK 扩展点中的选型决策框架（有无状态、是否需构造函数、是否需 `protected` 成员） ③ Lambda 底层 `invokedynamic` 的 Bootstrap 过程（`LambdaMetafactory` 生成匿名类而非编译期生成） |
| L4 | 能跨语言批判性分析 | **至少命中 1 项：** ① `default method` 无法持有状态导致的设计妥协（对比 Scala trait 的 `val` 成员） ② Sealed Classes + Pattern Matching 组合实现代数数据类型（ADT）的表达力 ③ 从 JPMS `exports` 粒度谈封装边界的演进（包级 → 模块级） |

### 3. 异常处理与性能代价

| 等级 | 判定标准 | 必须命中 |
| ---- | -------- | -------- |
| L1 | 只知道 `try-catch-finally` | — |
| L2 | Checked vs Unchecked 分类、`try-with-resources` | — |
| L3 | 能量化异常的性能代价 | **至少命中 2 项：** ① `Throwable.fillInStackTrace()` 是核心瓶颈——需遍历当前线程调用栈帧构建 `StackTraceElement[]` ② 优化方案：重写 `fillInStackTrace()` 为空方法 / 使用静态异常实例复用 ③ 异常风暴导致 Full GC 的完整因果链：高频异常 → 大量 `StackTraceElement[]` 数组 → 老年代快速填充 → CMS Concurrent Mode Failure / G1 Full GC |
| L4 | 能从 JVM 实现层面分析 | **至少命中 1 项：** ① JVM 异常表（Exception Table）——`Code` 属性中的 `exception_table` 结构（`start_pc/end_pc/handler_pc/catch_type`），以及"零成本异常"设计哲学（无异常时零开销 vs C++ 的表驱动） ② 对比 Go `panic/recover` 的 defer 栈展开机制与成本差异 ③ JEP 358 Helpful NPE 的实现原理（在 NPE message 中嵌入变量名，通过字节码分析定位） |

### 4. 集合框架与硬件级性能

| 等级 | 判定标准 | 必须命中 |
| ---- | -------- | -------- |
| L1 | 只停留在 API 层面 | — |
| L2 | 读过 HashMap 源码，知道扩容和树化 | — |
| L3 | 能定量分析性能瓶颈 | **至少命中 2 项：** ① `ArrayList` 扩容的完整代价——`Arrays.copyOf` 内存拷贝 + 旧数组成为垃圾 → 若未 `ensureCapacity`，从默认容量 10 到 100 万元素需扩容约 17 次，累计拷贝约 190 万元素 ② `HashMap` 扩容 rehash 的 CPU 尖刺 + JDK 8 优化（`(e.hash & oldCap) == 0` 高低位拆分，避免重新 hash） ③ 大数据量场景的选型决策：ArrayList（预分配）vs 分片 List vs 流式处理 |
| L4 | 硬件级 / 跨语言视角 | **至少命中 1 项：** ① CPU Cache Line（64 字节）预取对连续内存（ArrayList）vs 链表（LinkedList）的性能差异——不是"快一点"，是数量级差异（顺序遍历 ArrayList 可比 LinkedList 快 10-50 倍） ② 伪共享（False Sharing）在并发集合中的影响——`ConcurrentHashMap` 的 `CounterCell` 使用 `@Contended` 注解填充 ③ 对比 Go slice 扩容策略（< 256 双倍增长 / ≥ 256 约 1.25 倍）与 Java ArrayList（1.5 倍）的差异及背后设计考量 |

### 5. 并发原语与虚拟线程

| 等级 | 判定标准 | 必须命中 |
| ---- | -------- | -------- |
| L1 | `synchronized` 和 `Thread` 基本用法 | — |
| L2 | 锁升级大致流程，用过 `ReentrantLock` | — |
| L3 | 能说清实现机制 | **至少命中 3 项：** ① AQS 的 CLH 变体队列结构（`Node.prev/next/waitStatus`，头节点为 dummy node） ② 公平锁 vs 非公平锁在 `tryAcquire` 中的差异——公平锁多了 `hasQueuedPredecessors()` 检查 ③ JDK 15 废弃偏向锁的原因（JEP 374——维护成本远超收益，现代应用多为多线程竞争场景，偏向锁撤销代价高） ④ `synchronized` 锁升级完整路径（无锁 → 偏向 → 轻量级 CAS 自旋 → 重量级 monitor enter）及各阶段的触发条件 |
| L4 | OS 层 + 虚拟线程深度 | **至少命中 2 项：** ① `synchronized` 重量级锁底层依赖 Linux `futex`——涉及用户态 → 内核态切换，单次上下文切换约 1-5μs ② 虚拟线程 Pinning 问题——`synchronized` 块或 native 方法中执行阻塞 IO 时，载体线程（Carrier Thread）无法卸载 → 平台线程池耗尽 → 吞吐量反降。解决方案：用 `ReentrantLock` 替代 `synchronized` ③ 检测 Pinning：`-Djdk.tracePinnedThreads=short` 或 JFR 的 `jdk.VirtualThreadPinned` 事件 ④ Structured Concurrency（JEP 453）解决的问题域——子任务生命周期与父任务绑定，避免线程泄漏 |

### 6. 类加载与模块化隔离

| 等级 | 判定标准 | 必须命中 |
| ---- | -------- | -------- |
| L1 | 只知道"双亲委派"名字 | — |
| L2 | 知道双亲委派可打破，能举 SPI/Tomcat | — |
| L3 | 能实现自定义隔离方案 | **至少命中 2 项：** ① Tomcat `WebAppClassLoader` 的隔离策略——先尝试自己加载（`findClass`），找不到才委派父加载器，与标准双亲委派相反 ② 自定义 ClassLoader 打破双亲委派的正确姿势——重写 `loadClass()` 而非 `findClass()`（前者控制委派逻辑，后者仅控制查找逻辑） ③ Spring Boot `LaunchedURLClassLoader` 的实际行为——并非完全打破双亲委派，而是扩展了加载路径 |
| L4 | 演进视角 + 方案对比 | **至少命中 1 项：** ① 从 OSGi → Jigsaw/JPMS 的演进分析模块化核心矛盾（运行时动态性 vs 编译期确定性，OSGi 的 Bundle 热部署 vs JPMS 的静态模块图） ② Maven Shade Plugin 字节码重定位（Relocation）原理——ASM 修改字节码中的包名引用，局限：无法处理 SPI 配置文件和反射字符串 ③ GraalVM Native Image 对动态类加载的限制（`Class.forName` 需 `reflect-config.json` 注册）及应对策略 |

### 7. JVM 内存与 GC 调优

| 等级 | 判定标准 | 必须命中 |
| ---- | -------- | -------- |
| L1 | 只知道堆和栈 | — |
| L2 | 知道分代模型、能说清 Young GC / Full GC 区别 | — |
| L3 | 能分析 GC 日志并给出调优方案 | **至少命中 2 项：** ① G1 的 Region 划分与 RSet 维护成本——每个 Region 的 RSet 约占堆的 5-10%，Region 大小 1-32MB 的选择对内存和性能的影响 ② CMS Concurrent Mode Failure 的完整因果链——并发标记期间老年代被填满 → 退化为 Serial Old → 长时间 STW ③ 对象晋升老年代的三条路径（年龄阈值 / 动态年龄判断 / 大对象直接晋升）及 `-XX:PretenureSizeThreshold` 的实际影响 |
| L4 | 能从 GC 算法设计哲学层面分析 | **至少命中 1 项：** ① ZGC 着色指针（Colored Pointers）的多视图映射原理——Marked0/Marked1/Remapped 三个视图如何利用 44 位地址空间中的低 4 位 ② 分代 ZGC（JDK 21）与单代 ZGC 的写屏障差异——分代引入后需要 SATB 写屏障 + 存储屏障双重开销 ③ 对比 Go GC 的混合写屏障（Yuasa-style + Dijkstra-style）与 Java SATB 的设计权衡 |

### 8. 线程池与异步任务编排

| 等级 | 判定标准 | 必须命中 |
| ---- | -------- | -------- |
| L1 | 只会 `Executors` 工厂方法 | — |
| L2 | 知道 7 大参数，能手动构造 `ThreadPoolExecutor` | — |
| L3 | 能根据业务场景定量设计线程池参数 | **至少命中 2 项：** ① 线程数估算公式——CPU 密集型 N+1 / IO 密集型 N×(1+W/C)，并能解释为什么 IO 密集型要乘 (1+W/C) ② 线程池动态调参的完整方案——`setCorePoolSize`/`setMaximumPoolSize` 的运行时限制（队列容量不可动态修改），Hippo4j/Dynamic TP 的实现原理 ③ 线程池监控指标——`activeCount`/`queueSize`/`completedTaskCount`/`rejectedCount` 的采集与告警阈值设置 |
| L4 | 能对比跨语言并发调度模型 | **至少命中 1 项：** ① Go `GOMAXPROCS` 与 Java `ForkJoinPool` parallelism 的设计哲学差异——Go 的 GMP 模型中 P 的本地队列 vs Java 的工作窃取双端队列 ② 结构化并发（JEP 453）vs Kotlin Coroutine 的结构化并发——`StructuredTaskScope` 的 `ShutdownOnFailure`/`ShutdownOnSuccess` vs Kotlin 的 `coroutineScope`/`supervisorScope` ③ 虚拟线程的载体线程池（ForkJoinPool）默认并行度为 CPU 核数的原因——为什么不像 Go 那样允许动态扩缩容 |

---

## 场景化题库

以下场景均基于真实生产事故/技术决策改编。**严禁一次性抛出所有题目。**
每个场景附 **设计意图**（面试官自用，不展示给候选人）。

### 维度 1：类型系统与内存模型

**L2 引子**：包装类型的缓存机制了解么？

> "一个风控服务，QPS 峰值 2 万，JDK 17，堆 4G，G1。某天 YGC 频率从每分钟 2 次飙升到每秒 3 次，但业务量没有明显变化，`jmap -histo` 显示 `java.lang.Long` 实例数排进了前三。代码里没有显式 `new Long()`。你的排查思路？"

**设计意图**：

- 期望路径：自动装箱 → `Long.valueOf` 默认只缓存 `-128~127` → 业务 ID 超出缓存范围 → 每次装箱都 `new Long()` → 2 万 QPS × 每次 24B（对象头 16B + 数据 8B）→ 每秒约 480KB 新对象 → Eden 区快速填满 → YGC 频繁
- L3 候选人应能给出上述定量估算
- L4 候选人应提到 `-XX:AutoBoxCacheMax` 对 `Long` 无效（仅 `Integer` 可配）

### 维度 2：面向对象与设计范式

**L2 引子**：接口的默认方法冲突如何解决？

> "你要设计一个支付网关的 SPI 扩展点，让各银行渠道方接入。要求：① 新增渠道不改框架代码 ② 渠道方不能误用框架内部类导致升级 breaking ③ 未来加新能力时不能 breaking change ④ 有能力下线某个渠道。JDK 17 环境。你怎么设计这个扩展体系？"

**设计意图**：

- 期望路径：接口（`default method` 提供默认实现 → 新增能力不 breaking）→ `sealed` 限制实现范围 → JPMS `exports` 精确控制可见包 → `ServiceLoader` 或 Spring SPI 加载
- L3 候选人应能画出清晰的接口层级和包结构
- L4 候选人应能讨论 `default method` 的局限性（无法持有状态）并给出补偿方案

### 维度 3：异常处理与性能代价

**L2 引子**：如何使用 `try-with-resources` 代替 `try-catch-finally`？

> "一个网关服务，逻辑很薄——校验、路由、转发。但高峰期 Full GC 频繁。MAT 分析发现 `Object[]` 占了 40% 堆，追溯引用链发现大量是 `Throwable.stackTrace` 数组。业务代码没有显式 `new Exception`。什么场景会触发？怎么解？"

**设计意图**：

- 期望路径：上游服务超时 → 大量 `SocketTimeoutException` / `ConnectException` → JVM 每次创建异常都执行 `fillInStackTrace()` → 每个异常携带完整栈帧数组 → 请求线程栈深 → 单个异常的 `StackTraceElement[]` 可能 100+ 个元素 → 数组进入老年代 → 老年代快速填充 → Full GC
- L3 候选人应能完整推导上述因果链
- L4 候选人应提到 JVM 的异常表"零成本"设计哲学（无异常时零开销），以及为何这个哲学在异常风暴场景下反而成为陷阱

### 维度 4：集合框架与硬件级性能

**L2 引子**：`ArrayBlockingQueue` 和 `LinkedBlockingQueue` 有什么区别？

> "数据同步任务：从上游拉取 100 万条记录到内存做聚合计算。测试环境 1 秒完成（1 万条数据），生产环境 10 分钟超时。生产数据量是测试的 100 倍，但 CPU 只有 30%。你怀疑什么？给出一个具体的数字估算来支撑你的判断。"

**设计意图**：

- 期望路径：未 `ensureCapacity` → 从默认容量 10 开始 → 扩容约 17 次 → 累计拷贝约 190 万元素 → 旧数组（约 130 万元素空间）成为垃圾 → 如果 Eden 区不够大，大数组直接晋升老年代 → YGC 频繁甚至 Full GC → STW 导致吞吐骤降
- L3 候选人应给出扩容次数和拷贝量的估算
- L4 候选人应提到大对象直接进老年代的 GC 策略（`-XX:PretenureSizeThreshold`），以及流式处理替代全量加载的架构方案

### 维度 5：并发原语与虚拟线程

**L2 引子**：Java 传统线程和虚拟线程有什么区别？

> "老系统从 JDK 8 升到 JDK 21，某些接口用了虚拟线程后发现：吞吐量不升反降。`jstack` 看到大量载体线程（Carrier Thread）BLOCKED 在 `sun.nio.ch.SocketChannelImpl.read`，而虚拟线程数（`Thread.ofVirtual` 创建）远超载体线程数。发生了什么？怎么解？"

**设计意图**：

- 期望路径：虚拟线程执行阻塞 IO 时，如果被 `synchronized` 包裹 → Pinning → 载体线程无法卸载 → 载体线程池（默认等于 CPU 核数）耗尽 → 后续虚拟线程无法调度 → 吞吐反降
- L3 候选人应说出 Pinning 概念和 `synchronized` 的关系
- L4 候选人应给出：① 检测命令 `-Djdk.tracePinnedThreads=short` ② 修复方案（`synchronized` → `ReentrantLock`） ③ JFR 事件 `jdk.VirtualThreadPinned`

### 维度 6：类加载与模块化隔离

**L2 引子**：有哪些场景破坏了双亲委派模型？

> "微服务 A 引入了一个三方风控 SDK，该 SDK 内部 shade 了 Jackson 2.9，而主应用用的是 Jackson 2.15。运行时发现：主应用的某个 Controller 返回 JSON 序列化结果异常——`@JsonInclude(NON_NULL)` 没生效，null 字段被序列化了。你没有权限修改三方 SDK 的 shade 配置。怎么办？"

**设计意图**：

- 期望路径：双亲委派 → 父加载器加载了 SDK 的 Jackson 2.9 → 主应用的 Jackson 2.15 中 `@JsonInclude` 的新行为未生效 → 方案：① Maven Shade 自己的重定位 ② 自定义 ClassLoader 隔离 ③ 排除 SDK 的 Jackson 依赖（如果 SDK 不依赖 Jackson 特有 API）
- L3 候选人应能解释 Spring Boot `LaunchedURLClassLoader` 的实际加载顺序
- L4 候选人应讨论 Shade Relocation 的局限性（SPI 配置文件、反射字符串不会被重定位）

### 维度 7：JVM 内存与 GC 调优

**L2 引子**：Java 中的 Young GC、Old GC、Full GC 和 Mixed GC 的区别是什么？

> "一个订单服务，JDK 17，G1，堆 8G。日常 YGC 平均 50ms，每隔 2-3 天出现一次 2-3 秒的 STW。GC 日志显示这次是 Full GC，触发原因是 `G1 Evacuation Pause` 阶段 `to-space exhausted`。业务侧没有明显流量突增。你怎么排查和解决？"

**设计意图**：

- 期望路径：`to-space exhausted` = G1 疏散时目标 Region 空间不足 → 可能原因：对象晋升速度过快 / Humongous 对象占用过多 Region / 老年代碎片 → 排查方向：`jmap -histo` 看大对象 / GC 日志看 promotion rate / 调整 `-XX:G1HeapRegionSize` 或增大 `-XX:G1ReservePercent`
- L3 候选人应能解释 `to-space exhausted` 的含义和常见触发条件
- L4 候选人应提到 G1 的 `G1ReservePercent`（默认 10%）机制，以及 Humongous 对象在 G1 中的特殊处理（占整个 Region 或连续多个 Region）

### 维度 8：线程池与异步任务编排

**L2 引子**：Java 线程池的核心线程会被回收吗？

> "一个营销活动系统，大促期间 QPS 从 500 飙升到 5000。现有线程池配置：`corePoolSize=10, maxPoolSize=50, queueCapacity=200, AbortPolicy`。大促开始 5 分钟后，大量请求被拒绝，但 CPU 只有 40%，内存正常。你怎么分析和调整？"

**设计意图**：

- 期望路径：QPS 5000 × 单请求耗时（假设 20ms）= 需要约 100 个并发线程 → 当前 maxPoolSize=50 不够 → 队列 200 满后直接拒绝 → 但 CPU 只有 40% 说明有扩容空间 → 方案：增大 maxPoolSize / 换 CallerRunsPolicy 降级 / 动态调参
- L3 候选人应能给出定量估算（QPS × 响应时间 = 所需并发线程数）
- L4 候选人应提到动态线程池方案（Hippo4j/Dynamic TP）以及虚拟线程在此场景下的适配性分析

---

## 陷阱追问

陷阱追问时机见 SKILL.md「陷阱追问」小节：在第 5-7 维度（核心深挖区/高压区），故意给出 1 个错误前提，测试候选人的纠错能力和源码真实度。

| 维度 | 陷阱示例 | 正确认知 |
| ---- | -------- | -------- |
| 并发 | "我听说 `ConcurrentHashMap` JDK 8 里还是 Segment 分段锁，对吧？" | JDK 8 已改为 CAS + synchronized 锁 Node 头节点 |
| 集合 | "`HashMap` 树化阈值是 6，链表化阈值是 8，对吧？" | 说反了——树化阈值 8，退化阈值 6 |
| 虚拟机 | "G1 的 Young GC 是并发执行的，不 STW，对吧？" | G1 Young GC 仍然 STW，只是停顿时间可控 |
| 类型 | "`Long` 的缓存上限可以用 `-XX:AutoBoxCacheMax` 调大，对吧？" | 该参数仅对 `Integer` 有效，`Long` 固定缓存到 127 |
