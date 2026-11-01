# Code Review Standards

---

## 1. Trigger Timing

| Scenario | Operation |
|----------|-----------|
| Coding complete, ready to submit PR | Load `requesting-code-review` Skill, trigger AI-assisted Review |
| Received Review feedback, ready to modify | Load `receiving-code-review` Skill, process comments item by item |
| PR passed, ready to merge | Confirm all `MUST-FIX` items fixed, gates passed (→ quality-gate.md) |

**MUST NOT** merge changes involving public contracts, storage Schema, or security-related changes without Code Review.

---

## 2. AI Auto-Check Items

Before submitting Review, AI **MUST** complete the following checks and attach output results:

### 2.1. Architecture Compliance

- [ ] Call chain direction correct (Controller → ApplicationService → DomainService → Repository, no cross-layer calls)
- [ ] ApplicationService / DomainService layers do not directly depend on DAO classes (through Repository interface for anti-corruption)
- [ ] Controller does not expose DO (converted to VO / DTO)
- [ ] No circular dependencies, no cross-storage module direct dependencies

### 2.2. Coding Standards

- [ ] Naming suffixes conform to standards (DO / DTO / VO / CMD / QRY / Dao / Repository)
- [ ] Object conversion uses MapStruct, no `BeanUtils.copyProperties`
- [ ] Converters use `@Mapper` + `INSTANCE` pattern, no `@Mapper(componentModel = "spring")` (→ java-guide.md §6)
- [ ] Unit tests do not `@Mock` Converters, use real `INSTANCE` (→ java-guide.md §6.2)
- [ ] Responses uniformly use `{ResponseWrapper}<T>` / `{PageResponse}<T>` / `{ScrollResponse}<T>`
- [ ] Error code naming conforms to `{DOMAIN}_{ACTION_RESULT}` format, all uppercase (→ java-guide.md §3)
- [ ] General coding conventions (method line count, JavaDoc, dependency injection, layer responsibilities) conform to team standards (→ java-guide.md)

### 2.3. Exception Transactions

- [ ] No silent exception swallowing after `catch`
- [ ] Exceptions use `{BizException}({ResultCode}.XXX)`, do not throw raw `RuntimeException`
- [ ] `@Transactional` only on Service methods, no RPC / HTTP calls inside transactions
- [ ] No large transactions (non-core logic moved out of transactions)

### 2.4. Security

- [ ] No plaintext keys, Tokens, passwords in source code / configuration / logs
- [ ] Sensitive fields encrypted for storage (→ security-guide.md §1)
- [ ] SQL uses `#{}` parameter binding, no string concatenation

### 2.5. Testing

- [ ] Core branches have corresponding unit tests
- [ ] No commented-out assertions or `@Disabled` tests
- [ ] Mock granularity reasonable (not over-mocked, ApplicationService / DomainService layers must have real logic tests)

---

## 3. Manual Review Must-Check Items

The following dimensions require human judgment, AI checks are for reference only:

| Dimension | Check points |
|-----------|-------------|
| Business logic correctness | Whether the implementation matches `spec.md` acceptance criteria item by item |
| Boundary and exception scenarios | Whether scenarios such as empty input, concurrency, exceeding limits, and third-party timeouts are handled |
| Data consistency | Whether multi-storage writes have a transaction or compensation mechanism; whether cache and DB may become inconsistent |
| Performance risks | N+1 queries, IO in loops, large object serialization, unindexed large table scans |
| Observability | Whether critical operations have logs; whether exceptions are traceable; whether metrics are reported |
| Maintainability | Whether magic numbers are extracted as constants; whether complex logic has comments explaining intent |

---

## 4. Review Comment Format

All Review comments use unified format for traceability:

```
[severity] 文件路径:行号
原因：{为什么有问题}
建议：{如何修改}
```

**Severity Definitions:**

| Level | Meaning | Handling requirement |
|-------|---------|---------------------|
| `MUST-FIX` | Defect / violates team mandatory standards | **Must fix before merge, cannot bypass** |
| `SUGGEST` | Better solution available, but current solution acceptable | Must respond with handling decision (accept / reject + reason) |
| `NIT` | Minor improvement (naming optimization, formatting, etc.) | Optional to handle, but must not be closed without response |

**Examples:**

```
[MUST-FIX] src/service/ArticleService.java:42
原因：catch(Exception e) 后仅打印日志，异常被吞掉，调用方无法感知失败
建议：throw new {BizException}({ResultCode}.ARTICLE_SAVE_FAILED, e)

[SUGGEST] src/domain/ArticleRepository.java:18
原因：直接依赖 ArticleMapper，破坏防腐层
建议：通过 Repository 接口隔离，在 infrastructure 层注入 Mapper

[NIT] src/dto/vo/ArticleVO.java:5
原因：字段缺少 @Schema 注解，Swagger 文档不完整
建议：补充 @Schema(description = "...")
```

---

## 5. Handling Review Feedback Standards

After loading `receiving-code-review` Skill, handle each comment according to the following standards:

1. **Respond item by item**: Must not batch close, each comment must have clear response
2. **MUST-FIX**: After fixing, attach modification commit hash in comment
3. **SUGGEST**: If accepted, modify and reply; if rejected, must state technical reason, cannot just reply "acknowledged"
4. **NIT**: After handling reply "Done"; when deciding not to handle, explain reason
5. **Disputes**: Discuss in comments, must not bypass Review process for direct merge through private communication
