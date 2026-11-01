# Concurrent Programming Standards

---

## 1. Thread Pool Standards

MUST use Spring `ThreadPoolTaskExecutor` or JDK `ThreadPoolExecutor`, configuration template:

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

## 2. CompletableFuture Standards

Async chains MUST specify a custom thread pool (prohibit ForkJoinPool.commonPool), MUST define exception fallback:

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

### 2.1. Multi-task Orchestration

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

### 2.2. Prohibited Behaviors

- **MUST NOT** use `ForkJoinPool.commonPool()`
- **MUST NOT** skip exception handling (at least one of `exceptionally` / `handle` / `whenComplete`)
- **MUST NOT** execute long-blocking operations in `CompletableFuture` chains
- **MUST NOT** `.join()` in Servlet threads to wait for async results (should use async Servlet or reactive return)

---

## 3. Distributed Lock Standards

### 3.1. Tool Selection

| Scenario | Recommended solution | Notes |
|----------|---------------------|-------|
| Cross-JVM process mutual exclusion | **Redisson** | Preferred, supports reentrant, watchdog auto-renewal, red lock |
| Single-JVM thread mutual exclusion | `synchronized` / `ReentrantLock` | Lightweight, no network overhead |

**MUST NOT** implement distributed locks yourself (lacks renewal and reentry mechanisms).

### 3.2. Redisson Coding Pattern

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

### 3.3. Prohibited Behaviors

- **MUST NOT** implement distributed locks yourself based on `SET NX EX`
- **MUST NOT** have lock hold time far exceed business execution time (wastes resources)
- **MUST NOT** forget to release locks in `finally`
- **MUST NOT** execute RPC / HTTP calls while holding distributed locks (lock granularity should be as small as possible)
