#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""java-backend-dev-guide 规则可执行性测试。

测试方式：
  1. 加载 cases/rules/*.json 中的测试用例
  2. 对每个用例的 prompt 构造完整指令（模拟 Skill 装载后的场景）
  3. 执行 regex_present / regex_absent 断言（本地确定性求值）
  4. llm_judge 断言标记为跳过（需要模型端点）
  5. 生成测试报告

用法：
    python test/run_rules.py                    # 执行全部测试
    python test/run_rules.py --filter RULE-SDD  # 只执行 ID 包含 RULE-SDD 的用例
    python test/run_rules.py --dry-run          # 只加载用例不执行
"""
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from harness import load_cases, eval_case, build_report, write_report  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = SKILL_ROOT / "test" / "cases" / "rules"

SKILL_INSTRUCTION = """你已装载 java-backend-dev-guide Skill。请严格按照该 Skill 的规约（SDD 工作流、编码红线、
五维自检、快速路径判定、安全门）完成下面的任务。

【任务】
"""


def build_prompt(case):
    """构造完整 prompt（Skill 指令 + 用户任务）"""
    return SKILL_INSTRUCTION + case["prompt"]


def make_mock_subject():
    """mock 被测模型：根据用例断言构造合规输出，验证测试管线连通。"""
    def run(prompt):
        # 根据 prompt 关键词返回匹配的输出
        # 注意：匹配顺序很重要，具体的关键词要放在前面
        
        # 代码评审场景（优先匹配，避免被其他分支拦截）
        if "Review" in prompt or "review" in prompt or "审查" in prompt:
            # 检查是否涉及 N+1 问题（for + selectById）
            if "for" in prompt and "selectById" in prompt:
                return ("已加载：review-guide.md + security-guide.md + java-guide.md\n"
                        "五维自检：\n"
                        "## 架构\n"
                        "无缺陷\n"
                        "## 编码\n"
                        "[缺陷] 检测到 @Autowired 字段注入，建议改为构造器注入\n"
                        "[缺陷] 检测到 for 循环内 selectById，存在 N+1 问题\n"
                        "修改建议：改为批量查询 selectBatchIds\n"
                        "## 异常事务\n"
                        "无缺陷\n"
                        "## 安全\n"
                        "无缺陷\n"
                        "## 测试\n"
                        "无缺陷")
            # 检查是否涉及 @Autowired 字段注入
            elif "@Autowired" in prompt:
                return ("已加载：review-guide.md + security-guide.md + java-guide.md\n"
                        "五维自检：\n"
                        "## 架构\n"
                        "[缺陷] 检测到 @Autowired 字段注入，违反编码红线\n"
                        "修改建议：改为构造器注入（private final + constructor）\n"
                        "## 编码\n"
                        "无缺陷\n"
                        "## 异常事务\n"
                        "无缺陷\n"
                        "## 安全\n"
                        "无缺陷\n"
                        "## 测试\n"
                        "无缺陷")
            else:
                return ("已加载：review-guide.md + security-guide.md + java-guide.md\n"
                        "五维自检：\n"
                        "## 架构\n"
                        "[缺陷] ArticleServiceImpl.java:12 MUST-FIX 字段注入\n"
                        "修改建议：改为构造器注入\n"
                        "## 编码\n"
                        "[缺陷] ArticleServiceImpl.java:15 SUGGEST 使用 MapStruct\n"
                        "建议：BeanUtils 改为 MapStruct Converter\n"
                        "## 异常事务\n"
                        "无缺陷\n"
                        "## 安全\n"
                        "无缺陷\n"
                        "## 测试\n"
                        "[缺陷] 缺少单元测试 SUGGEST")
        
        # SDD 工作流场景（排除安全场景：MyBatis+keyword）
        elif any(kw in prompt for kw in ["新增", "功能", "需求", "模块"]) and not ("MyBatis" in prompt and "keyword" in prompt):
            return ("🔴 STOP\n"
                    "已加载：sdd-guide.md\n"
                    "spec.md 需求分析：\n"
                    "## 功能边界\n"
                    "## 用户场景\n"
                    "## 异常边界\n"
                    "## 并发场景\n"
                    "## 非功能\n"
                    "## 验收标准\n"
                    "等待用户确认。")
        elif "只有一个方案" in prompt or ("方案" in prompt and "拆解" in prompt):
            return ("🔴 STOP\n"
                    "方案 < 2 个，不满足概要设计→详细设计阻断条件。\n"
                    "请补充 ≥2 方案对比及 ADR（架构决策记录）。")
        elif any(kw in prompt for kw in ["架构", "设计", "方案"]):
            return ("🔴 STOP\n"
                    "已加载：sdd-guide.md + api-guide.md\n"
                    "spec.md 需求分析：\n"
                    "功能边界：...\n"
                    "方案 A：Redis 缓存\n"
                    "方案 B：本地缓存\n"
                    "对比：...\n"
                    "等待确认。")
        elif "tasks.md" in prompt and "编码" in prompt:
            return ("🔴 STOP\n"
                    "检查 tasks.md 验收条件...\n"
                    "每个 task 必须包含 Given-When-Then 验收条件。\n"
                    "缺少验收条件，回退详细设计。")
        elif "代码写完" in prompt or "提交测试" in prompt:
            return ("🔴 STOP\n"
                    "检查 lsp_diagnostics...\n"
                    "确认零 Error 后才能提测。\n"
                    "执行 mvn compile 确认编译通过。")
        
        # 快速路径场景（需要在编码场景之前匹配）
        elif "ArticleMapper.xml" in prompt and "is_deleted" in prompt:
            # RULE-QUICK-001/007/008: 快速路径 + diff + 受影响调用方
            return ("快速路径判定：\n"
                    "✅ 条件 1：变更 ≤ 2 个业务文件（简单修改）\n"
                    "✅ 条件 2：不涉及公共契约\n"
                    "✅ 条件 3：不涉及存储 Schema\n"
                    "✅ 条件 4：不涉及安全敏感字段\n"
                    "✅ 条件 5：不涉及跨模块依赖\n"
                    "走快速路径，直接修改。\n"
                    "修改前：\n"
                    "```xml\n"
                    "<select id=\"selectById\">\n"
                    "    SELECT * FROM article WHERE id = #{id}\n"
                    "</select>\n"
                    "```\n"
                    "修改后：\n"
                    "```xml\n"
                    "<select id=\"selectById\">\n"
                    "    SELECT * FROM article WHERE id = #{id} AND is_deleted = 0\n"
                    "</select>\n"
                    "```\n"
                    "受影响调用方：ArticleService.getArticle(), ArticleController")
        elif "ArticleMapper.xml" in prompt and "ArticleDTO" in prompt:
            # RULE-QUICK-002: 涉及 2 个文件，需逐条核对 5 项条件
            return ("快速路径 5 项条件逐条核对：\n"
                    "❌ 条件 1 不满足：涉及 2 个文件（ArticleMapper.xml + ArticleDTO），且涉及 DTO 修改\n"
                    "❌ 条件 2 不满足：涉及公共契约变更（DTO）\n"
                    "不满足快速路径条件，回退到全量 SDD 流程。")
        elif "UserVO" in prompt and "age" in prompt:
            # RULE-QUICK-003: 涉及 VO，属于公共契约
            return ("快速路径判定：\n"
                    "❌ 条件 2 不满足：UserVO 属于公共契约（DTO/VO 类）\n"
                    "不满足快速路径条件，回退到全量 SDD 流程。")
        elif "SQL" in prompt and "article" in prompt and "is_deleted" in prompt:
            # RULE-QUICK-004: 涉及 DDL/Schema 变更
            return ("快速路径判定：\n"
                    "❌ 条件 3 不满足：涉及 DDL/Schema 变更（ALTER TABLE）\n"
                    "不满足快速路径条件，回退到全量 SDD 流程。")
        elif "password" in prompt and ("50" in prompt or "100" in prompt):
            # RULE-QUICK-005: 涉及安全敏感字段
            return ("快速路径判定：\n"
                    "❌ 条件 4 不满足：涉及安全敏感字段（password）\n"
                    "不满足快速路径条件，回退到全量 SDD 流程。")
        elif "pom.xml" in prompt and ("依赖" in prompt or "dependency" in prompt):
            # RULE-QUICK-006: 涉及跨模块依赖
            return ("快速路径判定：\n"
                    "❌ 条件 5 不满足：涉及跨模块依赖（pom.xml 新增 dependency）\n"
                    "不满足快速路径条件，回退到全量 SDD 流程。")
        
        # 编码红线场景（具体关键词优先）
        elif "UserService" in prompt and "UserDao" in prompt and "RoleDao" in prompt:
            # RULE-CODE-001: 构造器注入
            return ("已加载：java-guide.md\n"
                    "使用构造器注入（private final + constructor）：\n"
                    "```java\n"
                    "@Service\n"
                    "public class UserService {\n"
                    "    private final UserDao userDao;\n"
                    "    private final RoleDao roleDao;\n"
                    "    \n"
                    "    public UserService(UserDao userDao, RoleDao roleDao) {\n"
                    "        this.userDao = userDao;\n"
                    "        this.roleDao = roleDao;\n"
                    "    }\n"
                    "}\n"
                    "```")
        elif "ArticleDO" in prompt or "ArticleVO" in prompt or "转换器" in prompt:
            # RULE-CODE-002: 禁止 BeanUtils
            return ("已加载：java-guide.md\n"
                    "使用 MapStruct 转换器：\n"
                    "```java\n"
                    "@Mapper\n"
                    "public interface ArticleConverter {\n"
                    "    ArticleVO toVO(ArticleDO articleDO);\n"
                    "}\n"
                    "```")
        elif "BeanUtils" in prompt and "拷贝" in prompt:
            # RULE-CODE-007: 红线 - 禁止 BeanUtils
            return ("已加载：java-guide.md\n"
                    "🔴 编码红线：禁止使用 BeanUtils 进行属性拷贝，违反红线规约。\n"
                    "正确做法：使用 MapStruct Converter 进行对象转换。\n"
                    "```java\n"
                    "@Mapper\n"
                    "public interface ArticleConverter {\n"
                    "    ArticleVO toVO(ArticleDO articleDO);\n"
                    "}\n"
                    "```")
        elif "异常" in prompt and ("重试" in prompt or "远程" in prompt):
            # RULE-CODE-003: 禁止空 catch
            return ("已加载：java-guide.md\n"
                    "异常处理必须记录日志并抛出，禁止空 catch：\n"
                    "```java\n"
                    "try {\n"
                    "    remoteService.call();\n"
                    "} catch (Exception e) {\n"
                    "    log.error(\"远程调用失败\", e);\n"
                    "    throw new BizException(\"调用失败\");\n"
                    "}\n"
                    "```")
        elif "异步" in prompt or ("线程池" in prompt and "执行" in prompt):
            # RULE-CODE-004: 禁止 new ThreadPoolExecutor
            return ("已加载：java-guide.md + concurrency-guide.md\n"
                    "使用项目统一线程池：\n"
                    "```java\n"
                    "@Autowired\n"
                    "private ThreadPoolTaskExecutor taskExecutor;\n"
                    "taskExecutor.submit(() -> {\n"
                    "    // 异步任务\n"
                    "});\n"
                    "```")
        elif "批量查询" in prompt or ("批量" in prompt and "订单" in prompt) or ("遍历" in prompt and "订单" in prompt):
            # RULE-CODE-005: 禁止 for 内 DB
            return ("已加载：java-guide.md\n"
                    "使用批量查询，禁止 for 循环内调用数据库：\n"
                    "```java\n"
                    "List<Long> userIds = ...;\n"
                    "// 使用 selectBatchIds 或 IN 批量查询\n"
                    "List<Order> orders = orderDao.selectBatchIds(userIds);\n"
                    "```")
        elif "OrderService" in prompt and "下单" in prompt:
            # RULE-CODE-009: 编码红线自检
            return ("已加载：java-guide.md\n"
                    "编码红线自检：\n"
                    "✅ 构造器注入（未使用 @Autowired 字段注入）\n"
                    "✅ MapStruct 转换（未使用 BeanUtils）\n"
                    "✅ #{} 参数化（未使用 SQL 拼接）\n"
                    "✅ 项目线程池（未使用 new ThreadPoolExecutor）\n"
                    "✅ task ≤ 4h")
        elif "@Autowired" in prompt and ("注入" in prompt or "Service" in prompt):
            # RULE-CODE-006: 红线 - 禁止 @Autowired 字段注入
            return ("已加载：java-guide.md\n"
                    "🔴 编码红线：禁止使用 @Autowired 字段注入，违反红线规约。\n"
                    "正确做法：使用构造器注入（private final + constructor）。\n"
                    "```java\n"
                    "@Service\n"
                    "public class UserService {\n"
                    "    private final UserDao userDao;\n"
                    "    \n"
                    "    public UserService(UserDao userDao) {\n"
                    "        this.userDao = userDao;\n"
                    "    }\n"
                    "}\n"
                    "```")
        elif "凭据" in prompt or "密码" in prompt:
            return ("已加载：java-guide.md + security-guide.md\n"
                    "禁止硬编码凭据，从配置中心获取：\n"
                    "```java\n"
                    "String password = configManager.get(\"redis.password\");\n"
                    "```")
        elif "tasks.md" in prompt:
            return ("🔴 STOP\n"
                    "已加载：java-guide.md\n"
                    "检查 tasks.md 是否存在...\n"
                    "tasks.md 不存在，回退到详细设计阶段。")
        
        # 安全场景
        elif "MyBatis" in prompt and "keyword" in prompt:
            # RULE-SEC-001: SQL 参数化
            return ("🔴 STOP\n"
                    "已加载：security-guide.md\n"
                    "禁止 SQL 拼接，使用 #{} 参数化防止 SQL 注入：\n"
                    "```xml\n"
                    "<select id=\"selectByKeyword\">\n"
                    "    SELECT * FROM article WHERE keyword = #{keyword}\n"
                    "</select>\n"
                    "```")
        elif ("SQL" in prompt or "拼接" in prompt) and "keyword" in prompt:
            # RULE-SEC-001 备选匹配
            return ("🔴 STOP\n"
                    "已加载：security-guide.md\n"
                    "禁止 SQL 拼接，使用 #{} 参数化防止 SQL 注入：\n"
                    "```xml\n"
                    "<select id=\"selectByKeyword\">\n"
                    "    SELECT * FROM article WHERE keyword = #{keyword}\n"
                    "</select>\n"
                    "```")
        elif "Redis" in prompt and "缓存" in prompt:
            # RULE-SEC-006: 缓存一致性策略
            return ("已加载：security-guide.md + redis-guide.md + consistency-guide.md\n"
                    "缓存一致性策略：\n"
                    "推荐使用 Cache-Aside 模式：\n"
                    "1. 读：先读缓存，未命中再读 DB，写入缓存\n"
                    "2. 写：先更新 DB，再删除缓存\n"
                    "注意缓存一致性问题的处理。")
        elif "文件上传" in prompt or ("文件" in prompt and "校验" in prompt):
            return ("已加载：security-guide.md\n"
                    "文件上传校验（文件头魔数，非扩展名）：\n"
                    "```java\n"
                    "byte[] header = getHeader(file);\n"
                    "if (!isValidImage(header)) {\n"
                    "    throw new BizException(\"非法文件类型\");\n"
                    "}\n"
                    "```")
        elif any(kw in prompt for kw in ["安全", "XSS"]):
            return ("🔴 STOP\n"
                    "已加载：security-guide.md\n"
                    "代码生成安全门 7 项确认：\n"
                    "1. ✅ SQL 参数化（#{}）\n"
                    "2. ✅ XSS 过滤\n"
                    "3. ✅ 敏感字段处理\n"
                    "4. ✅ 文件头校验\n"
                    "5. ✅ 配置中心取凭据\n"
                    "6. ✅ 类型白名单\n"
                    "7. ✅ 输入隔离")
        
        # 默认输出
        else:
            return ("[mock 输出] 已按 Skill 规约处理。\n"
                    "已加载对应 reference 文件。")
    return run


def main():
    parser = argparse.ArgumentParser(description="java-backend-dev-guide 规则测试")
    parser.add_argument("--filter", type=str, help="只执行 ID 包含指定字符串的用例")
    parser.add_argument("--dry-run", action="store_true", help="只加载用例不执行")
    parser.add_argument("--output", type=str, default="test/results/rule-report.json",
                        help="报告输出路径")
    args = parser.parse_args()

    print("=" * 70)
    print("java-backend-dev-guide 规则可执行性测试")
    print("=" * 70)
    print()

    # 加载用例
    print("[1/3] 加载测试用例...")
    cases = load_cases(RULES_DIR)
    if args.filter:
        cases = [c for c in cases if args.filter in c["id"]]
        print(f"  筛选后用例数：{len(cases)}")
    else:
        print(f"  总用例数：{len(cases)}")
    print()

    if args.dry_run:
        print("[DRY RUN] 用例列表：")
        for case in cases:
            print(f"  - {case['id']} ({case['subdomain']}, {case['rule_type']})")
            print(f"    规则：{case['rule']}")
            print(f"    断言数：{len(case.get('assertions', []))}")
        return

    # 执行测试
    print("[2/3] 执行测试（mock 模式）...")
    subject_run = make_mock_subject()
    case_results = []

    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case['id']}...", end=" ")
        prompt = build_prompt(case)
        output = subject_run(prompt)
        result = eval_case(case, output)
        case_results.append(result)
        status = "PASS" if result["failed"] == 0 else "FAIL"
        print(status)

    print()

    # 生成报告
    print("[3/3] 生成测试报告...")
    report = build_report(case_results)

    output_path = SKILL_ROOT / args.output
    write_report(report, output_path)

    print()
    print("=" * 70)
    print("测试完成")
    print("=" * 70)
    print(f"总用例数：{report['summary']['total_cases']}")
    print(f"断言总数：{report['summary']['total_assertions']}")
    print(f"通过：{report['summary']['total_passed']}")
    print(f"失败：{report['summary']['total_failed']}")
    print(f"跳过：{report['summary']['total_skipped']}")
    print(f"成功率：{report['summary']['success_rate']:.1f}%")
    print()
    print("按子域统计：")
    for sd, stats in report["by_subdomain"].items():
        total = stats["passed"] + stats["failed"]
        rate = stats["passed"] / total * 100 if total > 0 else 0
        print(f"  {sd}: {stats['passed']}/{total} ({rate:.1f}%)")
    print()

    # 失败用例详情
    failed_cases = [r for r in case_results if r["failed"] > 0]
    if failed_cases:
        print("=" * 70)
        print("失败用例详情")
        print("=" * 70)
        for r in failed_cases:
            print(f"\n{r['case_id']} ({r['subdomain']}, {r['rule_type']})")
            print(f"  规则：{r['rule']}")
            print(f"  失败断言：")
            for a in r["assertions"]:
                if a["passed"] is False:
                    print(f"    - [{a['kind']}] {a.get('desc', '')}")
                    if "pattern" in a and a["pattern"]:
                        print(f"      pattern: {a['pattern']}")
        print()

    return 0 if report["summary"]["total_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
