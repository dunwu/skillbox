# Unit Testing Standards

---

## 0. Technology Selection

> Version source: Project BOM. **MUST NOT** upgrade on own initiative.

| Library | Purpose |
|---------|---------|
| Spring Boot Starter Test | Test infrastructure (JUnit 5, Mockito, etc.) |
| JUnit Jupiter | Test engine and annotations |
| AssertJ Core | Fluent assertions (sole permitted option) |
| Mockito (Core / Inline / Jupiter) | Mock framework (including mockStatic) |
| JaCoCo Maven Plugin | Coverage collection and gates |
| Maven Surefire | Test execution engine |
| Maven PMD | Static analysis |
| Maven Checkstyle | Code style check |

> Specific version numbers defined by project-level Skill or BOM.

---

## 1. Testing Strategy

```
     ▲▲▲▲▲ 单元测试（大量，业务逻辑）
       ▲▲▲ Service 集成测试（中等，跨层交互）
        ▲  E2E / 集成测试（少量，关键链路）
```

**Unit tests as primary**: No dependency on DB/Redis/ES, fast, stable, repeatable.

---

## 2. TDD Workflow

**Write tests first, then implementation.** A task MUST NOT be marked complete before its tests pass.

```
验收条件 → Red（失败测试） → Green（最小实现） → Refactor → 重复至全覆盖
```

**MUST NOT** implement first then add tests — degrades to implementation description, loses verification significance.

---

## 3. Coverage Requirements

| Layer | Focus | Line coverage |
|-------|-------|--------------|
| DomainService | Business rules, branches, exceptions | **100%** |
| ApplicationService | Orchestration logic, transaction boundaries | ≥ 80% |
| Controller | Parameter validation, routing, response format | ≥ 80% |
| Util | Public methods, boundaries, exception paths | ≥ 80% |
| Repository / DAO | Integration test coverage | — |
| Overall module | — | **≥ 80%** |

---

## 4. Naming Conventions

- **Class name**: `{ClassUnderTest}Test`, only English letters + numbers
- **Method name**: `{method}_{scenario}_{expected}`, snake_case, only English + numbers + underscores
- **@DisplayName**: All class / `@Nested` / `@Test` annotated, Chinese describing intent

```java
// ✅ 方法名
void encrypt_whenPlainTextIsNull_returnsNull()

// ❌
void testEncrypt()              // 缺场景/预期
void 加密_空字符串_返回null()    // 含中文
void encrypt-null-input()       // 连字符分隔
```

---

## 5. Organization Structure

**MUST** group by tested method using `@Nested`, inner class name PascalCase; overloads distinguished by parameter type.

```java
@DisplayName("JsonUtil 单元测试")
class JsonUtilTest {
    @Nested @DisplayName("toString(Object)") class ToString {
        @Test @DisplayName("null 输入返回 null")
        void nullInput_returnsNull() {
            assertThat(JsonUtil.toString(null)).isNull();
        }
    }
    @Nested @DisplayName("toBean(String, Class)") class ToBeanClass { ... }
}
```

---

## 6. Mock Strategy

### Principles

- **Only Mock external dependencies** (Repository, RPC, HTTP, config center), **prohibit mocking tested object itself**
- DomainService / ApplicationService must not have everything Mocked out

### Tool Selection

| Scenario | Tool |
|----------|------|
| Standard Mock | `@ExtendWith(MockitoExtension.class)` + `@Mock` / `@InjectMocks` |
| Static methods | `MockedStatic` (use cautiously, prefer refactoring to injectable) |
| Spring context | `@SpringBootTest` (integration tests only) |

### MockedStatic

- Create with `Mockito.withSettings().lenient()`, avoid `InvalidUseOfMatchers`
- **MUST** close `mockStatic.close()` in `@AfterEach`
- When some tests in the class use MockedStatic, **MUST NOT** use class-level `@ExtendWith(MockitoExtension.class)`, change to `@Nested` manage as needed

### Reflection Replacement of `private static final`

```java
@BeforeEach void setUp() throws Exception {
    FileTypeChecker mock = mock(FileTypeChecker.class);
    when(mock.checkFileExtentionNames(anyString(), anyList())).thenReturn(true);
    Field f = CheckUtil.class.getDeclaredField("imageFileTypeChecker");
    f.setAccessible(true); f.set(null, mock);
}
```

### Converter Testing Strategy

Converters use `@Mapper` + `INSTANCE` pattern (→ java-guide.md §6), in unit tests:

