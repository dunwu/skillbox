# 代码评审规范

> **摘要**
>
> - **核心约束**：AI 自检 5 维度（架构合规/编码规范/异常事务/安全/测试）全部通过才能提 PR；公共契约/存储 Schema/安全相关变更 MUST NOT 跳过 Review 直接合并
> - **关键阈值**：Comment 格式 [severity] 路径:行号，MUST-FIX 合并前必修、SUGGEST 必须回复决策、NIT 不得无回应关闭
> - **常见违规**：未完成 AI 自检就提 PR、批量关闭 Review 意见、MUST-FIX 未修复直接合并、私下沟通绕过 Review

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 触发时机

| 场景                       | 操作                                                      |
| -------------------------- | --------------------------------------------------------- |
| 完成编码，准备提 PR        | 加载 `requesting-code-review` Skill，触发 AI 辅助 Review  |
| 收到 Review 反馈，准备修改 | 加载 `receiving-code-review` Skill，逐条处理意见          |
| PR 通过，准备合并          | 确认所有 `MUST-FIX` 已修复，门禁通过（→ quality-gate.md） |

**MUST NOT** 在未经 Code Review 的情况下合并涉及公共契约、存储 Schema、安全相关的变更。

---

## 2. AI 自动检查项

提交 Review 前，AI **MUST** 自行完成以下检查并附输出结果：

### 2.1. 架构合规

- [ ] 调用链方向正确（Controller → ApplicationService → DomainService → Repository，无跨层调用）
- [ ] ApplicationService / DomainService 层未直接依赖 DAO 类（经 Repository 接口防腐）
- [ ] Controller 未暴露 DO（已转换为 VO / DTO）
- [ ] 无循环依赖、无跨存储模块直接依赖

### 2.2. 编码规范

- [ ] 命名后缀符合规范（DO / DTO / VO / CMD / QRY / Dao / Repository）
- [ ] 对象转换使用 MapStruct，无 `BeanUtils.copyProperties`
- [ ] 响应统一使用 `{ResponseWrapper}<T>` / `{PageResponse}<T>` / `{ScrollResponse}<T>`
- [ ] 错误码命名符合 `{DOMAIN}_{ACTION_RESULT}` 格式，全大写（→ java-guide.md §3）
- [ ] 通用编码规约（方法行数、JavaDoc、依赖注入、分层职责）遵循《阿里巴巴 Java 开发手册（黄山版）》§一 编程规约 + §六 工程结构

### 2.3. 异常与事务

- [ ] 无 `catch` 后静默吞掉异常
- [ ] 异常使用 `{BizException}({ResultCode}.XXX)`，不抛原始 `RuntimeException`
- [ ] `@Transactional` 仅在 Service 方法，无事务内 RPC / HTTP 调用
- [ ] 无大事务（非核心逻辑已移出事务）

### 2.4. 安全

- [ ] 无明文密钥、Token、密码出现在源码 / 配置 / 日志
- [ ] 敏感字段已加密存储（→ security-guide.md §1）
- [ ] SQL 使用 `#{}` 参数绑定，无字符串拼接

### 2.5. 测试

- [ ] 核心分支有对应单元测试
- [ ] 无被注释的断言或 `@Disabled` 测试
- [ ] Mock 粒度合理（不过度 Mock，ApplicationService / DomainService 层必须有真实逻辑测试）

---

## 3. 人工 Review 必查项

以下维度需人工判断，AI 检查仅供参考：

| 维度           | 检查要点                                                 |
| -------------- | -------------------------------------------------------- |
| 业务逻辑正确性 | 实现是否与 `spec.md` 验收标准逐条吻合                    |
| 边界与异常场景 | 入参为空、并发、超限、第三方超时等场景是否处理           |
| 数据一致性     | 多存储写入是否有事务或补偿机制；缓存与 DB 是否可能不一致 |
| 性能隐患       | N+1 查询、循环内 IO、大对象序列化、无索引大表扫描        |
| 可观测性       | 关键操作是否有日志；异常是否可追踪；指标是否上报         |
| 可维护性       | 魔法数字是否提取为常量；复杂逻辑是否有注释说明意图       |

---

## 4. Review Comment 格式

所有 Review 意见统一格式，便于追踪处理：

```
[severity] 文件路径:行号
原因：{为什么有问题}
建议：{如何修改}
```

**Severity 定义：**

| 级别       | 含义                         | 处理要求                               |
| ---------- | ---------------------------- | -------------------------------------- |
| `MUST-FIX` | 缺陷 / 违反团队强制规范      | **合并前必须修复，不可绕过**           |
| `SUGGEST`  | 有更优方案，但当前方案可接受 | 必须回复处理决策（接受 / 拒绝 + 理由） |
| `NIT`      | 微小改进（命名优化、格式等） | 可选处理，但不得无回应关闭             |

**示例：**

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

## 5. 接收 Review 反馈的处理规范

加载 `receiving-code-review` Skill 后，按以下规范处理每条意见：

1. **逐条响应**：不得批量关闭，每条意见必须有明确回复
2. **MUST-FIX**：修复后在 comment 中附上修改 commit hash
3. **SUGGEST**：若接受则修改并回复；若拒绝须说明技术理由，不得仅回复"已知悉"
4. **NIT**：处理后回复"Done"；决定不处理时说明原因
5. **有疑义**：在 comment 中讨论，不得私下沟通后绕过 Review 流程直接合并
