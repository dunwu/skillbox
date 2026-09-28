# 单元测试规范

> **核心约束**：TDD；DomainService 行覆盖率 100%、整体 ≥ 80%；AssertJ only；Mock 仅外部依赖
>
> **结构约束**：`@Nested` 按被测方法分组；类名/方法名 snake_case（仅英文+数字）；全部标注 `@DisplayName`
>
> **关键阈值**：DomainService 100%、Service/Controller/Util ≥ 80%、单 task 通过率 100%
>
> **常见违规**：先实现后补测试、测试含 if/for、共享可变状态、@Disabled 跳过、Mock 过度

> v2.4 | 2026-06-10 | SKILL ≥ v1.4.0

---

## 0 技术选型

> 版本来源：项目 BOM。**MUST NOT** 擅自升级。

| 库 | 用途 |
|---|---|
| Spring Boot Starter Test | 测试基础设施（JUnit 5、Mockito 等） |
| JUnit Jupiter | 测试引擎与注解 |
| AssertJ Core | 流式断言（唯一允许） |
| Mockito (Core / Inline / Jupiter) | Mock 框架（含 mockStatic） |
| JaCoCo Maven Plugin | 覆盖率采集与门禁 |
| Maven Surefire | 测试执行引擎 |
| Maven PMD | 静态分析 |
| Maven Checkstyle | 代码风格检查 |

> 具体版本号由项目级 Skill 或 BOM 定义。

---

## 1 测试策略

```
     ▲▲▲▲▲ 单元测试（大量，业务逻辑）
       ▲▲▲ Service 成成测试（中等，跨层交互）
        ▲  E2E / 集成测试（少量，关键链路）
```

**单元测试为主**：不依赖 DB/Redis/ES，快速稳定可重复。

---

## 2 TDD 工作流

**先写测试再写实现。** task 测试未完成前不得标记完成。

```
验收条件 → Red（失败测试） → Green（最小实现） → Refactor → 重复至全覆盖
```

**MUST NOT** 先实现后补测试——退化为实现描述，失去验证意义。

---

## 3 覆盖率要求

| 层 | 重点 | 行覆盖率 |
|---|---|---|
| DomainService | 业务规则、分支、异常 | **100%** |
| ApplicationService | 编排逻辑、事务边界 | ≥ 80% |
| Controller | 参数校验、路由、响应格式 | ≥ 80% |
| Util | 公共方法、边界、异常路径 | ≥ 80% |
| Repository / DAO | 集成测试覆盖 | — |
| 整体模块 | — | **≥ 80%** |

---

## 4 命名规范

- **类名**：`{被测类名}Test`，仅英文字母+数字
- **方法名**：`{被测方法}_{场景}_{预期}`，snake_case，仅英文+数字+下划线
- **@DisplayName**：类/`@Nested`/`@Test` 全部标注，中文描述意图

```java
// ✅ 方法名
void encrypt_whenPlainTextIsNull_returnsNull()

// ❌
void testEncrypt()              // 缺场景/预期
void 加密_空字符串_返回null()    // 含中文
void encrypt-null-input()       // 连字符分隔
```

---

## 5 组织结构

**MUST** 按被测方法用 `@Nested` 分组，内部类名 PascalCase；重载追加参数类型区分。

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

## 6 Mock 策略

### 原则

- **只 Mock 外部依赖**（Repository、RPC、HTTP、配置中心），**禁 MOCK 被测对象自身**
- Mock 越多 → 耦合越紧 → 重构成本越高
- DomainService / ApplicationService 不得全部 Mock 掉

### 工具选择

| 场景 | 工具 |
|---|---|
| 标准 Mock | `@ExtendWith(MockitoExtension.class)` + `@Mock` / `@InjectMocks` |
| 静态方法 | `MockedStatic`（谨慎，优先重构为可注入） |
| Spring 上下文 | `@SpringBootTest`（仅集成测试） |

### MockedStatic