- **MUST NOT** `@Mock` Converter, directly use real `INSTANCE` to execute mapping
- **MUST NOT** `when(converter.xxx()).thenReturn()` to set stubs
- If needing to simulate `dao.save()` backfilling ID and other MyBatis-Plus behaviors, use `thenAnswer`:

```java
// ✅ 正确：不 Mock Converter，模拟 DAO 回填 ID
when(articleDao.save(any())).thenAnswer(invocation -> {
    ArticleDO saved = invocation.getArgument(0);
    saved.setId(1L);
    return true;
});

// ❌ 禁止：Mock Converter
@Mock private ArticleConverter articleConverter;
when(articleConverter.toVO(any())).thenReturn(vo);
```

### Service Test Template

```java
@ExtendWith(MockitoExtension.class)
@DisplayName("ArticleService 单元测试")
class ArticleServiceTest {
    @Mock ArticleRepository articleRepository;
    @Mock AuthorRepository authorRepository;
    @InjectMocks ArticleServiceImpl articleService;

    @Nested @DisplayName("publish(Long, PublishArticleCMD)") class Publish {
        @Test @DisplayName("作者不存在抛 NotFoundException")
        void whenAuthorNotFound_throwsNotFoundException() {
            when(authorRepository.findById(1L)).thenReturn(Optional.empty());
            assertThatThrownBy(() -> articleService.publish(1L, new PublishArticleCMD()))
                .isInstanceOf({BizException}.class)
                .extracting(e -> (({BizException}) e).get{ResultCode}())
                .isEqualTo({ResultCode}.AUTHOR_NOT_FOUND);
        }
    }
}
```

---

## 7. Assertion Standards

**Unified AssertJ**, prohibit `assertEquals` / `assertTrue`:

```java
// ✅
assertThat(result.getData()).isNotNull();
assertThatThrownBy(() -> service.doSomething()).isInstanceOf({BizException}.class);
// ❌
assertEquals("测试文章", result.getData().getTitle());
```

---

## 8. Test Data

**MUST NOT** use real production data.

**Semantic Mock data**, field values reflect test intent; complex objects use Builder / factory methods:

```java
// ✅
Long existingAuthorId = 1001L, nonExistentAuthorId = 9999L;
// ❌
Long authorId = 123L;
```

---

## 9. Util Testing and JaCoCo Excludes

### 9.1. Basic Rules

- Pure utility classes **MUST NOT** use `@SpringBootTest`
- Line coverage ≥ 80%, **MUST** cover normal paths + catch blocks

### 9.2. Untestable Classes and JaCoCo Excludes

Untestable classes **MUST NOT** have tests written, and **MUST** be excluded from JaCoCo coverage, otherwise coverage drops causing gate false positives.

**MUST** configure same `<excludes>` list in both BOM coverage aggregation module and sub-module `pom.xml`'s `prepare-agent` + `report` executions, each with comment:

```xml
<!-- 示例：子模块 pom.xml -->
<excludes>
    <exclude>{basePackage}/util/HttpUtil*</exclude>          <!-- HTTP 依赖真实网络 -->
    <exclude>{basePackage}/util/spring/*</exclude>            <!-- 依赖 ApplicationContext -->
    <exclude>{basePackage}/util/constans/*</exclude>          <!-- 常量类无逻辑 -->
</excludes>
```

**Untestable classes and exclude quick reference**:

| Category | Typical classes | Exclude reason |
|----------|----------------|---------------|
| HTTP dependent | HttpUtil, ChatUtil | Requires real network, belongs to integration testing |
| Servlet dependent | ServletUtils, FileUtil | Depends on Request / MultipartFile |
| File system | ExcelUtil, WordUtil | Depends on POI local read/write |
| ZK connection | CuratorClient, IdMakerImpl | @Service + ZooKeeper |
| Spring context | SpringUtils, CommonToolConfig | Depends on container initialization |
| Vendored | ansi/*, SystemUtil | Non-original (Apache License) |
| No behavior logic | Constant classes, DTOs, VOs, Enums | Pure data carriers |

---

## 10. Prohibited Behaviors

| MUST NOT | Reason |
|----------|--------|
| Comment out assertions or `assertTrue(true)` placeholders | Masks failures |
| `@Disabled` to skip (unless FIXME + deadline) | Hides problems |
| Test contains `if` / `for` | Each branch independent method |
| Tests share mutable state | Must be independently runnable |
| Unit tests connect to real DB/Redis/ES | Use Mock instead |
| Class/method names contain Chinese/spaces/hyphens | Only English + numbers + underscores |
| Missing `@DisplayName` | Class/Nested/Test all must annotate |
| Same method tests not `@Nested` grouped | Organize by tested method |
