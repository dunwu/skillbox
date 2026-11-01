# Middleware Development Standards

---

## 1. Dubbo RPC

### 1.1. Service Provider

```java
// api 模块：声明接口
public interface AuthorService {
    {ResponseWrapper}<AuthorVO> getById(Long authorId);
}

// server 模块：实现
@DubboService(version = "${dubbo.service.version}", group = "${dubbo.service.group}")
public class AuthorServiceImpl implements AuthorService {
    // ...
}
```

### 1.2. Service Consumer

```java
// @DubboReference 是 Dubbo 框架特例，允许字段注入
@DubboReference(version = "${dubbo.reference.version}", group = "${dubbo.reference.group}")
private AuthorService authorService;
```

> Standard Spring Beans must still use constructor injection; `@DubboReference` is the sole exception allowing field injection.

### 1.3. Prohibited Behaviors

- **MUST NOT** initiate Dubbo calls inside transactions
- **MUST NOT** directly depend on Dubbo interfaces in DomainService layer (should adapt through `infrastructure/gateway/` anti-corruption layer)
- **MUST NOT** pass Dubbo DTOs directly into Domain layer (must convert to BO / Command)

---

## 2. RabbitMQ Messages

### 2.1. Producer

```java
@Component
public class ArticleEventPublisher {

    private final RabbitTemplate rabbitTemplate;

    public ArticleEventPublisher(RabbitTemplate rabbitTemplate) {
        this.rabbitTemplate = rabbitTemplate;
    }

    public void publishCreated(ArticleCreatedEvent event) {
        rabbitTemplate.convertAndSend(
            ArticleMqConstants.EXCHANGE,
            ArticleMqConstants.ROUTING_KEY_CREATED,
            event
        );
    }
}
```

> **MUST NOT** send MQ inside transactions. Should send after transaction commits, or adopt transactional message solution.

### 2.2. Consumer

```java
@Component
@RabbitListener(queues = ArticleMqConstants.QUEUE_CREATED)
public class ArticleCreatedConsumer {

    @RabbitHandler
    public void handle(ArticleCreatedEvent event, Channel channel, Message message)
            throws IOException {
        try {
            articleApplicationService.onCreated(event);
            channel.basicAck(message.getMessageProperties().getDeliveryTag(), false);
        } catch (Exception e) {
            channel.basicNack(message.getMessageProperties().getDeliveryTag(), false, false);
            log.error("[ArticleCreatedConsumer] 处理失败，已投递死信队列", e);
        }
    }
}
```

### 2.3. Key Principles

- **Consumers must implement idempotency** (messages may be delivered repeatedly, deduplicate by message unique key)
- Dead letter queue (DLQ) must be configured and connected to monitoring alerts
- **MUST NOT** nest database transactions in consumers then send MQ

---

## 3. Scheduled Tasks

> The specific integration approach of the scheduled-task framework is defined by the project-level Skill (e.g. Spring @Scheduled, XXL-Job, etc.).

### 3.1. Task Implementation Principles

```java
@Scheduled(cron = "0 0 2 * * ?")
public void processExpired() {
    try {
        articleApplicationService.processExpired();
    } catch (Exception e) {
        log.error("[ArticleExpireJob] 执行失败", e);
        // 根据框架决定是否重试或标记失败
    }
}
```

### 3.2. Prohibited Behaviors

- **MUST NOT** let a single execution exceed 30s (should process in batches, each batch with pagination cursor)
- **MUST NOT** ignore exceptions (must catch and log, decide whether to retry based on framework)
- **MUST NOT** perform a full table scan inside a task (must have `WHERE` filter conditions + cursor-based batching)

---

## 4. Logging Standards

> For security masking, see → security-guide.md §4. Key operation entry/exit points in coding MUST have logs (see → observability-guide.md §1).

### 4.1. Usage Standards

```java
// MUST：Lombok @Slf4j，禁止 System.out.println
@Slf4j
@Service
public class ArticleApplicationService {

    public {ResponseWrapper}<ArticleVO> create(CreateArticleCMD cmd) {
        log.info("[ArticleApplicationService#create] authorId={}", cmd.getAuthorId());
        // ...
    }
}
```

### 4.2. Log Levels and Prohibited Behaviors

- **MUST NOT** log plaintext passwords, Tokens, ID card numbers, and other sensitive data
- **MUST NOT** log `INFO` level inside `for` loops
- **MUST NOT** use `e.printStackTrace()` (alternative: `log.error("description", e)`)

---

## 5. MyBatis-Plus ORM

> This section only covers ORM basic configuration. For complete MySQL standards, see → mysql-guide.md.

### 5.1. Mapper XML Path Convention

```yaml
mybatis-plus:
  mapper-locations: classpath*:mapper/**/*.xml
```

### 5.2. Paginated Queries

```java
Page<ArticleDO> page = new Page<>(pageIndex, pageSize);
IPage<ArticleDO> result = articleMapper.selectPage(page, queryWrapper);
```

### 5.3. Prohibited Behaviors

- **MUST NOT** use `${xxx}` string concatenation in Mapper XML (SQL injection, must use `#{xxx}`)
- **MUST NOT** write business logic in Mapper / DAO layer
- **MUST NOT** execute `UPDATE` / `DELETE` without `WHERE` conditions
- **MUST NOT** execute `SELECT *` on large tables

> For complete MySQL standards, see → mysql-guide.md.

---

## 6. Circuit Breaker Degradation Standards

> The circuit breaker degradation framework is defined by the project-level Skill (e.g. Sentinel, Resilience4j, etc.). Below is a Sentinel pattern example.

### 6.1. Core Principles

- **MUST NOT** hardcode circuit breaker degradation logic in business code, **MUST** configure dynamically through rules
- **MUST** configure degradation fallback strategies for all external dependencies (RPC, HTTP, Redis, ES)
- **MUST** configure rate limiting rules for core APIs to prevent downstream failures from causing cascading avalanches

### 6.2. Degradation Coding Pattern

```java
@SentinelResource(value = "getArticle", fallback = "getArticleFallback")
public ArticleVO getArticle(Long articleId) {
    return articleRepository.findById(articleId)
            .map(converter::toVO)
            .orElseThrow(() -> new {BizException}({ResultCode}.ARTICLE_NOT_FOUND));
}

// fallback 方法签名必须与原方法一致，参数多加 BlockException
public ArticleVO getArticleFallback(Long articleId, BlockException ex) {
    log.warn("[getArticle] 触发降级, articleId={}, rule={}", articleId, ex.getRule());
    return articleCacheService.getCached(articleId); // 返回兜底数据，MUST NOT 返回 null
}
```

### 6.3. Prohibited Behaviors

- **MUST NOT** have fallback method return `null` (callers will get NPE)
- **MUST NOT** initiate calls inside fallback that could trigger circuit breaking again
- **MUST NOT** ignore BlockException
