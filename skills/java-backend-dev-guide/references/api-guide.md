# API Design Standards

---

## 1. RESTful Standards

Route prefix conventions (specific prefixes defined by project-level Skill):

| Package path | Route prefix | Endpoint |
|-------------|-------------|----------|
| `controller.app.*` | Configurable | C-side |
| `controller.admin.*` | Configurable | B-side |

---

## 2. Unified Response Format

All APIs must return the framework response model uniformly. Returning bare Map or custom structures is prohibited:

| Scenario | Response type |
|----------|--------------|
| Single object | `{ResponseWrapper}<T>` |
| Paginated list | `{PageResponse}<T>` |
| Cursor scroll | `{ScrollResponse}<T>` (use search_after for deep pagination, not pageIndex) |
| No return value | `{ResponseWrapper}<Void>` |

```java
// ✅ 正确
{ResponseWrapper}<ArticleVO>  result = {ResponseWrapper}.success(articleVO);
{ResponseWrapper}<Void>       error  = {ResponseWrapper}.fail({ResultCode}.ARTICLE_NOT_FOUND);

// ❌ 禁止
return Map.of("code", 0, "data", articleVO);
```

---

## 3. Parameter Validation

Input DTOs use JSR-380 annotations, Controller adds `@Valid`:

```java
@PostMapping("/articles")
public {ResponseWrapper}<Long> create(@RequestBody @Valid CreateArticleCMD cmd) { ... }
```

`@Valid` validation failures are intercepted by the global exception handler uniformly. **MUST NOT** manually check `BindingResult` inside Controller methods.

---

## 4. OpenAPI 3 Annotation Standards

**[Mandatory]** All REST APIs and their parameters, request/response bodies must have OpenAPI 3 annotations.

### 4.1. API-level Annotations

| Annotation location | Annotation | Format |
|--------------------|-----------|--------|
| Controller class | `@Tag(name = "...")` | `{side} - {business domain}`, e.g. "Admin - API Access Log" |
| API method | `@Operation(summary = "...")` | One-line description of API functionality |

### 4.2. Input Parameter Annotations

| Parameter source | Annotation method |
|-----------------|-------------------|
| `@RequestParam` | Add `@Parameter(description = "...", required = true/false)` to method parameter |
| `@RequestBody` VO | VO class adds `@Schema(description = "...")`, each field adds `@Schema(description = "...", requiredMode = ...)` |
| `HttpServletRequest` / `HttpServletResponse` | **Do not add** `@Parameter`, Swagger auto-ignores |

### 4.3. Output Parameter Annotations

Output VO classes and each field must have `@Schema(description = "...")`. Response wrapper classes have built-in `@Schema`, only need to annotate the business VO in the generic type.

### 4.4. Complete Example

```java
@Tag(name = "管理端 - 文章管理")
@RestController
@RequestMapping("/api/article")
public class ArticleController {

    @Operation(summary = "滚动查询文章列表")
    @GetMapping("/scroll")
    public {ScrollResponse}<ArticleVO> scroll(ArticleScrollQRY qry) {
        return articleService.scroll(qry);
    }

    @Operation(summary = "查询文章详情")
    @GetMapping("/detail")
    public {ResponseWrapper}<ArticleVO> detail(
            @Parameter(description = "文章 ID", required = true) @RequestParam String articleId) {
        return articleService.detail(articleId);
    }
}

// 入参 QRY
@Schema(description = "文章滚动查询请求")
public class ArticleScrollQRY implements Serializable {

    @Schema(description = "分类 ID（可选，按分类筛选）")
    private Long categoryId;

    @Schema(description = "每批条数（max 100）", example = "20")
    private Integer pageSize = 20;

    @Schema(description = "游标值（首页不传，后续页传入上页返回值）")
    private String scrollId;
}

// 出参 VO
@Schema(description = "文章")
public class ArticleVO implements Serializable {

    @Schema(description = "文章 ID")
    private String articleId;

    @Schema(description = "文章标题")
    private String title;

    @Schema(description = "发布时间")
    private LocalDateTime publishTime;
}
```

### 4.5. Self-Check Checklist

- [ ] Controller class has `@Tag(name = "{side} - {business}")`
- [ ] Each HTTP method has `@Operation(summary = "...")`
- [ ] `@RequestParam` parameters have `@Parameter(description, required)`
- [ ] `@RequestBody` VO class and each field have `@Schema(description)`
- [ ] Output VO class and each field have `@Schema(description)`

---

## 5. Audit Logging

> The implementation of audit logging is defined by the project-level Skill. If using a custom annotation (such as `{AuditLogAnnotation}`), write operation APIs must add it.

All write operation APIs (POST / PUT / PATCH / DELETE) **MUST** add audit log annotations to ensure operations are traceable.