- 用 `Mockito.withSettings().lenient()` 创建，避免 `InvalidUseOfMatchers`
- **MUST** `@AfterEach` 关闭 `mockStatic.close()`
- 类内部分测试用 MockedStatic 时，**MUST NOT** 类级 `@ExtendWith(MockitoExtension.class)`，改为 `@Nested` 内按需管理

### 反射替换 `private static final`

```java
@BeforeEach void setUp() throws Exception {
    FileTypeChecker mock = mock(FileTypeChecker.class);
    when(mock.checkFileExtentionNames(anyString(), anyList())).thenReturn(true);
    Field f = CheckUtil.class.getDeclaredField("imageFileTypeChecker");
    f.setAccessible(true); f.set(null, mock);
}
```

### Service 测试模板

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

## 7 断言规范

**统一 AssertJ**，禁 `assertEquals` / `assertTrue`：

```java
// ✅
assertThat(result.getData()).isNotNull();
assertThatThrownBy(() -> service.doSomething()).isInstanceOf({BizException}.class);
// ❌
assertEquals("测试文章", result.getData().getTitle());
```

---

## 8 测试数据

> 禁止真实生产数据（《阿里巴巴 Java 开发手册》§四）

**语义化 Mock 数据**，字段值反映测试意图；复杂对象用 Builder / 工厂方法：

```java
// ✅
Long existingAuthorId = 1001L, nonExistentAuthorId = 9999L;
// ❌
Long authorId = 123L;
```

---

## 9 Util 测试与 JaCoCo excludes

### 9.1 基本规则

- **MUST NOT** 纯工具类使用 `@SpringBootTest`
- 行覆盖率 ≥ 80%，**MUST** 覆盖正常路径 + catch 块

### 9.2 不可测试类与 JaCoCo excludes

不可测试类既不编写测试，也 **MUST** 从 JaCoCo 覆盖率中排除，否则拉低覆盖率导致门禁误报。

**MUST** 在 BOM 覆盖率聚合模块与子模块 `pom.xml` 的 `prepare-agent` + `report` 两个 execution 中配置相同的 `<excludes>` 列表，每条附注释：

```xml
<!-- 示例：子模块 pom.xml -->
<excludes>
    <exclude>{basePackage}/util/HttpUtil*</exclude>          <!-- HTTP 依赖真实网络 -->
    <exclude>{basePackage}/util/spring/*</exclude>            <!-- 依赖 ApplicationContext -->
    <exclude>{basePackage}/util/constans/*</exclude>          <!-- 常量类无逻辑 -->
</excludes>
```

**不可测试类与 exclude 速查**：

| 分类 | 典型类 | exclude 原因 |
|---|---|---|
| HTTP 依赖 | HttpUtil、ChatUtil | 需真实网络，属集成测试 |
| Servlet 依赖 | ServletUtils、FileUtil | 依赖 Request / MultipartFile |
| 文件系统 | ExcelUtil、WordUtil | 依赖 POI 本地读写 |
| ZK 连接 | CuratorClient、IdMakerImpl | @Service + ZooKeeper |
| Spring 上下文 | SpringUtils、CommonToolConfig | 依赖容器初始化 |
| Vendored | ansi/*、SystemUtil | 非自研（Apache License） |
| 无行为逻辑 | 常量类、DTO、VO、Enum | 纯数据载体 |

---

## 10 禁止行为

| MUST NOT | 原因 |
|---|---|
| 注释断言或 `assertTrue(true)` 占位 | 掩盖失败 |
| `@Disabled` 跳过（除非 FIXME + 截止日期） | 隐藏问题 |
| 测试内含 `if` / `for` | 每分支独立方法 |
| 测试间共享可变状态 | 必须独立可运行 |
| 单元测试连真实 DB/Redis/ES | 用 Mock 替代 |
| 类名/方法名含中文/空格/连字符 | 仅英文+数字+下划线 |
| 缺少 `@DisplayName` | 类/Nested/Test 全标注 |
| 同方法测试未 `@Nested` 分组 | 按被测方法组织 |

