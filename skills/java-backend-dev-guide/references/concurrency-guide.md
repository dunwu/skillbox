# 并发编程规约

> **摘要**
>
> - **核心约束**：线程池 MUST 使用自定义 ThreadPoolTaskExecutor；CompletableFuture 异步链 MUST 指定自定义线程池 + 捕获异常；分布式锁 MUST 使用 Redisson 禁自行实现
> - **关键阈值**：有界队列容量 500-2000、锁超时 10-30s
> - **常见违规**：使用 Executors.newFixedThreadPool（无界队列导致 OOM）、CompletableFuture 忽略异常处理导致静默失败、自旋等待实现分布式锁

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 线程池规约

> 禁止 Executors 工厂方法、有界队列、参数公式等规约遵循《阿里巴巴 Java 开发手册（黄山版）》§一 编程规约 — 并发处理。

MUST 使用 Spring `ThreadPoolTaskExecutor` 或 JDK `ThreadPoolExecutor`，配置模板：

```java
@Configuration
public class ThreadPoolConfig {

    @Bean("bizExecutor")
    public ThreadPoolTaskExecutor bizExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(4);
        executor.setMaxPoolSize(8);
        executor.setQueueCapacity(1000);
        executor.setKeepAliveSeconds(60);
        executor.setThreadNamePrefix("biz-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }
}
```

---

## 2. CompletableFuture 规约

> 线程池指定、异常处理等通用规约遵循《阿里巴巴 Java 开发手册（黄山版）》§一 编程规约 — 并发处理。

异步链 MUST 指定自定义线程池（禁 ForkJoinPool.commonPool），MUST 定义异常兜底：

```java
@Async("bizExecutor")
public CompletableFuture<ArticleVO> getArticleAsync(Long articleId) {
    return CompletableFuture.supplyAsync(
        () -> articleRepository.findById(articleId).map(converter::toVO)
                .orElseThrow(() -> new {BizException}({ResultCode}.ARTICLE_NOT_FOUND)),
        bizExecutor
    ).exceptionally(ex -> {
        log.error("[getArticleAsync] 异步查询失败, articleId={}", articleId, ex);
        return null;
    });
}
```

### 2.1. 多任务编排

```java
// 并行执行多个独立任务，等待全部完成
CompletableFuture<ArticleVO> articleFuture = getArticleAsync(articleId);
CompletableFuture<AuthorVO> authorFuture = getAuthorAsync(authorId);
CompletableFuture.allOf(articleFuture, authorFuture).join();

// 任一成功即返回（适用于多源查询降级）
CompletableFuture<ArticleVO> result = CompletableFuture.anyOf(
    queryFromCache(articleId),
    queryFromDB(articleId),
    queryFromES(articleId)
).thenApply(obj -> (ArticleVO) obj);
```

### 2.2. 禁止行为

- **MUST NOT** 使用 `ForkJoinPool.commonPool()`（共享池线程数有限，高并发下阻塞）
- **MUST NOT** 不处理异常（`exceptionally` / `handle` / `whenComplete` 至少选一个）
- **MUST NOT** 在 `CompletableFuture` 链中执行长时间阻塞操作
- **MUST NOT** 在 Servlet 线程中 `.join()` 等待异步结果（应使用异步 Servlet 或响应式返回）

---

## 3. 分布式锁规约

### 3.1. 工具选择

| 场景              | 推荐方案                         | 说明                                   |
| ----------------- | -------------------------------- | -------------------------------------- |
| 跨 JVM 进程互斥   | **Redisson**                     | 首选，支持可重入、看门狗自动续期、红锁 |
| 单 JVM 内线程互斥 | `synchronized` / `ReentrantLock` | 轻量，无需网络开销                     |

**MUST NOT** 自行实现分布式锁（缺乏续期与重入机制）。

### 3.2. Redisson 编码模式

```java
public void deductStock(Long articleId, int count) {
    String lockKey = "stock:lock:" + articleId;
    RLock lock = redissonClient.getLock(lockKey);

    try {
        if (lock.tryLock(5, 10, TimeUnit.SECONDS)) {
            stockService.deduct(articleId, count);
        } else {
            throw new {BizException}({ResultCode}.STOCK_DEDUCT_BUSY);
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new {BizException}({ResultCode}.SYSTEM_ERROR);
    } finally {
        if (lock.isHeldByCurrentThread()) {
            lock.unlock();
        }
    }
}
```

### 3.3. 禁止行为

- **MUST NOT** 自行基于 `SET NX EX` 实现分布式锁（无看门狗续期、无重入检测）
- **MUST NOT** 锁的持有时间远大于业务执行时间（浪费资源）
- **MUST NOT** 忘记在 `finally` 中释放锁
- **MUST NOT** 在持有分布式锁期间执行 RPC / HTTP 调用（锁粒度应尽量小）
