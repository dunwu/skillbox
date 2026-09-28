# API 文档模板

> **适用范围**：RESTful API、gRPC API、GraphQL API 等接口文档。
> **使用提示**：本模板以 RESTful API 为例，gRPC / GraphQL 可替换对应协议细节。

## 概述

**章节内容意图**：提供 API 的全局视图，包括版本策略、认证方式、基础 URL、速率限制等，帮助调用方快速理解接入规范。

**规范化写作指南**：

- **基础信息**：API 名称、当前版本、基础 URL（区分环境）。
- **认证方式**：说明认证协议（OAuth 2.0 / API Key / JWT）、Token 获取方式、有效期。
- **版本策略**：URL 路径版本（`/v1/`）或 Header 版本，版本生命周期。
- **通用约定**：日期时间格式、字符编码、分页方式、排序方式、ID 生成规则。
- **速率限制**：限额阈值、限流响应码、限流 Header。
- **错误响应结构**：统一错误响应格式定义。
- **幂等性约定**：写操作（POST / PUT / DELETE）的幂等策略。

**模板示例**：

- **API 名称**：订单服务 API（Order Service API）
- **版本**：v1
- **基础 URL**：
  - 生产环境：`https://api.example.com/v1`
  - 预发环境：`https://api-staging.example.com/v1`
- **认证**：OAuth 2.0 Bearer Token，通过 `/oauth/token` 获取，有效期 7200 秒。
- **通用约定**：
  - 日期时间：ISO 8601（`2026-06-01T08:30:00Z`）
  - 字符编码：UTF-8
  - 分页：`?page=1&size=20`，响应含 `total`、`pages` 字段
  - ID：雪花算法生成的 64 位整数
- **速率限制**：1,000 次/分钟，超出返回 `429 Too Many Requests`，响应 Header 含 `X-RateLimit-Remaining`。
- **幂等性**：
  - 创建类接口通过 `Idempotency-Key` Header 保证幂等，Key 有效期 24 小时。
  - 更新/删除类接口通过资源版本号或条件请求（如 `If-Match`）保证幂等。
- **统一错误响应**：

  ```json
  {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "requestId": "req-unique-id",
    "timestamp": "2026-06-01T08:30:00Z"
  }
  ```

## 接口列表

**章节内容意图**：提供所有接口的全景索引，方便快速定位。

**模板示例**：

| 方法 | 路径 | 说明 | 认证 |
|:-----|:-----|:-----|:-----|
| POST | `/orders` | 创建订单 | 需要 |
| GET | `/orders/{id}` | 查询订单详情 | 需要 |
| GET | `/orders` | 查询订单列表 | 需要 |
| PUT | `/orders/{id}/status` | 更新订单状态 | 需要 |
| DELETE | `/orders/{id}` | 取消订单 | 需要 |

## 接口详情

**章节内容意图**：逐一描述每个接口的完整定义，包括请求参数、响应结构、错误码、示例。

**规范化写作指南**：

- 每个接口使用统一的二级标题格式：`方法 路径 — 简要说明`。
- 必须包含：接口说明、请求参数（路径 / 查询 / 请求体）、响应结构（成功 / 失败）、错误码表、请求 / 响应示例。
- 参数表必须包含：字段名、类型、必填、约束 / 校验规则、说明。

**模板示例**：

### POST /orders — 创建订单

创建一笔新订单。成功返回 `201 Created`，订单进入"待支付"状态。

**请求参数（Request Body）**：

| 字段 | 类型 | 必填 | 约束 | 说明 |
|:-----|:-----|:-----|:-----|:-----|
| productId | string | 是 | 非空，最大 64 字符 | 商品 ID |
| quantity | integer | 是 | ≥ 1，≤ 999 | 购买数量 |
| couponCode | string | 否 | 最大 32 字符 | 优惠码 |
| idempotencyKey | string | 是 | UUID，最大 64 字符 | 幂等键，24 小时内同一 Key 返回相同结果 |

**请求示例**：

```json
{
  "productId": "PROD-12345",
  "quantity": 2,
  "couponCode": "SUMMER2026"
}
```

**成功响应（201 Created）**：

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| orderId | string | 订单 ID |
| status | string | 订单状态：`PENDING_PAYMENT` |
| amount | decimal | 订单金额（元） |
| createdAt | string | 创建时间（ISO 8601） |

**响应示例**：

```json
{
  "orderId": "ORD-20260601-00001",
  "status": "PENDING_PAYMENT",
  "amount": 299.00,
  "createdAt": "2026-06-01T08:30:00Z"
}
```

**错误码**：

| HTTP 状态码 | 错误码 | 说明 |
|:------------|:-------|:-----|
| 400 | INVALID_PARAMETER | 请求参数校验失败 |
| 401 | UNAUTHORIZED | 认证失败或 Token 过期 |
| 404 | PRODUCT_NOT_FOUND | 商品不存在 |
| 409 | CONFLICT | 业务冲突（如库存不足、重复提交） |
| 429 | RATE_LIMITED | 请求频率超限 |

## 通用错误码

| HTTP 状态码 | 错误码 | 说明 |
|:------------|:-------|:-----|
| 400 | BAD_REQUEST | 通用请求参数错误 |
| 401 | UNAUTHORIZED | 未认证或 Token 无效 |
| 403 | FORBIDDEN | 无权限访问该资源 |
| 404 | NOT_FOUND | 资源不存在 |
| 409 | CONFLICT | 资源冲突 |
| 422 | UNPROCESSABLE_ENTITY | 语义校验失败 |
| 429 | RATE_LIMITED | 请求频率超限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 数据模型

**章节内容意图**：定义 API 涉及的核心数据结构，供接口章节引用，避免重复定义。

**模板示例**：

### Order（订单）

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| orderId | string | 订单唯一标识 |
| userId | string | 下单用户 ID |
| productId | string | 商品 ID |
| quantity | integer | 购买数量 |
| amount | decimal | 订单金额（元） |
| status | enum | 状态枚举：`PENDING_PAYMENT` / `PAID` / `SHIPPED` / `CANCELLED` |
| createdAt | string | 创建时间 |
| updatedAt | string | 最后更新时间 |

## 变更记录

按时间倒序记录接口变更。每次变更需说明：版本号、日期、变更类型（新增 / 修改 / 废弃）、变更内容、兼容性影响。

| 版本 | 日期 | 变更类型 | 变更说明 | 兼容性 |
|:-----|:-----|:---------|:---------|:-------|
| v1.2.0 | 2026-06-01 | 新增 | 创建订单接口新增 `couponCode` 参数 | 向后兼容 |
| v1.1.0 | 2026-05-15 | 修改 | 订单列表接口新增时间范围过滤参数 | 向后兼容 |
| v1.0.0 | 2026-04-01 | 新增 | 初始版本发布 | - |
