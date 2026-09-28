# Redis 整合开发规约

> **摘要**
>
> - **核心约束**：Key 格式 {模块}:{对象}:{标识} 必须设 TTL；禁 BigKey（String>10KB / 集合>5000 元素）；缓存更新先更库再删缓存；生产禁 KEYS 命令
> - **关键阈值**：单实例内存 ≤32GB（物理内存 70-80%）、Pipeline 批量 ≤500、HGETALL 仅限字段数 <100
> - **常见违规**：不设 TTL 导致内存膨胀、HGETALL 大 Hash 阻塞 Redis、Lua 脚本/Pipeline 跨节点、缓存与 DB 不一致

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

> 若存在冲突，以《Redis 开发规约》为准。

---

## 1. 通用开发规约

### 1.1. 键值规约

#### 1.1.1. 【强制】Key 命名规约

Key 命名遵循 `{业务模块}:{对象类型}:{唯一标识}[:{附加维度}]`，使用冒号 `:` 分隔。

示例：`article:detail:12345`、`author:info:67890`

#### 1.1.2. 【强制】禁止使用 BigKey

String 类型 Value >10KB 或 Hash/List/Set/ZSet 集合元素 >5000 即视为 BigKey。Value >1MB 应压缩或拆分。

#### 1.1.3. 【强制】Key 必须设置过期时间

除持久化存储场景外，所有缓存 Key 必须设置 TTL。要求长期有效的 Key 采用「每次访问顺延过期时间」策略。

#### 1.1.4. 【推荐】选择合适的数据结构

| 数据结构      | 适用场景                  |
| ------------- | ------------------------- |
| `String`      | 普通 KV、计数器、分布式锁 |
| `Hash`        | 存储对象属性，字段数 ≤100 |
| `List`        | 消息队列、最新列表        |
| `Set`         | 去重、交集/并集运算       |
| `ZSet`        | 排行榜、延时队列          |
| `Bitmap`      | 统计、用户签到            |
| `HyperLogLog` | 去重计数                  |

> `HGETALL`、`SMEMBERS` 时间复杂度 O(N)，Hash 字段 >100 时需拆分或改用 String 序列化存储。

---

### 1.2. 缓存规约

#### 1.2.1. 【强制】数据同步采用 Cache Aside Pattern

更新数据时先更新数据库，成功后再删除缓存。禁止「先删缓存再更库」或「双写」模式。

对一致性要求极高的场景，使用 Canal 监听 Binlog 异步删除缓存或采用分布式锁。

#### 1.2.2. 【推荐】缓存雪崩治理

1. 过期时间随机化：TTL 增加随机抖动（1%-5%）
2. 多级缓存：本地缓存 + Redis 两级结构
3. 熔断降级：缓存集群不可用时降级到数据库直查

#### 1.2.3. 【推荐】缓存穿透治理

1. 缓存空值/默认值：查询不到的结果设短 TTL（如 5 分钟）
2. 布隆过滤器：访问缓存前预先判断 Key 是否可能存在

#### 1.2.4. 【推荐】缓存击穿治理

1. 互斥锁（Mutex Lock）：缓存未命中时用分布式锁确保单线程加载
2. 逻辑过期：缓存数据时存储逻辑过期时间，过期后异步更新

#### 1.2.5. 【推荐】热点 Key 治理

- 本地缓存（Guava/Caffeine）+ Redis 多级缓存
- 热点 Key 拆分（如 `key_1`, `key_2`）
- 优化数据类型（排行榜改用 String+incr）

---

### 1.3. 命令规约

#### 1.3.1. 【强制】禁止线上使用 KEYS 命令

`KEYS *` 时间复杂度 O(N) 会阻塞 Redis 单线程。使用 `SCAN` 命令渐进式遍历，建议在从库执行。

#### 1.3.2. 【强制】谨慎使用全量获取命令

禁止对大型集合使用 `HGETALL`、`SMEMBERS`、`LRANGE 0 -1`。使用 `HSCAN`、`SSCAN` 分页获取。

#### 1.3.3. 【推荐】优先使用 Lua 脚本保证原子性

涉及多步逻辑（如判断+更新）时优先使用 Lua 脚本。Cluster 模式下所有 Key 必须通过 Hashtag `{}` 映射到同一分片。

#### 1.3.4. 【推荐】Pipeline 批量操作优化

优先使用 `MGET`、`MSET`、`HMGET` 等批量命令或 Pipeline。批量 Key 数 ≤500。Cluster 模式下 Pipeline 涉及多个分片时无法保证原子性，应拆分为单一分片的 Pipeline。

#### 1.3.5. 【强制】谨慎使用 Redis 事务

尽量避免 `MULTI/EXEC`。Redis 事务不支持回滚；Cluster 下 Key 分布不同分片时事务无法执行；高并发场景用 Lua 脚本替代。

---

### 1.4. 客户端规约

#### 1.4.1. 【强制】合理配置连接池参数

根据业务 QPS 配置 `maxTotal`、`maxIdle`、`minIdle`、`maxWaitMillis`。`maxTotal` 参考公式：`(QPS × 平均响应时间) / 1000 + 缓冲`。读取超时建议 2s-5s。

