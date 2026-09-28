# 可观测性规范

> **摘要**
>
> - **核心约束**：业务关键操作 MUST 打结构化日志；新增接口 MUST 埋点耗时指标；异常 MUST 记录完整上下文（不吞异常）；链路追踪 TraceId MUST 透传至所有下游调用
> - **关键阈值**：日志级别 INFO 用于业务流程，WARN 用于可预期异常，ERROR 仅用于需人工介入场景；单条日志 MUST NOT 超过 1MB
> - **常见违规**：catch 后只打日志不抛出（吞异常）、日志无 TraceId 透传、打印敏感字段明文、用 System.out.println 替代日志框架

> **版本**：v1.0 | 最后更新：2026-06-08 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 日志规范

### 1.1. 日志级别使用

| 级别    | 使用场景                                             | 示例                            |
| ------- | ---------------------------------------------------- | ------------------------------- |
| `DEBUG` | 开发调试，生产禁止打印大对象                         | 方法入参、中间变量              |
| `INFO`  | 业务关键节点（请求进入、状态流转、异步任务触发）     | 文章发布成功、审核状态变更      |
| `WARN`  | 可预期的异常情况（参数不合法、业务规则不满足、重试） | 限流触发、熔断降级、幂等拦截    |
| `ERROR` | 需人工介入的故障（外部系统不可用、数据不一致、BUG）  | 数据库连接失败、MQ 消息处理异常 |

**MUST NOT** 使用 `System.out.println`；**MUST** 使用 `Slf4j` + `LoggerFactory`。

### 1.2. 日志内容规范

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

### 1.3. 敏感字段脱敏

日志中**MUST NOT**打印明文敏感字段，脱敏规则见 `security-guide.md §4`。

### 1.4. TraceId 透传

- Spring Boot 应用通常由 tracing 框架（如 Spring Cloud Sleuth / Micrometer Tracing）自动注入 TraceId 至 MDC，**无需手动设置**
- 跨线程（异步任务、线程池）时，**MUST** 使用框架提供的可透传 MDC 的线程池包装器传递上下文：

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

## 2. 指标埋点规范

### 2.1. 接口耗时埋点

新增 Controller 接口时，**MUST** 通过拦截器或 AOP 注解声明，框架自动采集接口耗时、QPS、错误率：

```java
@PostMapping("/publish")
@{AuditLogAnnotation}(bizType = "ARTICLE_PUBLISH", sanitizeKeys = {"content"})
public {ResponseWrapper}<ArticleVO> publish(@RequestBody PublishRequest request) { ... }
```

> 项目级 Skill 可定义具体的审计日志注解名称，默认使用 `{AuditLogAnnotation}` 占位。

### 2.2. 业务指标上报

关键业务操作（内容发布、审核通过/拒绝、支付等）**MUST** 上报业务指标：

```java
// 方式一：使用 Micrometer（Spring Boot 默认指标门面）
@Autowired
private MeterRegistry meterRegistry;

meterRegistry.counter("article.publish", "result", "success").increment();
meterRegistry.counter("article.publish", "result", "fail", "reason", resultCode.name()).increment();
meterRegistry.timer("article.publish.duration").record(cost, TimeUnit.MILLISECONDS);

// 方式二：使用项目自定义指标工具（由项目级 Skill 定义）
```

### 2.3. 告警阈值建议

| 指标类型      | 建议告警阈值                     |
| ------------- | -------------------------------- |
| 接口错误率    | > 1%（P1 告警）；> 5%（P0 告警） |
| 接口 P99 耗时 | 超出非功能需求 SLA 的 200%       |
| 业务失败率    | 与基准值偏差 > 50%               |

> 具体告警规则在监控平台配置，AI 负责确保埋点代码正确，**不负责**配置监控平台。

---

## 3. 链路追踪规范

### 3.1. RPC 透传

RPC 框架（Dubbo / gRPC / Spring Cloud OpenFeign 等）通常内置 TraceId 透传，无需额外配置。

### 3.2. 异步消息透传

发送 MQ 消息时，**MUST** 将 TraceId 写入消息 Header：

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

## 4. 健康检查

新增依赖外部系统（DB / Redis / ES / 第三方 HTTP 服务）的模块时，**MUST** 实现 `HealthIndicator`，确保服务健康状态可被监控探测：

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

## 5. 可观测性自检清单

- [ ] 业务关键节点已打 INFO 级结构化日志（含业务 ID）
- [ ] 所有 `catch` 块：异常已向上抛出或已打 ERROR 日志（MUST NOT 吞异常）
- [ ] 日志中无敏感字段明文
- [ ] 跨线程调用使用 MDC 透传包装器，TraceId 不丢失
- [ ] 新增 Controller 接口已添加审计日志注解
- [ ] 关键业务操作已上报计数/耗时指标
- [ ] MQ 消息收发已透传 TraceId
