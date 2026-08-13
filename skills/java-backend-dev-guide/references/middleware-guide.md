# 中间件开发规范

> **摘要**
>
> - **核心约束**：Dubbo 禁事务内调用、Domain 层禁直接依赖 Dubbo 接口（经 gateway 防腐）；RabbitMQ 消费者必须幂等 + 死信队列、禁事务内发 MQ；定时任务禁超 30s + 禁全表扫描 + 禁忽略异常
> - **关键阈值**：定时任务单次 ≤30s
> - **常见违规**：事务内发 MQ 导致消息不一致、消费者未实现幂等、定时任务全表 Scan 无 WHERE

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. Dubbo RPC

### 1.1. 服务提供方

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

### 1.2. 服务消费方

```java
// @DubboReference 是 Dubbo 框架特例，允许字段注入
@DubboReference(version = "${dubbo.reference.version}", group = "${dubbo.reference.group}")
private AuthorService authorService;
```

> 常规 Spring Bean 仍须使用构造器注入；`@DubboReference` 是唯一允许字段注入的例外。

### 1.3. 禁止行为

- **MUST NOT** 在事务内发起 Dubbo 调用（事务回滚但 RPC 已执行）
- **MUST NOT** 在 DomainService 层直接依赖 Dubbo 接口（应通过 `infrastructure/gateway/` 防腐层适配）
- **MUST NOT** 将 Dubbo DTO 直接传入 Domain 层（需转换为 BO / Command）

---

## 2. RabbitMQ 消息

### 2.1. 生产者

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

> **MUST NOT** 在事务内发送 MQ（事务回滚但消息已发出，造成数据不一致）。应在事务提交后发送，或采用事务消息方案。

### 2.2. 消费者

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

### 2.3. 关键原则

- **消费者必须实现幂等**（消息可能重复投递，以消息唯一键做去重）
- 死信队列（DLQ）必须配置并接入监控告警
- **MUST NOT** 在消费者中嵌套数据库事务后再发 MQ

---

## 3. 定时任务

> 定时任务框架由项目级 Skill 定义具体集成方式（如 Spring @Scheduled、XXL-Job 等）。

### 3.1. 任务实现原则

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

### 3.2. 禁止行为

- **MUST NOT** 单次执行超过 30s（应分批处理，每批加分页游标）
- **MUST NOT** 忽略异常（必须捕获并记录，根据框架决定是否重试）
- **MUST NOT** 在任务内做全表扫描（必须有 `WHERE` 过滤条件 + 游标分批）

---

## 4. 日志规范

> 安全脱敏见 → security-guide.md §4。编码中关键操作入口/出口 MUST 有日志（见 → java-guide.md §9）。

### 4.1. 使用规范

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

### 4.2. 日志级别与禁止行为

> 日志级别（ERROR/WARN/INFO/DEBUG）语义遵循《阿里巴巴 Java 开发手册（黄山版）》§2 异常日志。

- **MUST NOT** 日志记录明文密码、Token、身份证号等敏感数据
- **MUST NOT** 在 `for` 循环内打 `INFO` 日志
- **MUST NOT** 使用 `e.printStackTrace()`（替代：`log.error("描述", e)`）

---

## 5. MyBatis-Plus ORM

> 本节仅涵盖 ORM 基础配置。MySQL 完整规范见 → mysql-guide.md。

### 5.1. Mapper XML 路径约定

```yaml
mybatis-plus:
  mapper-locations: classpath*:mapper/**/*.xml
```

### 5.2. 分页查询

```java
Page<ArticleDO> page = new Page<>(pageIndex, pageSize);
IPage<ArticleDO> result = articleMapper.selectPage(page, queryWrapper);
```

### 5.3. 禁止行为

- **MUST NOT** Mapper XML 中使用 `${xxx}` 字符串拼接（SQL 注入，必须用 `#{xxx}`）
- **MUST NOT** 在 Mapper / DAO 层写业务逻辑
- **MUST NOT** 执行无 `WHERE` 条件的 `UPDATE` / `DELETE`
- **MUST NOT** 对大表执行 `SELECT *`

> MySQL 完整规范见 → mysql-guide.md。

---

## 6. 熔断降级规范

> 熔断降级框架由项目级 Skill 定义（如 Sentinel、Resilience4j 等）。以下为 Sentinel 模式示例。

### 6.1. 核心原则

- **MUST NOT** 将熔断降级逻辑硬编码在业务代码中，**MUST** 通过规则动态配置
- **MUST** 为所有外部依赖（RPC、HTTP、Redis、ES）配置降级兜底策略
- **MUST** 为核心接口配置限流规则，防止下游故障引发级联雪崩

### 6.2. 降级编码模式

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

### 6.3. 禁止行为

- **MUST NOT** fallback 方法返回 `null`（调用方会 NPE）
- **MUST NOT** 在 fallback 中再次发起可能触发熔断的调用
- **MUST NOT** 忽略 BlockException
