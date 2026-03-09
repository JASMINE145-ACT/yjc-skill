---
name: quotation-register-from-dialog
description: "当对话中出现「报价单：」段落时，将后续文本解析为报价明细行并登记到 Neon 报价草稿表（QuotationDraft/Line）。仅做解析与落库，不做审批。检测到 pattern 即调用，无需用户再点 run。另一 LLM 可直接执行 scripts/run.py 得到 draft_id/line_count。"
---

# 对话中「报价单：」自动登记（quotation-register-from-dialog）

## 触发条件

- 在对话/文本块中检测到以 **「报价单：」** 开头的片段（或等价表述，如「quotation:」后跟中文说明）。
- 检测到即应调用本 Skill，**无需用户再点 run**；仅负责解析与写入 Neon。

## 目的与能力

当文本中出现 **「报价单：」** 开头的段落时，将后面的内容解析为「报价明细行」，**登记到 Neon 报价草稿表**（`quotation_drafts`、`quotation_draft_lines`）。本 Skill 只做**结构化 + 落库**，不做价格审批、不生成正式订单；审批由平台或其它 Agent 处理。

## 可执行脚本（供另一 LLM 直接调用）

执行 **scripts/run.py** 将「报价单：...」文本解析并落库。

- **输入**：stdin 或第一参数文件，JSON：`{ "raw_text": "报价单：\n行1\n行2...", "customer_level"?, "source"? }`
- **输出**：stdout `{ "success", "data": { "draft_id", "draft_no", "line_count", "message" }, "error"? }`
- **环境**：`BASE_URL`（默认 `http://localhost:8000`）；依赖 `requests`（`pip install requests`）。
- **可移植性**：可复制到任意目录使用，只需设置 `BASE_URL`，不依赖 agent-jk 或 v3 目录结构。

```bash
echo '{"raw_text":"报价单：\nPVC 管 dn20 100\n弯头 dn25 50"}' | python scripts/run.py
```

## 输入

| 字段 | 必填 | 说明 |
|------|------|------|
| raw_text | 是 | 包含「报价单：」段的完整文本（或已截取的该段落） |
| customer_level, session_id, customer_id, source | 否 | 客户档位、会话、客户 ID、来源（聊天/邮件等） |

## 输出

```json
{
  "success": true,
  "data": {
    "draft_id": 42,
    "draft_no": "QT-20250308-0001",
    "line_count": 5,
    "message": "已登记报价草稿，共 5 行。"
  }
}
```

失败时：`{ "success": false, "error": { "code": "...", "message": "..." } }`。Neon 中 `quotation_drafts` 与 `quotation_draft_lines` 已有对应记录。

## 内部实现约定

1. **解析**
   - 从 `raw_text` 中提取「报价单：」后的内容，按行或分隔符拆成多条明细。
   - 每行抽取：产品名称（整行去掉末尾数量后的部分）、数量（末尾数字）。
   - 解析失败的行以 warning 形式返回，不阻塞整体落库。

2. **落库**
   - HTTP **POST /api/quotation-drafts** Body `{ "name", "source": "nl", "lines": [ { "product_name", "specification", "qty", ... } ] }`。
   - 或 **DataService.insert_quotation_draft(name, source="nl", file_path=None, lines=...)**。
   - 禁止仅生成本地文件而不写 Neon。

3. **边界**
   - 不做价格审批、折扣策略判断。
   - 不主动触发发邮件或生成正式 Work 任务；只返回 `draft_id` / `draft_no` 供后续流程使用。

## 参考路径

| 说明 | 路径 |
|------|------|
| 报价草稿 API | `Agent Team version3/backend/server/api/routes_quotation.py` POST /api/quotation-drafts |
| DataService 报价落库 | `Agent Team version3/backend/tools/oos/services/data_service.py` `insert_quotation_draft` |
| 后端与表映射 | `Agent Team version3/doc/Neon_Skill_后端与表映射.md` |
