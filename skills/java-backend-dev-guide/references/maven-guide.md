# Maven 工程规范

> **摘要**
>
> - **核心约束**：依赖版本 MUST 在 BOM 统一声明、子模块禁写 `<version>`；项目版本用 `${revision}`；插件版本/配置 MUST 在根 POM pluginManagement 统一声明、子模块禁重复；APT 声明顺序 lombok → mapstruct → binding
> - **关键阈值**：全新环境须先 `mvn install -pl {build-module}`
> - **常见违规**：子模块硬编码依赖版本、插件配置在子模块重复声明、APT 顺序错误导致 MapStruct 编译失败

> **版本**：v1.0 | 最后更新：2026-06-08 | 适用 SKILL 版本：≥ v1.0.0

---

## 1. 版本管理规则

### 1.1. 依赖版本统一在 BOM 中声明

BOM 模块（`{bomModule}/pom.xml`）是**唯一版本权威来源**。子模块引用依赖时**MUST NOT** 指定版本号：

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

### 1.2. 插件版本统一在根 POM pluginManagement 中声明

根 POM 的 `<pluginManagement>` 是所有插件的统一配置来源。子模块**MUST NOT** 重复指定 `<version>`、`<configuration>`、`<executions>`：

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

### 1.3. 项目版本用 `${revision}`

所有模块版本使用 `${revision}` 占位符，由 `flatten-maven-plugin` 在打包阶段展开为实际版本号：

```xml
<version>${revision}</version>
```

升级版本时只需修改根 POM 的 `<revision>` property，无需逐一修改子模块。

### 1.4. BOM import 不传播 properties

Maven `<scope>import</scope>` 只影响 `dependencyManagement` 版本解析，不会将 BOM 中的 `<properties>` 注入消费方。插件配置（如 `annotationProcessorPaths`）引用的版本属性必须存在于当前 POM 或其 parent 继承链中，并与 BOM **严格保持一致**。

---

## 2. 插件继承架构

### 2.1. 设计原则

遵循**单一来源、继承分发**原则：

- 根 POM 的 `<pluginManagement>` 定义完整插件配置
- 子模块通过 Maven parent 继承链自动获得
- 子模块只需声明 `groupId + artifactId` 即可激活

### 2.2. 继承链

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

### 2.3. 子模块禁止重复声明

子模块 **MUST NOT** 重复声明：

- 插件版本（从 pluginManagement 继承）
- 插件配置（annotationProcessorPaths、rulesets 等从 pluginManagement 继承）
- 插件 executions 和 dependencies（从 pluginManagement 继承）
- 质量门禁属性（从根 POM properties 继承）
- `dev` profile（从根 POM profiles 继承）

---

## 3. 注解处理器（APT）配置

### 3.1. 声明顺序（MUST 遵守）

`lombok` MUST 排在 `mapstruct-processor` **之前**，由根 POM 的 `maven-compiler-plugin` pluginManagement 统一配置，子模块通过继承自动获得：

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

顺序错误会导致 MapStruct 生成的映射方法报"找不到属性"编译错误。

---

## 4. dev / CI 双模式构建

根 POM 通过继承链获得 `dev` profile。**默认构建开启全部质量门禁**，传入 `-Ddev` 激活本地开发模式后关闭门禁以提速。

| 场景             | 命令                                  | 质量门禁   | sources.jar |
| ---------------- | ------------------------------------- | ---------- | ----------- |
| 正常构建（默认） | `mvn clean install -DskipTests`       | ✓ 全部开启 | ✓ 生成      |
| 本地开发         | `mvn clean install -DskipTests -Ddev` | ✗ 全部关闭 | ✗ 跳过      |

### 4.1. dev profile 关闭的任务

| 任务                | 对应配置                            | 原因               |
| ------------------- | ----------------------------------- | ------------------ |
| 依赖收敛检查        | `enforce.enabled=false`             | 大依赖树时耗时明显 |
| Checkstyle 风格检查 | `checkstyle.validate.disabled=true` | 本地迭代快速构建   |
| PMD P3C 检查        | `pmd.enforce.validate=false`        | 本地迭代快速构建   |
| sources.jar 打包    | `maven.source.skip=true`            | 本地开发无需       |

> 质量门禁插件详情见 → quality-gate.md §2。

---

## 5. 常用构建命令

```bash
# ⚠️ 全新环境首次克隆后，执行一次引导安装
mvn install -pl {build-module} -DskipTests

# 1. 正常构建（所有门禁启用）
mvn clean install -DskipTests

# 2. 本地开发模式（关闭门禁）
mvn clean install -DskipTests -Ddev
```

### 5.1. 质量门禁相关命令

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

