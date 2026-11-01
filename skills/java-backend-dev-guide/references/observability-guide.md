# Observability Standards

> **Summary**
>
> - **Core constraint**: Business-critical operations MUST log structured logs; new APIs MUST instrument latency metrics; exceptions MUST record complete context (do not swallow exceptions); for distributed tracing, TraceId MUST propagate to all downstream calls
> - **Key thresholds**: Log level INFO for business flows, WARN for expected exceptions, ERROR only for scenarios requiring manual intervention; single log entry MUST NOT exceed 1MB
> - **Common violations**: Only logging after catch without rethrowing (swallowing exceptions), logs without TraceId propagation, printing sensitive fields in plaintext, using System.out.println instead of logging framework

---

## 1. Logging Standards

### 1.1. Log Level Usage

| Level | Usage scenario | Example |
|-------|---------------|---------|
| `DEBUG` | Development debugging, prohibit printing large objects in production | Method parameters, intermediate variables |
| `INFO` | Business-critical nodes (request entry, state transition, async task trigger) | Article published successfully, review status changed |
| `WARN` | Expected exception situations (invalid parameters, business rules not met, retries) | Rate limiting triggered, circuit breaker degradation, idempotency interception |
| `ERROR` | Failures requiring manual intervention (external system unavailable, data inconsistency, BUG) | Database connection failed, MQ message processing exception |

**MUST NOT** use `System.out.println`; **MUST** use `Slf4j` + `LoggerFactory`.

### 1.2. Log Content Standards

```java
// ✅ 结构化日志：包含业务 ID、操作、结果
log.info("文章发布成功, articleId={}, authorId={}, cost={}ms", articleId, authorId, cost);

// ✅ 异常日志：保留完整堆栈
log.error("文章发布失败, articleId={}", articleId, e);

// ❌ 无上下文（无法定位问题）
log.info("发布成功");

// ❌ 吞异常（只打日志，不向上抛）
try { ... } catch (Exception e) { log.error("error", e); }
// MUST 改为：log.error(...); throw new {BizException}({ResultCode}.XXX, e);
```

### 1.3. Sensitive Field Masking

**MUST NOT** print plaintext sensitive fields in logs, masking rules see `security-guide.md §4`.

### 1.4. TraceId Propagation

- Spring Boot applications typically have tracing framework (such as Spring Cloud Sleuth / Micrometer Tracing) automatically inject TraceId into MDC, **no manual setup needed**
- When crossing threads (async tasks, thread pools), **MUST** use framework-provided MDC-propagating thread pool wrapper to pass context:

```java
// ✅ 使用可透传 TraceId 的线程池
// 方式一：Spring Cloud Sleuth / Micrometer 提供
@Bean
public Executor asyncExecutor() {
    return new TaskExecutorAdapter(
        new LazyTraceExecutor(traceTaskExecutor, threadPoolExecutor)
    );
}

// 方式二：手动包装 MDC 上下文
@Bean
public Executor asyncExecutor() {
    return runnable -> {
        Map<String, String> contextMap = MDC.getCopyOfContextMap();
        threadPoolExecutor.execute(() -> {
            if (contextMap != null) MDC.setContextMap(contextMap);
            try { runnable.run(); }
            finally { MDC.clear(); }
        });
    };
}

// ❌ 普通线程池，TraceId 丢失
@Bean
public Executor asyncExecutor() {
    return new ThreadPoolExecutor(...);
}
```

---

## 2. Metric Instrumentation Standards

### 2.1. API Latency Instrumentation

When adding new Controller APIs, **MUST** declare through interceptors or AOP annotations, framework automatically collects API latency, QPS, error rate:

```java
@PostMapping("/publish")
@{AuditLogAnnotation}(bizType = "ARTICLE_PUBLISH", sanitizeKeys = {"content"})
public {ResponseWrapper}<ArticleVO> publish(@RequestBody PublishRequest request) { ... }
```

> Project-level Skill can define specific audit log annotation names, default uses `{AuditLogAnnotation}` placeholder.

### 2.2. Business Metric Reporting

Critical business operations (content publishing, review approval/rejection, payments, etc.) **MUST** report business metrics:

```java
// 方式一：使用 Micrometer（Spring Boot 默认指标门面）
@Autowired
private MeterRegistry meterRegistry;

meterRegistry.counter("article.publish", "result", "success").increment();
meterRegistry.counter("article.publish", "result", "fail", "reason", resultCode.name()).increment();
meterRegistry.timer("article.publish.duration").record(cost, TimeUnit.MILLISECONDS);

// 方式二：使用项目自定义指标工具（由项目级 Skill 定义）
```

### 2.3. Alert Threshold Recommendations

| Metric type | Recommended alert threshold |
|-------------|---------------------------|
| API error rate | > 1% (P1 alert); > 5% (P0 alert) |
| API P99 latency | Exceeds 200% of non-functional requirement SLA |
| Business failure rate | Deviation from baseline > 50% |

> Specific alert rules configured on monitoring platform, AI is responsible for ensuring instrumentation code is correct, **not responsible** for configuring monitoring platform.

---

## 3. Distributed Tracing Standards

### 3.1. RPC Propagation

RPC frameworks (Dubbo / gRPC / Spring Cloud OpenFeign etc.) typically have built-in TraceId propagation, no additional configuration needed.

### 3.2. Async Message Propagation

When sending MQ messages, **MUST** write TraceId into message Header:

```java
// 发送时透传 TraceId（以 RabbitMQ 为例）
Message message = MessageBuilder.withBody(body)
    .setHeader("traceId", MDC.get("traceId"))
    .build();
rabbitTemplate.send(exchange, routingKey, message);

// 消费时恢复 TraceId
@RabbitListener(queues = "xxx")
public void consume(Message message) {
    String traceId = message.getMessageProperties().getHeader("traceId");
    MDC.put("traceId", traceId);
    try { ... } finally { MDC.remove("traceId"); }
}
```

---

## 4. Health Checks

When adding modules that depend on external systems (DB / Redis / ES / third-party HTTP services), **MUST** implement `HealthIndicator`, to ensure service health status can be detected by monitoring:

```java
@Component
public class ArticleServiceHealthIndicator implements HealthIndicator {
    @Override
    public Health health() {
        if (isDbAlive()) {
            return Health.up().build();
        }
        return Health.down().withDetail("reason", "DB connection failed").build();
    }
}
```

---

## 5. Observability Self-Check Checklist

- [ ] Business-critical nodes have INFO-level structured logs (with business ID)
- [ ] All `catch` blocks: exceptions either rethrown up or logged as ERROR (MUST NOT swallow exceptions)
- [ ] No plaintext sensitive fields in logs
- [ ] Cross-thread calls use MDC propagation wrapper, TraceId not lost
- [ ] New Controller APIs have audit log annotations added
- [ ] Critical business operations have counter/latency metrics reported
- [ ] MQ message send/receive has TraceId propagated
