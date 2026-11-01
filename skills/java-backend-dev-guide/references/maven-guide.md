# Maven Engineering Standards

> **Summary**
>
> - **Core constraint**: Dependency versions MUST be declared uniformly in BOM, sub-modules prohibited from writing `<version>`; project version uses `${revision}`; plugin versions/configuration MUST be declared uniformly in root POM pluginManagement, sub-modules prohibited from duplicating; APT declaration order: lombok → mapstruct → binding
> - **Key threshold**: Brand new environment must first run `mvn install -pl {build-module}`
> - **Common violations**: Sub-modules hardcoding dependency versions, plugin configuration duplicated in sub-modules, APT order errors causing MapStruct compilation failure

---

## 1. Version Management Rules

### 1.1. Dependency Versions Uniformly Declared in BOM

The BOM module (`{bomModule}/pom.xml`) is the **single source of version authority**. When sub-modules reference dependencies, they **MUST NOT** specify version numbers:

```xml
<!-- ✅ 子模块 — 只声明坐标 -->
<dependency>
    <groupId>org.mapstruct</groupId>
    <artifactId>mapstruct</artifactId>
</dependency>

<!-- ❌ 禁止在子模块中硬编码版本 -->
<dependency>
    <groupId>org.mapstruct</groupId>
    <artifactId>mapstruct</artifactId>
    <version>1.5.5.Final</version>
</dependency>
```

### 1.2. Plugin Versions Uniformly Declared in Root POM pluginManagement

The root POM's `<pluginManagement>` is the unified configuration source for all plugins. Sub-modules **MUST NOT** repeatedly specify `<version>`, `<configuration>`, `<executions>`:

```xml
<!-- 根 POM — 版本权威来源 -->
<pluginManagement>
    <plugins>
        <plugin>
            <artifactId>maven-enforcer-plugin</artifactId>
            <version>${maven-enforcer-plugin.version}</version>
            ...
        </plugin>
    </plugins>
</pluginManagement>

<!-- 子模块 — 只声明激活，不写版本 -->
<plugins>
    <plugin>
        <artifactId>maven-enforcer-plugin</artifactId>
    </plugin>
</plugins>
```

### 1.3. Project Version Uses `${revision}`

All module versions use `${revision}` placeholder, expanded to actual version number by `flatten-maven-plugin` during packaging phase:

```xml
<version>${revision}</version>
```

When upgrading versions, only modify the `<revision>` property in root POM, no need to modify sub-modules one by one.

### 1.4. BOM Import Does Not Propagate Properties

Maven `<scope>import</scope>` only affects `dependencyManagement` version resolution, it does not inject `<properties>` from the BOM into consumers. Version properties referenced in plugin configurations (such as `annotationProcessorPaths`) must exist in the current POM or its parent inheritance chain, and must remain **strictly consistent** with the BOM.

---

## 2. Plugin Inheritance Architecture

### 2.1. Design Principle

Follow the **single source, distribution via inheritance** principle:

- Root POM's `<pluginManagement>` defines complete plugin configuration
- Sub-modules automatically obtain it through Maven parent inheritance chain
- Sub-modules only need to declare `groupId + artifactId` to activate

### 2.2. Inheritance Chain

```
根 POM (pluginManagement 定义)
  │
  ├── 核心模块      ← 继承，自动激活
  ├── 工具模块      ← 同上
  ├── 数据访问层    ← 同上
  │
  └── 业务模块 POM (继承，声明激活)
        ├── 模块 A
        └── 模块 B
```

### 2.3. Sub-modules Prohibited from Repeating Declarations

Sub-modules **MUST NOT** repeatedly declare:

- Plugin versions (inherited from pluginManagement)
- Plugin configurations (annotationProcessorPaths, rulesets, etc. inherited from pluginManagement)
- Plugin executions and dependencies (inherited from pluginManagement)
- Quality gate properties (inherited from root POM properties)
- `dev` profile (inherited from root POM profiles)

---

## 3. Annotation Processor (APT) Configuration

### 3.1. Declaration Order (MUST Follow)

`lombok` MUST be ordered **before** `mapstruct-processor`, configured uniformly in root POM's `maven-compiler-plugin` pluginManagement, sub-modules automatically obtain through inheritance:

```xml
<annotationProcessorPaths>
    <!-- 1. lombok 先生成 getter/setter/builder -->
    <path>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <version>${lombok.version}</version>
    </path>
    <!-- 2. mapstruct-processor 再读取 getter/setter 生成映射代码 -->
    <path>
        <groupId>org.mapstruct</groupId>
        <artifactId>mapstruct-processor</artifactId>
        <version>${mapstruct.version}</version>
    </path>
    <!-- 3. 绑定器：确保两者协作时的 classloader 兼容性 -->
    <path>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok-mapstruct-binding</artifactId>
        <version>${lombok-mapstruct-binding.version}</version>
    </path>
</annotationProcessorPaths>
```

Incorrect ordering will cause MapStruct generated mapping methods to report "cannot find attribute" compilation errors.

---

## 4. Dev / CI Dual-Mode Build

Root POM defines the `dev` profile, and sub-modules obtain it through the inheritance chain. **Default build enables all quality gates**, pass `-Ddev` to activate local development mode and disable gates for speed.

| Scenario | Command | Quality gates | sources.jar |
|----------|---------|--------------|-------------|
| Normal build (default) | `mvn clean install -DskipTests` | ✓ All enabled | ✓ Generated |
| Local development | `mvn clean install -DskipTests -Ddev` | ✗ All disabled | ✗ Skipped |

### 4.1. Tasks Disabled by dev Profile

| Task | Corresponding configuration | Reason |
|------|---------------------------|--------|
| Dependency convergence check | `enforce.enabled=false` | Significant time cost with large dependency trees |
| Checkstyle style check | `checkstyle.validate.disabled=true` | Fast local iteration builds |
| PMD P3C check | `pmd.enforce.validate=false` | Fast local iteration builds |
| sources.jar packaging | `maven.source.skip=true` | Not needed for local development |

> For quality gate plugin details, see → quality-gate.md §2.

---

## 5. Common Build Commands

```bash
# ⚠️ 全新环境首次克隆后，执行一次引导安装
mvn install -pl {build-module} -DskipTests

# 1. 正常构建（所有门禁启用）
mvn clean install -DskipTests

# 2. 本地开发模式（关闭门禁）
mvn clean install -DskipTests -Ddev
```

### 5.1. Quality Gate Related Commands

```bash
# 仅运行 checkstyle 检查
mvn checkstyle:check

# 仅运行 PMD 检查
mvn pmd:check

# 本地开发模式：关闭全部门禁
mvn clean install -DskipTests -Ddev

# 单独跳过 checkstyle（仅调试期临时使用）
mvn clean install -DskipTests -Dcheckstyle.validate.disabled=true

# 单独跳过 PMD（仅调试期临时使用）
mvn clean install -DskipTests -Dpmd.enforce.validate=false
```
