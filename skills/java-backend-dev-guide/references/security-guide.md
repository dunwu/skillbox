# Security Standards

---

## 1. Data Security Levels and Encryption Requirements

> Security level classification and encryption requirements are defined by project-level Skill based on business compliance requirements. Below is a universal reference:

**[Mandatory]** Data at the highest security level must be encrypted in all storage media.

| Security level | Typical fields | Encryption requirement |
|---------------|---------------|----------------------|
| Highest (S4) | ID card numbers, bank card numbers | Must encrypt |
| High (S3) | Phone numbers | Must encrypt |
| Medium (S2) | Email, address | Evaluate as needed |
| Low (S1) | Nickname, avatar URL | No encryption needed |

> If a field's security level is not noted during requirement review, the requirement will be returned for supplementation.

---

## 2. Encryption Implementation

| Storage medium | Encryption method | Business layer awareness |
|---------------|------------------|------------------------|
| MySQL | Framework interceptor auto encrypt/decrypt (recommended) | **Unaware**, framework handles transparently |
| Redis / ES / MongoDB / HBase | Application layer manual encrypt on write, decrypt on read | **Requires explicit handling by business layer** |

For sensitive fields in non-MySQL storage, use project-provided encryption utility classes, prohibit self-implementing encryption/decryption algorithms.

---

## 3. Injection Prevention

### 3.1. SQL Injection

Recommend using MyBatis-Plus LambdaQueryWrapper:

```java
LambdaQueryWrapper<ArticleDO> wrapper = Wrappers.lambdaQuery(ArticleDO.class)
        .eq(ArticleDO::getAuthorId, authorId);
```

### 3.2. ES Injection

```java
// ✅ 使用 QueryBuilders 构建查询
QueryBuilders.termQuery("authorId", authorId);

// ❌ 禁止用户输入直接拼入查询 JSON
// ❌ 禁止 script 查询
```

### 3.3. MongoDB Injection

- Prohibit `$where` executing JS expressions
- User input must undergo type validation, must not be directly passed as query conditions

---

## 4. Sensitive Information Output Protection

### 4.1. Log Masking

Framework auto-masks fields (such as `password`, `token` etc.) as defined by project-level Skill.

New sensitive fields added by business must be manually masked in audit log annotations or before log printing:

```java
// ✅ 手动脱敏后打印
log.info("用户注册，手机号：{}", mask(phone));

// ❌ 禁止直接打印敏感字段
log.info("用户注册，手机号：{}", phone);
```

### 4.2. API Responses

- High-sensitivity level fields **must not** return plaintext in API responses (if display needed, frontend renders with masking)
- Error responses **must not** expose internal stack traces, SQL, system paths, and other implementation details

---

## 5. Configuration Security

**[Mandatory]** All data source passwords, keys, Tokens obtained dynamically through `{ConfigManager}`, prohibit hardcoding in any form:

```java
// ✅ 从配置中心获取
String password = {ConfigManager}.getConfig("db.password");

// ❌ 禁止硬编码
String password = "my_secret_password";
```

Prohibit committing the following to code repository:

- Database passwords, Redis passwords for any environment
- AK / SK, API Tokens, private key files (`.pem`, `.key`)
- `.env` files containing real keys

---

## 6. Security Self-Check Checklist

Confirm item by item after coding is complete:

- [ ] High-sensitivity fields encrypted for storage (MySQL handled by framework, other storage manually encrypted)
- [ ] SQL uses `#{}` parameter binding, no string concatenation
- [ ] ES queries use QueryBuilders, no script queries
- [ ] No plaintext sensitive fields in logs
- [ ] No plaintext sensitive fields in API responses, no internal stack trace information
- [ ] No hardcoded keys, passwords, Tokens
- [ ] Audit log annotations declare all new sensitive fields
- [ ] Involving external HTTP calls: target URL validated against domain whitelist
- [ ] Involving file uploads: MIME type validated + file size limited + randomized storage path

---

## 7. Code Generation Security Gate

> Whenever external input is handled, AI MUST execute all of the following checks.

### 7.1. SQL Injection Prevention

- **MUST** parameterized queries (MyBatis `#{}`), **MUST NOT** string concatenation or `${}`
- Recommend using MyBatis-Plus `LambdaQueryWrapper`

### 7.2. File Path Security

- **MUST** call path validity validation utility class, **MUST NOT** directly concatenate user input as file path
- **MUST** use randomized file names for uploaded file storage, **MUST NOT** use user-provided original file names

### 7.3. Random Security Values

- **MUST** `SecureRandom`, **MUST NOT** `Math.random()` or `new Random()`

```java
// ✅ 安全随机数
SecureRandom random = new SecureRandom();
String token = Long.toHexString(random.nextLong());

// ❌ 不安全
String token = Long.toHexString((long)(Math.random() * Long.MAX_VALUE));
```

### 7.4. Deserialization Security

- **MUST** validate type whitelist, **MUST NOT** directly deserialize from untrusted sources (HTTP request body, MQ messages, etc.)
- When using Jackson, **MUST NOT** enable global `enableDefaultTyping`

### 7.5. Prohibit Hardcoding Intranet Addresses

- **MUST NOT** hardcode intranet IP / domain names / ports, all addresses obtained through `{ConfigManager}` or config center

### 7.6. SSRF Prevention

- **MUST** validate target URL domain whitelist, **MUST NOT** directly use user-provided URLs to make intranet requests
- **MUST** prohibit requesting the following intranet segments: `169.254.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`

```java
// ✅ 校验域名白名单后再发起请求
private static final Set<String> ALLOWED_HOSTS = Set.of("api.example.com", "cdn.example.com");
if (!ALLOWED_HOSTS.contains(new URL(targetUrl).getHost())) {
    throw new {BizException}({ResultCode}.PARAM_INVALID);
}
```

### 7.7. File Upload Security

- **MUST** validate file MIME type (prohibit only validating extension, must read file header bytes to verify)
- **MUST** limit single file size (typically ≤ 100MB)
- **MUST** use randomized file names (UUID) for storage, **MUST NOT** use user input as storage path
