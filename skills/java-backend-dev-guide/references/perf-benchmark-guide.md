# Performance Benchmarking Guide

> **Summary**
>
> - **Core constraint**: New APIs MUST declare performance targets (P50/P99/throughput) in spec.md non-functional requirements; benchmark tests MUST be executed before going live with results recorded; performance regression > 20% MUST block merge
> - **Key thresholds**: API P99 < 200ms (CRUD) / < 500ms (complex queries); batch operation throughput ≥ 1000 TPS; GC pause < 100ms
> - **Common violations**: spec.md without performance targets, no benchmark test before going live, benchmark test without warmup, JMH tests sharing mutable state, performance regression not blocking merge

---

## 1. Performance Target Definition

### 1.1. Performance Declaration in spec.md

Each new API **MUST** declare the following metrics in `spec.md` non-functional requirements:

| Metric | Description | Example |
|--------|-------------|---------|
| P50 latency | Response time for 50% of requests | ≤ 50ms |
| P99 latency | Response time for 99% of requests | ≤ 200ms |
| Throughput | Single instance QPS/TPS | ≥ 500 QPS |
| Concurrent users | Expected peak concurrency | 100 |

### 1.2. Default Performance Baseline (Example)

When not explicitly declared in spec.md, can refer to the following defaults (adjust based on project reality):

| API type | P99 latency | Throughput |
|----------|-------------|-----------|
| Single table CRUD | ≤ 200ms | ≥ 500 QPS |
| Cross-table query / list pagination | ≤ 500ms | ≥ 200 QPS |
| Full-text search (ES) | ≤ 300ms | ≥ 300 QPS |
| Batch write (≥ 100 records) | ≤ 1s | ≥ 1000 TPS |
| Async task (MQ triggered) | ≤ 5s | — |

---

## 2. Benchmark Testing Methods

### 2.1. API-level Benchmark Testing

Use JMeter / wrk / hey for HTTP API load testing.

**Before testing MUST**:

- Warmup: First execute 100 requests to warm up JIT compilation and connection pool
- Data preparation: Ensure test data volume matches production scale (at least 100K rows)
- Environment isolation: Use independent test environment, avoid affecting other tests

**Test report format**:

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

### 2.2. Method-level Micro-benchmark Testing

Use JMH (Java Microbenchmark Harness) to test hot method performance:

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

**JMH MUST**:

- **MUST NOT** use mutable state in `@State(Scope.Benchmark)` (unless the test is specifically about concurrent modification)
- **MUST** set `@Warmup` to at least 3 rounds of warmup
- **MUST** set `@Measurement` to at least 5 rounds of measurement
- **MUST NOT** ignore dead code elimination (use `Blackhole.consumeCPU` or return results)

### 2.3. Database Query Performance Testing

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

## 3. Performance Gates

### 3.1. CI Stage Gates

| Check item | Blocking condition | Notes |
|-----------|-------------------|-------|
| API P99 latency | > 150% of non-functional requirement SLA | Exceeding MUST block |
| Performance regression | > 20% (relative to baseline) | Baseline determined by last release branch test results |
| Memory leak | Heap memory continuously growing during load test | Observe for 10+ minutes |

### 3.2. Pre-launch Acceptance Gates

| Check item | Blocking condition |
|-----------|-------------------|
| Benchmark test report | Not provided MUST block |
| Performance target met | P99 exceeding MUST block |
| Gray-release strategy | No gray-release plan MUST block |
| Rollback plan | No rollback plan MUST block |
| Monitoring alerts | No P99 / Error Rate alerts MUST block |

---

## 4. Common Performance Issues and Troubleshooting

### 4.1. High-Frequency Performance Issues

| Issue | Troubleshooting direction | Typical tools |
|-------|--------------------------|--------------|
| Slow SQL | Missing index / implicit conversion / deep pagination | `EXPLAIN` / slow query log |
| GC pause | Large object allocation / memory leak | `jstat` / GC logs / MAT |
| Thread blocking | Lock contention / connection pool exhaustion | Thread Dump / Arthas |
| Network timeout | RPC timeout / connection pool configuration | Distributed tracing / Sentinel |
| Cache miss | Key design / TTL too short | Redis `INFO` / slow log |

### 4.2. Performance Optimization Priority

```
1. 减少调用次数（缓存 / 批量 / 合并请求）
2. 减少单次耗时（索引 / 算法 / 并行化）
3. 减少资源占用（连接池 / 线程池 / 内存）
```

---

## 5. Performance Testing Checklist and Anti-Patterns

### 5.1. Checklist

Confirm item by item before going live:

- [ ] spec.md has declared performance targets (P50/P99/throughput)
- [ ] API-level benchmark test executed, results meet targets
- [ ] Hot methods have JMH micro-benchmark tests (if applicable)
- [ ] Database queries verified for index usage through `EXPLAIN`
- [ ] No memory leak during load test (heap memory stable)
- [ ] GC pause < 100ms
- [ ] Benchmark test report attached to PR description
- [ ] P99 / Error Rate monitoring alerts configured

### 5.2. Common Anti-Patterns (Prohibited)

```
❌ spec.md 无性能目标
❌ 上线前未做基准测试
❌ 基准测试未预热（JIT 未编译，结果偏高）
❌ 测试数据量与生产差距过大
❌ JMH 测试共享可变状态
❌ 性能回归 > 20% 仍允许合并
❌ 无监控告警直接上线
```
