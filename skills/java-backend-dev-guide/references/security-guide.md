# 安全规范

> **摘要**
>
> - **核心约束**：高敏感字段必须加密存储；ES 用 QueryBuilders 禁 script 查询；密钥走配置中心禁硬编码；涉及外部输入必须执行代码生成安全门（§7）
> - **关键阈值**：最高敏感级别字段必须加密、中等敏感级别必须加密、低级别无需加密
> - **常见违规**：日志打印明文敏感字段、.env 文件含真实密钥提交仓库、SQL 字符串拼接、外部 URL 未校验白名单（SSRF）

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 数据安全等级与加密要求

> 安全等级分类与加密要求由项目级 Skill 根据业务合规要求定义。以下为通用参考：

**【强制】最高安全级别的数据，在所有存储介质中必须加密存储。**

| 安全级别     | 典型字段                 | 加密要求   |
| ------------ | ------------------------ | ---------- |
| 最高（S4）   | 身份证号、银行卡号       | 必须加密   |
| 高（S3）     | 手机号                   | 必须加密   |
| 中（S2）     | 邮箱、地址               | 按需评估   |
| 低（S1）     | 昵称、头像 URL           | 无需加密   |

> 需求评审时未注明字段安全级别，将被退回补充。

---

## 2. 加密实现

| 存储介质                          | 加密方式                     | 业务层感知               |
| --------------------------------- | ---------------------------- | ------------------------ |
| MySQL                             | 框架拦截器自动加解密（推荐） | **无感知**，框架透明处理 |
| Redis / ES / MongoDB / HBase      | 应用层手动加密写入、解密读取 | **需业务层显式处理**     |

非 MySQL 存储的敏感字段，使用项目提供的加密工具类，禁止自行实现加解密算法。

---

## 3. 注入防护

### 3.1. SQL 注入

> #{} 参数绑定、禁止 ${}、禁止字符串拼接等规约遵循《阿里巴巴 Java 开发手册（黄山版）》§五 MySQL 数据库 — SQL 语句。

推荐使用 MyBatis-Plus LambdaQueryWrapper：

```java
LambdaQueryWrapper<ArticleDO> wrapper = Wrappers.lambdaQuery(ArticleDO.class)
        .eq(ArticleDO::getAuthorId, authorId);
```

### 3.2. ES 注入

```java
// ✅ 使用 QueryBuilders 构建查询
QueryBuilders.termQuery("authorId", authorId);

// ❌ 禁止用户输入直接拼入查询 JSON
// ❌ 禁止 script 查询（Script 执行任意代码）
```

### 3.3. MongoDB 注入

- 禁止 `$where` 执行 JS 表达式
- 用户输入必须经过类型校验，不得直接作为查询条件传入

---

## 4. 敏感信息输出防护

### 4.1. 日志脱敏

框架自动脱敏字段（如 `password`、`token` 等）由项目级 Skill 定义。

业务新增的敏感字段必须在审计日志注解或日志打印前手动脱敏：

```java
// ✅ 手动脱敏后打印
log.info("用户注册，手机号：{}", desensitize(phone));

// ❌ 禁止直接打印敏感字段
log.info("用户注册，手机号：{}", phone);
```

### 4.2. 接口响应

- 高敏感级别字段**不得**在接口响应中返回明文（如需展示，由前端脱敏渲染）
- 错误响应**不得**暴露内部堆栈、SQL、系统路径等实现细节

---

## 5. 配置安全

**【强制】** 所有数据源密码、密钥、Token 通过 `{ConfigManager}` 动态获取，禁止任何形式的硬编码：

```java
// ✅ 从配置中心获取
String password = {ConfigManager}.getConfig("db.password");

// ❌ 禁止硬编码
String password = "my_secret_password";
```

禁止将以下内容提交至代码仓库：

- 任何环境的数据库密码、Redis 密码
- AK / SK、API Token、私钥文件（`.pem`、`.key`）
- `.env` 文件中包含真实密钥的内容

---

## 6. 安全自检清单

编码完成后逐项确认：

- [ ] 高敏感字段已加密存储（MySQL 由框架处理，其他存储已手动加密）
- [ ] SQL 使用 `#{}` 绑定，无字符串拼接
- [ ] ES 查询使用 QueryBuilders，无 script 查询
- [ ] 日志中无敏感字段明文
- [ ] 接口响应中无敏感字段明文、无内部堆栈信息
- [ ] 无硬编码密钥、密码、Token
- [ ] 审计日志注解已声明所有新增敏感字段
- [ ] 涉及外部 HTTP 调用：目标 URL 已校验域名白名单
- [ ] 涉及文件上传：已校验 MIME 类型 + 文件大小 + 随机化存储路径

---

## 7. 代码生成安全门

> 凡涉及外部输入处理时，AI MUST 执行以下所有检查。

### 7.1. SQL 注入防护

- **MUST** 参数化查询（MyBatis `#{}`），**MUST NOT** 字符串拼接或 `${}`
- 推荐使用 MyBatis-Plus `LambdaQueryWrapper`

### 7.2. 文件路径安全

- **MUST** 调用路径合法性校验工具类，**MUST NOT** 直接拼接用户输入作为文件路径
- **MUST** 使用随机化文件名存储上传文件，**MUST NOT** 使用用户提供的原始文件名

### 7.3. 随机安全值

- **MUST** `SecureRandom`，**MUST NOT** `Math.random()` 或 `new Random()`

```java
// ✅ 安全随机数
SecureRandom random = new SecureRandom();
String token = Long.toHexString(random.nextLong());

// ❌ 不安全
String token = Long.toHexString((long)(Math.random() * Long.MAX_VALUE));
```

### 7.4. 反序列化安全

- **MUST** 校验类型白名单，**MUST NOT** 对不可信来源（HTTP 请求体、MQ 消息等）直接反序列化
- 使用 Jackson 时 **MUST NOT** 开启全局 `enableDefaultTyping`

### 7.5. 禁止硬编码内网地址

- **MUST NOT** 硬编码内网 IP / 域名 / 端口，所有地址通过 `{ConfigManager}` 或配置中心获取

### 7.6. SSRF 防护

- **MUST** 校验目标 URL 的域名白名单，**MUST NOT** 直接使用用户提供的 URL 发起内网请求
- **MUST** 禁止请求以下内网段：`169.254.0.0/16`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`

```java
// ✅ 校验域名白名单后再发起请求
private static final Set<String> ALLOWED_HOSTS = Set.of("api.example.com", "cdn.example.com");
if (!ALLOWED_HOSTS.contains(new URL(targetUrl).getHost())) {
    throw new {BizException}({ResultCode}.PARAM_INVALID);
}
```

### 7.7. 文件上传安全

- **MUST** 校验文件 MIME 类型（禁止仅校验扩展名，需读取文件头字节验证）
- **MUST** 限制单文件大小（通常 ≤ 100MB）
- **MUST** 使用随机化文件名（UUID）存储，**MUST NOT** 使用用户输入作为存储路径
