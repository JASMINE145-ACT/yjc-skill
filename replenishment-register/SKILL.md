---
name: replenishment-register
description: "解析「补货：产品名/编码 数量」等自然语言，登记到 Neon 补货草稿表（ReplenishmentDraft/Line）。仅做解析与落库，不负责审批或实际改库存。触发于用户输入包含「补货：」的文本。另一 LLM 可直接执行 scripts/run.py 得到 replenishment_id/line_count。"
---

# 补货登记落库（replenishment-register）

## 触发条件

- 文本中出现 **「补货：」**，后跟产品名称或编码及数量（可多行/多条）。
- 用户明确要求「登记补货」「把补货需求记到系统」等。

## 目的与能力

解析用户输入中的 **「补货：」** 片段（如「补货：PVC 管 dn20 100」「补货：ITEM12345 数量 50」），将产品与数量登记到 **Neon 补货相关表**（`replenishment_drafts`、`replenishment_draft_lines`），供 Agent Team 平台补货页面使用。本 Skill 只做**解析 + 草稿落库**，不负责审批或实际库存修改。

## 可执行脚本（供另一 LLM 直接调用）

执行 **scripts/run.py** 解析「补货：...」文本并落库。

- **输入**：stdin 或第一参数文件，JSON：`{ "raw_text": "补货：PVC 管 dn20 100\n补货：ITEM123 50", "name"?, "warehouse"?, "priority"? }`
- **输出**：stdout `{ "success", "data": { "replenishment_id", "draft_no", "line_count", "message" }, "error"? }`
- **环境**：`BASE_URL`（默认 `http://localhost:8000`）；依赖 `requests`（`pip install requests`）。
- **可移植性**：可复制到任意目录使用，只需设置 `BASE_URL`，不依赖 agent-jk 或 v3 目录结构。

```bash
echo '{"raw_text":"补货：PVC 管 dn20 100\n补货：8030020580 50"}' | python scripts/run.py
```

## 解析规则

- **产品**：`补货：` 后至末尾数量前的部分，可为产品名称或物料编码（10 位数字可直接视为 code）。
- **数量**：从行末尾数字提取（整数）。
- 支持多行多条「补货：...」；每条解析为一行 `{ product_or_code, quantity }`。
- 同时识别中文冒号「补货：」和英文冒号「补货:」。

## 输入

| 字段 | 必填 | 说明 |
|------|------|------|
| raw_text | 是 | 包含「补货：」片段的文本（可多条） |
| name | 否 | 草稿名称，默认 `补货-{时间}` |
| warehouse, expected_date, priority, remark | 否 | 仓库、期望日期、优先级、备注（若后端 API 支持则写入） |

## 输出

```json
{
  "success": true,
  "data": {
    "replenishment_id": 7,
    "draft_no": "RP-20250308-0001",
    "line_count": 2,
    "message": "已登记补货草稿，共 2 行。"
  }
}
```

失败时：`{ "success": false, "error": { "code": "...", "message": "..." } }`。Neon 中 `replenishment_drafts` 与 `replenishment_draft_lines` 已有记录。

## 内部实现约定

1. **解析**：识别所有「补货：/补货:」片段，提取产品（名称或 code）和数量。产品名可后续由后端通过 inventory_agent 解析为 code。

2. **落库**：HTTP **POST /api/replenishment-drafts** Body `{ "lines": [ { "product_or_code", "quantity" }, ... ], "name", "warehouse"?, ... }`；后端调用 `preview_replenishment_lines` 做产品解析与库存预览，再 `DataService.insert_replenishment_draft`。

3. **边界**：只创建补货草稿；不直接修改库存，不执行 confirm/审批逻辑。

## 参考路径

| 说明 | 路径 |
|------|------|
| 补货 API | `Agent Team version3/backend/server/api/routes_quotation.py` POST /api/replenishment-drafts |
| 补货预览 | `Agent Team version3/backend/tools/inventory/services/replenishment_preview.py` `preview_replenishment_lines` |
| DataService 补货落库 | `Agent Team version3/backend/tools/oos/services/data_service.py` `insert_replenishment_draft` |
| 后端与表映射 | `Agent Team version3/doc/Neon_Skill_后端与表映射.md` |