#### 1.4.2. 【推荐】谨慎使用 Hashtag

除非有跨 Key 原子操作需求，禁止人为使用 `{}` 构造 Hashtag。Hashtag 导致数据倾斜和热点分片。

#### 1.4.3. 【推荐】Cluster 重试机制配置

`maxRedirections` 默认 5 次即可。频繁出现重定向异常应排查集群稳定性而非增加重试。

---

### 1.5. 架构规约

#### 1.5.1. 【强制】单机内存限制

Redis 单实例最大内存不超过物理内存的 70%-80%，不建议超过 32GB。必须设置 `maxmemory` 和 `maxmemory-policy`。内存过大导致 RDB/AOF 重写 fork 耗时过长，主从同步时间线性增长。

#### 1.5.2. 【强制】冷热数据分离

仅将高频访问的热数据（QPS > 5000）存入 Redis，冷数据存 MySQL/ES/MongoDB。

#### 1.5.3. 【强制】业务隔离

不同业务数据存入独立 Redis 集群，避免相互影响。

#### 1.5.4. 【推荐】数据压缩存储

超过 500 Byte 的文本数据在应用端压缩（GZIP/Snappy/LZ4）后存入 Redis。

#### 1.5.5. 【推荐】合理选择内存淘汰策略

生产环境必须配置 `maxmemory-policy`，不推荐 `noeviction`。常用：`allkeys-lru`（混合读写）、`volatile-lru`（仅淘汰有 TTL 的 Key）、`volatile-ttl`（优先淘汰即将过期）、`allkeys-lfu`（Redis ≥4.0）。

---

### 1.6. 高可用规约

#### 1.6.1. 【强制】禁止使用 FLUSHALL/FLUSHDB

严禁生产环境执行清空数据库命令。

#### 1.6.2. 【推荐】关键操作增加异常处理

核心业务数据写入必须捕获 Redis 客户端异常并进行重试或降级。

#### 1.6.3. 【推荐】可靠消息队列实现

使用 Redis List 做消息队列时配合 `RPOPLPUSH` 实现消费确认。生产环境消息队列建议使用 RocketMQ/Kafka。

#### 1.6.4. 【推荐】数据备份与恢复

- 缓存场景可只开启 RDB
- 持久化数据场景 RDB 与 AOF 同时开启
- 混合持久化（Redis ≥4.0）：`aof-use-rdb-preamble yes`
- 每日至少一次快照备份

#### 1.6.5. 【推荐】集群部署与节点监控

生产实例必须选择主备或集群实例。Redis Cluster 数据分片到多个节点，每个 Key 映射到 16384 个哈希槽之一。必须监控内存使用率、连接数、淘汰键数量、慢查询日志。

---

## 2. 工程化规约（Redisson + Spring Data Redis）

> **[FOR HUMAN REFERENCE]** 以下内容为工程化配置说明，AI 编码时通常无需加载。
>
> 本节基于 **Redisson + Spring Data Redis** 标准用法编写。项目级 Skill 可覆盖为项目自定义封装。

### 2.1. 快速上手

#### 2.1.1. 添加依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson-spring-boot-starter</artifactId>
</dependency>
```

#### 2.1.2. 配置

```yaml
spring:
  redis:
    cluster:
      nodes: ${REDIS_CLUSTER_NODES}
    timeout: 2000
    lettuce:
      pool:
        max-active: 20
        max-idle: 4
        max-wait: 1000
        min-idle: 2
```

```java
// 缓存操作 → RedisTemplate / StringRedisTemplate
@Autowired
private StringRedisTemplate redisTemplate;

