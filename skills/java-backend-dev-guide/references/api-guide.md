# 接口设计规范

> **摘要**
>
> - **核心约束**：统一响应格式禁裸 Map；写操作接口必须加审计日志注解；所有 REST 接口必须标记 OpenAPI 3 注解（@Tag + @Operation + @Schema）
> - **关键阈值**：游标分页用 search_after 禁 from+size 深分页
> - **常见违规**：Controller 返回 Map 而非统一响应、@RequestBody VO 缺 @Schema、写接口漏审计日志

> **版本**：v1.0 | 最后更新：2026-06-09 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. RESTful 规范

> HTTP 方法语义遵循《阿里巴巴 Java 开发手册（黄山版）》§一 编程规约 — 前后端规约。

路由前缀约定（由项目级 Skill 定义具体前缀）：

| 包路径               | 路由前缀     | 端   |
| -------------------- | ------------ | ---- |
| `controller.app.*`   | 可配置       | C 端 |
| `controller.admin.*` | 可配置       | B 端 |

---

## 2. 统一响应格式

所有接口统一返回框架响应模型，禁止返回裸 Map 或自定义结构：

| 场景     | 响应类型                                                   |
| -------- | ---------------------------------------------------------- |
| 单对象   | `{ResponseWrapper}<T>`                                     |
| 分页列表 | `{PageResponse}<T>`                                        |
| 游标滚动 | `{ScrollResponse}<T>`（深分页用 search_after，不用 pageIndex） |
| 无返回值 | `{ResponseWrapper}<Void>`                                  |

```java
// ✅ 正确
{ResponseWrapper}<ArticleVO>  result = {ResponseWrapper}.success(articleVO);
{ResponseWrapper}<Void>       error  = {ResponseWrapper}.fail({ResultCode}.ARTICLE_NOT_FOUND);

// ❌ 禁止
return Map.of("code", 0, "data", articleVO);
```

---

## 3. 参数校验

入参 DTO 使用 JSR-380 注解，Controller 加 `@Valid`：

```java
@PostMapping("/articles")
public {ResponseWrapper}<Long> create(@RequestBody @Valid CreateArticleCMD cmd) { ... }
```

`@Valid` 校验失败由全局异常处理器统一拦截，**MUST NOT** 在 Controller 方法内手动判断 `BindingResult`。

---

## 4. OpenAPI 3 标记规范

**【强制】** 所有 REST 接口及其入参、出参必须添加 OpenAPI 3 注解。

### 4.1. 接口级标记

| 标记位置      | 注解                          | 格式                                           |
| ------------- | ----------------------------- | ---------------------------------------------- |
| Controller 类 | `@Tag(name = "...")`          | `{端} - {业务领域}`，如"管理端 - API 访问日志" |
| 接口方法      | `@Operation(summary = "...")` | 一句话说明接口功能                             |

### 4.2. 入参标记

| 参数来源                                     | 标记方式                                                                                              |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `@RequestParam`                              | 方法参数加 `@Parameter(description = "...", required = true/false)`                                   |
| `@RequestBody` VO                            | VO 类加 `@Schema(description = "...")`，每个字段加 `@Schema(description = "...", requiredMode = ...)` |
| `HttpServletRequest` / `HttpServletResponse` | **不加** `@Parameter`，Swagger 自动忽略                                                               |

### 4.3. 出参标记

出参 VO 类及每个字段均加 `@Schema(description = "...")`。响应包装类已内置 `@Schema`，只需标注泛型中的业务 VO。

### 4.4. 完整示例

```java
@Tag(name = "管理端 - API 访问日志")
@RestController
@RequestMapping("/api/access-log")
public class AccessLogController {

    @Operation(summary = "滚动查询 API 访问日志")
    @GetMapping("/scroll")
    public {ScrollResponse}<ApiAccessLogVO> scroll(ApiAccessLogScrollQRY qry) {
        return accessLogService.scroll(qry);
    }

    @Operation(summary = "查询日志详情")
    @GetMapping("/detail")
    public {ResponseWrapper}<ApiAccessLogVO> detail(
            @Parameter(description = "文档 ID", required = true) @RequestParam String docId,
            @Parameter(description = "日志所属日期", required = true)
            @RequestParam String beginTime) {
        return accessLogService.detail(docId, beginTime);
    }
}

// 入参 QRY
@Schema(description = "API 访问日志滚动查询请求")
public class ApiAccessLogScrollQRY implements Serializable {

    @Schema(description = "开始时间（默认近 1 小时）")
    private LocalDateTime beginTime;

    @Schema(description = "每批条数（max 100）", example = "20")
    private Integer pageSize = 20;

    @Schema(description = "游标值（首页不传，后续页传入上页返回值）")
    private String scrollId;
}

// 出参 VO
@Schema(description = "API 访问日志")
public class ApiAccessLogVO implements Serializable {

    @Schema(description = "链路追踪编号")
    private String traceId;

    @Schema(description = "请求 URL")
    private String requestUrl;

    @Schema(description = "接口耗时（ms）")
    private Integer duration;
}
```

### 4.5. 自检清单

- [ ] Controller 类有 `@Tag(name = "{端} - {业务}")`
- [ ] 每个 HTTP 方法有 `@Operation(summary = "...")`
- [ ] `@RequestParam` 参数有 `@Parameter(description, required)`
- [ ] `@RequestBody` VO 类和每个字段有 `@Schema(description)`
- [ ] 出参 VO 类和每个字段有 `@Schema(description)`

---

## 5. 审计日志

> 审计日志的实现方式由项目级 Skill 定义。如使用自定义注解（如 `{AuditLogAnnotation}`），写操作接口必须添加。

所有写操作接口（POST / PUT / PATCH / DELETE）**MUST** 添加审计日志注解，确保操作可追溯。
