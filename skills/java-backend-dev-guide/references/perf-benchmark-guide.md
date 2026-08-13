# 性能基准测试指南

> **摘要**
>
> - **核心约束**：新增接口 MUST 在 spec.md 非功能需求中声明性能目标（P50/P99/吞吐量）；上线前 MUST 执行基准测试并记录结果；性能回归 > 20% MUST 阻断合并
> - **关键阈值**：接口 P99 < 200ms（CRUD）/ < 500ms（复杂查询）；批量操作吞吐量 ≥ 1000 TPS；GC 暂停 < 100ms
> - **常见违规**：spec.md 无性能目标、上线前未做基准测试、基准测试未预热、JMH 测试共享可变状态、性能回归未阻断合并

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 性能目标定义

### 1.1. spec.md 中的性能声明

每个新增接口 **MUST** 在 `spec.md` 非功能需求中声明以下指标：

| 指标       | 说明               | 示例      |
| ---------- | ------------------ | --------- |
| P50 延迟   | 50% 请求的响应时间 | ≤ 50ms    |
| P99 延迟   | 99% 请求的响应时间 | ≤ 200ms   |
| 吞吐量     | 单实例 QPS/TPS     | ≥ 500 QPS |
| 并发用户数 | 预期峰值并发       | 100       |

### 1.2. 默认性能基线（示例）

未在 spec.md 中显式声明时，可参考以下默认值（需根据项目实际调整）：

| 接口类型             | P99 延迟 | 吞吐量     |
| -------------------- | -------- | ---------- |
| 单表 CRUD            | ≤ 200ms  | ≥ 500 QPS  |
| 跨表查询 / 列表分页  | ≤ 500ms  | ≥ 200 QPS  |
| 全文检索（ES）       | ≤ 300ms  | ≥ 300 QPS  |
| 批量写入（≥ 100 条） | ≤ 1s     | ≥ 1000 TPS |
| 异步任务（MQ 触发）  | ≤ 5s     | —          |

---

## 2. 基准测试方法

### 2.1. 接口级基准测试

使用 JMeter / wrk / hey 进行 HTTP 接口压测。

**测试前 MUST**：

- 预热：先执行 100 次请求预热 JIT 编译和连接池
- 数据准备：确保测试数据量与生产量级一致（至少 10 万行）
- 环境隔离：使用独立测试环境，避免影响其他测试

**测试报告格式**：

```text
接口：POST /api/article/publish
数据量：100 万行
并发数：50
持续时间：60s
结果：
  - QPS：523
  - P50：45ms
  - P99：187ms
  - 错误率：0.0%
  - 结论：满足 P99 ≤ 200ms 目标 ✓
```

### 2.2. 方法级微基准测试

使用 JMH（Java Microbenchmark Harness）测试热点方法性能：

```java
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 3, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(1)
@State(Scope.Benchmark)
public class ArticleConverterBenchmark {

    private ArticleDO articleDO;

    @Setup
    public void setup() {
        articleDO = new ArticleDO();
        articleDO.setId(1L);
        articleDO.setTitle("测试文章");
    }

    @Benchmark
    public ArticleVO mapStruct() {
        return ArticleConverter.INSTANCE.toVO(articleDO);
    }

    @Benchmark
    public ArticleVO manual() {
        ArticleVO vo = new ArticleVO();
        vo.setId(articleDO.getId());
        vo.setTitle(articleDO.getTitle());
        return vo;
    }
}
```

**JMH MUST**：

- **MUST NOT** 在 `@State(Scope.Benchmark)` 中使用可变状态（除非测试的就是并发修改）
- **MUST** 设置 `@Warmup` 至少 3 轮预热
- **MUST** 设置 `@Measurement` 至少 5 轮测量
- **MUST NOT** 忽略死代码消除（使用 `Blackhole.consumeCPU` 或返回结果）

### 2.3. 数据库查询性能测试

```java
@Test
void testQueryPerformance() {
    List<ArticleDO> articles = buildTestArticles(100_000);
    articleDao.saveBatch(articles, 500);

    // 预热
    for (int i = 0; i < 10; i++) {
        articleDao.selectPage(page, wrapper);
    }

    long start = System.nanoTime();
    for (int i = 0; i < 100; i++) {
        articleDao.selectPage(Page.of(i % 100, 20), wrapper);
    }
    long costMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start);
    long avgMs = costMs / 100;

    assertThat(avgMs).isLessThan(50); // 单次查询平均 < 50ms
}
```

---

## 3. 性能门禁

### 3.1. CI 阶段门禁

| 检查项        | 阻断条件                 | 说明                                |
| ------------- | ------------------------ | ----------------------------------- |
| 接口 P99 延迟 | > 非功能需求 SLA 的 150% | 超标 MUST 阻断                      |
| 性能回归      | > 20%（相对基线）        | 基线由上次 release 分支测试结果确定 |
| 内存泄漏      | 压测期间堆内存持续增长   | 运行 10 分钟以上观察                |

### 3.2. 上线前验收门禁

| 检查项       | 阻断条件                           |
| ------------ | ---------------------------------- |
| 基准测试报告 | 未提供 MUST 阻断                   |
| 性能目标达标 | P99 超标 MUST 阻断                 |
| 灰度策略     | 无灰度方案 MUST 阻断               |
| 回滚方案     | 无回滚方案 MUST 阻断               |
| 监控告警     | 无 P99 / Error Rate 告警 MUST 阻断 |

---

## 4. 常见性能问题与排查

### 4.1. 高频性能问题

| 问题       | 排查方向                     | 典型工具                |
| ---------- | ---------------------------- | ----------------------- |
| 慢 SQL     | 索引缺失 / 隐式转换 / 深分页 | `EXPLAIN` / 慢查询日志  |
| GC 暂停    | 大对象分配 / 内存泄漏        | `jstat` / GC 日志 / MAT |
| 线程阻塞   | 锁竞争 / 连接池耗尽          | 线程 Dump / Arthas      |
| 网络超时   | RPC 超时 / 连接池配置        | Trace 链路 / Sentinel   |
| 缓存未命中 | Key 设计 / TTL 过短          | Redis `INFO` / 慢日志   |

### 4.2. 性能优化优先级

```
1. 减少调用次数（缓存 / 批量 / 合并请求）
2. 减少单次耗时（索引 / 算法 / 并行化）
3. 减少资源占用（连接池 / 线程池 / 内存）
```

---

## 5. 性能测试 Checklist 与反模式

### 5.1. Checklist

上线前逐项确认：

- [ ] spec.md 已声明性能目标（P50/P99/吞吐量）
- [ ] 已执行接口级基准测试，结果满足目标
- [ ] 热点方法已做 JMH 微基准测试（如有时）
- [ ] 数据库查询已通过 `EXPLAIN` 验证索引使用
- [ ] 压测期间无内存泄漏（堆内存稳定）
- [ ] GC 暂停 < 100ms
- [ ] 基准测试报告已附在 PR 描述中
- [ ] 已配置 P99 / Error Rate 监控告警

### 5.2. 常见反模式（禁止）

```
❌ spec.md 无性能目标
❌ 上线前未做基准测试
❌ 基准测试未预热（JIT 未编译，结果偏高）
❌ 测试数据量与生产差距过大
❌ JMH 测试共享可变状态
❌ 性能回归 > 20% 仍允许合并
❌ 无监控告警直接上线
```
