# java-backend-dev-guide 测试框架

本目录包含 `java-backend-dev-guide` Skill 的自动化测试框架，参考 `prd-management/test` 设计。

## 目录结构

```
test/
├── cases/
│   └── rules/
│       ├── rules_a_sdd_workflow.json    # SDD 工作流规则（7 个用例）
│       ├── rules_b_coding_redline.json  # 编码红线规则（9 个用例）
│       ├── rules_c_review.json          # 代码评审规则（5 个用例）
│       ├── rules_d_security.json        # 安全规则（6 个用例）
│       └── rules_e_quick_path.json      # 快速路径规则（8 个用例）
├── bilingual_audit.py                   # 中英配对一致性门禁（6 项机械检查 + 注入式负控）
├── test-prompts.json                    # 触发词测试（8 个 prompt）
└── README.md                            # 本文件
```

## 测试用例格式

每个 JSON 文件包含多个测试用例，格式如下：

```json
{
  "meta": {
    "subdomains": ["sdd", "workflow"],
    "assertion_kinds": {
      "regex_present": "输出必须匹配 pattern（确定性断言）",
      "regex_absent": "输出禁止匹配 pattern（确定性断言）",
      "llm_judge": "由 judge 模型按 criterion 判定，evidence_required=true 时必须引用输出原文作为证据"
    },
    "note": "prompt 中已内联必要输入材料，保证用例自包含、可脱离会话历史独立回归"
  },
  "cases": [
    {
      "id": "RULE-SDD-001",
      "subdomain": "sdd",
      "rule_type": "MUST",
      "source": "SKILL.md#§1",
      "rule": "MUST NOT 跨阶段跳跃：每阶段必须先产出 Artifact 并经用户确认，才能进入下一阶段",
      "prompt": "帮我新增一个文章收藏功能，用户可以收藏和取消收藏文章。",
      "assertions": [
        {"kind": "regex_present", "pattern": "🔴 STOP|🔴 阻断", "desc": "使用 🔴 STOP 标记阻断"},
        {"kind": "regex_absent", "pattern": "@Service|@RestController", "desc": "不得直接输出实现代码"},
        {"kind": "llm_judge", "criterion": "未直接写代码，而是先输出 spec.md 需求分析框架", "evidence_required": true}
      ]
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 用例唯一标识（格式：`RULE-{SUBDOMAIN}-{NNN}`） |
| `subdomain` | string | 子领域（sdd/workflow/coding/redline/review/security/quick_path） |
| `rule_type` | string | 规则类型（`MUST` / `MUST_NOT`） |
| `source` | string | 规则来源（SKILL.md 的章节引用） |
| `rule` | string | 规则描述（自然语言） |
| `prompt` | string | 用户输入（测试 prompt） |
| `assertions` | array | 断言数组 |

### 断言类型

| kind | 说明 | 参数 |
|------|------|------|
| `regex_present` | 输出必须匹配 pattern | `pattern`（正则表达式） |
| `regex_absent` | 输出禁止匹配 pattern | `pattern`（正则表达式） |
| `llm_judge` | 由 judge 模型按 criterion 判定 | `criterion`（判定标准）+ `evidence_required`（是否要求引用原文） |

## 测试覆盖

### rules_a_sdd_workflow.json（7 个用例）

| ID | 规则 | 类型 |
|----|------|------|
| RULE-SDD-001 | MUST NOT 跨阶段跳跃 | MUST_NOT |
| RULE-SDD-002 | 全量流程必须先产出 spec.md | MUST |
| RULE-SDD-003 | 概要设计→详细设计阻断：方案 < 2 个 | MUST |
| RULE-SDD-004 | 详细设计→编码阻断：无验收条件 | MUST |
| RULE-SDD-005 | 编码→测试阻断：LSP 有 Error | MUST |
| RULE-SDD-006 | 场景路由：新功能匹配 #1 | MUST |
| RULE-SDD-007 | 场景路由：代码评审匹配 #4 | MUST |

### rules_b_coding_redline.json（9 个用例）

| ID | 规则 | 类型 |
|----|------|------|
| RULE-CODE-001 | 禁止 @Autowired 字段注入 | MUST_NOT |
| RULE-CODE-002 | 禁止 BeanUtils.copyProperties | MUST_NOT |
| RULE-CODE-003 | 禁止空 catch | MUST_NOT |
| RULE-CODE-004 | 禁止 new ThreadPoolExecutor | MUST_NOT |
| RULE-CODE-005 | 禁止 for 循环内调用数据库 | MUST_NOT |
| RULE-CODE-006 | 五条红线：@Autowired → 构造器注入 | MUST_NOT |
| RULE-CODE-007 | 五条红线：BeanUtils → MapStruct | MUST_NOT |
| RULE-CODE-008 | 五条红线：SQL 拼接 → #{} 参数化 | MUST_NOT |
| RULE-CODE-009 | 编码前必须对照反例黑名单自检 | MUST |

### rules_c_review.json（5 个用例）

| ID | 规则 | 类型 |
|----|------|------|
| RULE-REVIEW-001 | 五维自检（架构/编码/异常事务/安全/测试） | MUST |
| RULE-REVIEW-002 | 每条缺陷含文件路径+行号+修复方案 | MUST |
| RULE-REVIEW-003 | 识别 §4.1 反例黑名单命中项 | MUST |
| RULE-REVIEW-004 | MUST-FIX 缺陷标注级别 | MUST |
| RULE-REVIEW-005 | 加载 review-guide.md + security-guide.md + java-guide.md | MUST |

### rules_d_security.json（6 个用例）

| ID | 规则 | 类型 |
|----|------|------|
| RULE-SEC-001 | 禁止 SQL 字符串拼接 | MUST_NOT |
| RULE-SEC-002 | 禁止仅校验扩展名 | MUST_NOT |
| RULE-SEC-003 | 禁止硬编码凭据 | MUST_NOT |
| RULE-SEC-004 | 禁止反序列化无白名单 | MUST_NOT |
| RULE-SEC-005 | 安全场景触发代码生成安全门 7 项自检 | MUST |
| RULE-SEC-006 | 涉及存储操作先确认一致性策略 | MUST |

### rules_e_quick_path.json（8 个用例）

| ID | 规则 | 类型 |
|----|------|------|
| RULE-QUICK-001 | 快速路径适用条件：≤ 2 个业务文件 | MUST |
| RULE-QUICK-002 | 快速路径 5 项客观判定标准逐条核对 | MUST |
| RULE-QUICK-003 | 快速路径不涉及公共契约变更 | MUST_NOT |
| RULE-QUICK-004 | 快速路径不涉及存储 Schema 变更 | MUST_NOT |
| RULE-QUICK-005 | 快速路径不涉及安全敏感字段 | MUST_NOT |
| RULE-QUICK-006 | 快速路径不涉及跨模块依赖 | MUST_NOT |
| RULE-QUICK-007 | 快速路径输出含 diff（修改前/修改后） | MUST |
| RULE-QUICK-008 | 快速路径列出受影响调用方 | MUST |

## 运行测试

### 前置条件

- Python 3.8+
- 安装测试依赖：`pip install pytest pytest-asyncio`

### 执行测试

```bash
# 运行全部规则测试
python -m pytest cases/rules/ -v