// 分布式锁 → RedissonClient
@Autowired
private RedissonClient redissonClient;
```

---

### 2.2. Key 命名规范

```
{业务模块}:{对象类型}:{唯一标识}[:{附加维度}]
```

示例：`article:detail:12345`、`author:info:67890`、`rate:limit:api:/v1/upload`、`lock:article:publish:12345`

```
✅ 命名见名知意
✅ 必须以业务模块名作为第一层前缀
✅ 所有 Key 必须设置 TTL
✅ Value ≤ 10KB（避免 bigkey）
✅ 大文本建议应用层压缩（Gzip/LZ4）
❌ 禁止含义不清的 Key 命名
❌ 禁止使用 hashtag（数据倾斜 + 热点）
❌ 禁止中文或特殊字符
```

---

### 2.3. 基础操作示例

#### 2.3.1. 缓存读写

```java
public ArticleDTO getArticleWithCache(Long articleId) {
    String key = "article:detail:" + articleId;
    String cached = redisTemplate.opsForValue().get(key);
    if (StringUtils.isNotBlank(cached)) {
        return JsonUtil.parseObject(cached, ArticleDTO.class);
    }
    ArticleDTO dto = articleRepository.findById(articleId);
    if (dto != null) {
        redisTemplate.opsForValue().set(key, JsonUtil.toJsonString(dto),
            Duration.ofSeconds(1800));
    }
    return dto;
}
```

#### 2.3.2. 计数器

```java
public void incrViewCount(Long articleId) {
    String key = "article:view:" + articleId;
    redisTemplate.opsForValue().increment(key);
    Long ttl = redisTemplate.getExpire(key);
    if (ttl == null || ttl == -1) {
        redisTemplate.expire(key, Duration.ofSeconds(86400));
    }
}
```

---

### 2.4. 分布式锁规范

**必须使用 Redisson `RLock`，禁止手写 SETNX 实现锁。**

```java
public void publishArticle(Long articleId) {
    String lockKey = "lock:article:publish:" + articleId;
    RLock lock = redissonClient.getLock(lockKey);
    boolean acquired = false;
    try {
        acquired = lock.tryLock(3, 10, TimeUnit.SECONDS);
        if (!acquired) {
            throw new {BizException}({ResultCode}.ARTICLE_PUBLISH_BUSY);
        }
        doPublish(articleId);
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new {BizException}({ResultCode}.SYSTEM_ERROR);
    } finally {
        if (acquired && lock.isHeldByCurrentThread()) {
            lock.unlock();
        }
    }
}
```

```
✅ finally 块中释放锁
✅ 释放前检查 lock.isHeldByCurrentThread()
✅ 设置合理持有时间（leaseTime）
✅ 使用 tryLock 而非 lock
✅ 锁内避免耗时 IO
❌ 禁止 SETNX 手写分布式锁
```

---

### 2.5. Pipeline 批量操作

```java
public Map<Long, String> batchGetArticles(List<Long> articleIds) {
    List<Object> results = redisTemplate.executePipelined(
        (RedisCallback<String>) connection -> {
            StringRedisConnection stringConn = (StringRedisConnection) connection;
            for (Long id : articleIds) {
                stringConn.get("article:detail:" + id);
            }
            return null;
        }
    );
    Map<Long, String> result = new HashMap<>(articleIds.size());
    for (int i = 0; i < articleIds.size(); i++) {
        if (results.get(i) != null) {
            result.put(articleIds.get(i), (String) results.get(i));
        }
    }
    return result;
}
```

Pipeline 适用：一次业务操作需执行 ≥5 个独立 Redis 命令。

---

### 2.6. 原子操作

```java
public boolean isRateLimited(String userId) {
    String key = "rate:limit:user:" + userId;
    String luaScript =
        "local count = redis.call('incr', KEYS[1]) " +
        "if count == 1 then " +
        "  redis.call('expire', KEYS[1], 60) " +
        "end " +
        "return count";
    Long count = redisTemplate.execute(
        new DefaultRedisScript<>(luaScript, Long.class),
        Collections.singletonList(key));
    return count != null && count > 100;
}
```

---

### 2.7. 缓存问题防护

#### 2.7.1. 缓存穿透

```java
if (dto == null) {
    redisTemplate.opsForValue().set(key, "NULL", Duration.ofSeconds(60));
    return null;
}
```

#### 2.7.2. 缓存击穿

```java
RLock lock = redissonClient.getLock("lock:rebuild:article:" + articleId);
try {
    lock.lock(5, TimeUnit.SECONDS);
    String cached = redisTemplate.opsForValue().get(key);
    if (StringUtils.isNotBlank(cached)) {
        return deserialize(cached);
    }
    ArticleDTO dto = articleRepository.findById(articleId);
    redisTemplate.opsForValue().set(key, serialize(dto), Duration.ofSeconds(1800));
    return dto;
} finally {
    if (lock.isHeldByCurrentThread()) lock.unlock();
}
```

#### 2.7.3. 缓存雪崩

```java
int ttl = 1800 + ThreadLocalRandom.current().nextInt(300);
redisTemplate.opsForValue().set(key, value, Duration.ofSeconds(ttl));
```

---

### 2.8. 开发 Checklist 与反模式

#### Checklist

- [ ] Key 命名遵循 `{业务模块}:{对象类型}:{唯一标识}` 格式
- [ ] 所有 Key 设置了 TTL
- [ ] 大文本存储时评估是否需要应用层压缩
- [ ] 单 Value ≤ 10KB
- [ ] 未使用 hashtag
- [ ] 分布式锁使用 Redisson RLock，finally 块中释放
- [ ] 批量操作使用 Pipeline
- [ ] 多命令原子操作使用 Lua 脚本
- [ ] 缓存穿透、击穿、雪崩场景已考虑

#### 常见反模式（禁止）

```
❌ 永久 Key（无 TTL）
❌ 生产环境使用 KEYS 命令
❌ 超大文本不压缩直接存储
❌ bigkey（单 Value 超过 10KB）
❌ 使用 hashtag（数据倾斜 + 热点）
❌ HGETALL/SMEMBERS 操作大 Hash/Set
❌ 手写 SETNX 分布式锁
❌ for 循环逐个调用 Redis（使用 Pipeline）
❌ 多命令原子操作不使用 Lua
❌ 锁未在 finally 块中释放
❌ 硬编码集群地址
```

---

## 参考资料

- Redis 官方文档
- 《Redis 实战》
- 《Redis 设计与实现》
