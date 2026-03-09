---
name: oos-shortage-register
description: "将无货/缺货信息登记到 Neon 数据库对应表（无货表、缺货表）。支持从报价单文件或文字说明登记；只做写入，不含审批。触发于用户说「登记无货/缺货」「把这些缺货记到系统」等。另一 LLM 可直接执行 scripts/run.py（仅支持 oos_from_text、shortage_from_text）得到 JSON。"
---

# 无货/缺货登记落库（oos-shortage-register）

## 触发条件

- 用户明确表示要「登记无货」「登记缺货」「把这些缺货记录记到系统里」。
- 上游流程（如报价单解析、run_quotation_agent）已产生无货/缺货记录，需要落库到 Neon。

## 目的与能力

将所有「无货/缺货」登记统一写入 **Neon 对应表**（无货表 `out_of_stock_records`、缺货表 `shortage_records`），无论入口是报价单文件还是纯文字。本 Skill 只做**登记/写入**，不包含审批或邮件策略；审批由 Agent Team 平台或其它流程处理。

## 可执行脚本（供另一 LLM 直接调用）

执行 **scripts/run.py** 完成「文字/结构化记录」登记（不包含从 Excel 文件解析；文件入口见内部约定）。

- **输入**：stdin 或第一参数文件，JSON：
  `{ "mode": "oos_from_text" | "shortage_from_text", "text"?: "一行或每行一条", "records"?: [{ "product_name", "specification?", "quantity?", "available_qty?" }] }`
- **输出**：stdout `{ "success", "data": { "inserted_count", "message" }, "error"? }`
- **环境**：`BASE_URL`（默认 `http://localhost:8000`）指向 Agent Team v3 后端；依赖 `requests`（`pip install requests`）。
- **可移植性**：可复制到任意目录使用，只需设置 `BASE_URL`，不依赖 agent-jk 或 v3 目录结构。

```bash
echo '{"mode":"oos_from_text","text":"PVC 管 dn20 无货 100"}' | python scripts/run.py
```

**oos_from_file** 不通过本脚本：使用 run_quotation_agent + `persist_out_of_stock_records`（见内部约定）。

## 输入

| 字段 | 必填 | 说明 |
|------|------|------|
| mode | 是 | `"oos_from_file"` \| `"oos_from_text"` \| `"shortage_from_text"` |
| file_path / file_name | mode=oos_from_file 时必填 | 报价单/询价文件路径或文件名 |
| text / records | mode 为 text 时必填 | 一句或几句无货/缺货描述；或已解析的 `records` 数组 |
| session_id, source, operator | 否 | 会话、来源（control-ui/企微/邮件）、操作人 |

## 输出

```json
{
  "success": true,
  "data": {
    "inserted_count": 3,
    "message": "已登记 3 条。"
  }
}
```

失败时：`{ "success": false, "error": { "code": "...", "message": "..." } }`。Neon 中对应表已完成插入（以后端返回为准）。

## 内部实现约定（必须复用，禁止绕开）

1. **无货记录**
   - **文件入口**：优先调用 `persist_out_of_stock_records(file_name, records, sheet_name, file_path)`，或 HTTP **POST /api/oos/add** Body `{ "product_name", "specification?", "quantity?", "unit?" }`。
   - 写入表：`out_of_stock_records`（DataService）；`persist_out_of_stock_records` 同步到云端 `oos_records`。

2. **缺货记录**
   - 复用 `DataService.insert_shortage_records`，或 HTTP **POST /api/shortage/add** Body `{ "product_name", "specification?", "quantity?", "available_qty?" }`。
   - 写入表：`shortage_records`。

3. **禁止**：绕过上述服务直接改表结构；不得仅写本地文件不写 Neon。

## 参考路径

| 说明 | 路径 |
|------|------|
| 无货持久化 | `Agent Team version3/backend/tools/oos/services/quotation_agent_tool.py` `persist_out_of_stock_records` |
| 缺货写入 | `Agent Team version3/backend/tools/oos/services/data_service.py` `insert_shortage_records` |
| OOS API | `Agent Team version3/backend/server/api/routes_oos.py`（/api/oos/add、/api/shortage/add） |
| 后端与表映射 | `Agent Team version3/doc/Neon_Skill_后端与表映射.md` |