# 运行单个文件
python -m pytest cases/rules/rules_a_sdd_workflow.json -v

# 运行触发词测试
python -m pytest test-prompts.json -v
```

### 测试输出

测试通过时输出：

```
test/rules_a_sdd_workflow.py::test_RULE_SDD_001 PASSED
test/rules_a_sdd_workflow.py::test_RULE_SDD_002 PASSED
...
```

测试失败时输出：

```
test/rules_a_sdd_workflow.py::test_RULE_SDD_001 FAILED
AssertionError: regex_present failed
  pattern: 🔴 STOP|🔴 阻断
  output: (实际输出)
```

## 中英配对一致性门禁

`SKILL.en.md` 与 `references/*.en.md` 是中文原文的镜像译文（sidecar 本地化）。任何一侧单独改动都会让译文腐化，因此有一层**只收机械可判定项**的门禁：

```bash
python test/bilingual_audit.py              # 全量检查，有失败则退出码 1
python test/bilingual_audit.py --selftest   # 注入式负控：确认 6 项检查都能抓到人造缺陷
```

| 检查 | 判据 | 为什么可机械判定 |
|------|------|------------------|
| `fence` | 代码块内容中英**逐字节**一致 | 既定约定：围栏内保留中文，不允许翻译 |
| `shape` | 标题层级数 / 围栏标记数 / 表格行数 / 总行数一致 | 结构漂移等于漏译整段 |
| `number` | 逐行数量级一致（万/亿 与 K/M/billion 归一后比较） | 阈值错一个量级是硬伤 |
| `ref` | § 引用可解析；裸 `（§x.y）` 不得在本文件与 `SKILL.md` 同号不同题 | 就近解析会指错章节 |
| `identifier` | 行内代码里的编程标识符（snake/camel/@注解）两侧都必须出现 | `pageIndex` 被写成 `pageIndexIndex` 这类错译可枚举 |
| `term` | 术语黑名单：指定中文术语出现处，英文禁止出现指定写法 | 已修过的错译不许复发（线上→online、灰度→canary、脱敏→desensitization 等） |

**何时必须跑**：改动 `SKILL.md` / `SKILL.en.md` / `references/` 下任意成对文件后、commit 之前。

**边界**：语义保真度（论据弱化、范围收窄、术语域塌缩中不命中黑名单的那些）**不在本门禁内**——它只能靠盲译回译流程，做法与历史结论见 [BACKTRANSLATION_AUDIT.md](BACKTRANSLATION_AUDIT.md)。本脚本负责的是"已经犯过的错不再犯"，不是"没有新错"。

## 添加新测试

1. 在对应子领域的 JSON 文件中添加新用例
2. 确保 `id` 唯一（格式：`RULE-{SUBDOMAIN}-{NNN}`）
3. 填写完整的 `prompt` 和 `assertions`
4. 运行测试验证

## 参考

- [prd-management/test](../../prd-management/test/) — 原始设计参考
- [SKILL.md](../SKILL.md) — 被测 Skill 定义
- [test-prompts.json](../test-prompts.json) — 触发词测试集
