---
name: inventory-price-query
description: "统一查询产品价格与库存：先由 inventory_agent（Resolver + CONTAINS/向量 + ACCURATE table）解析产品并拉取库存，再按万鼎价格库与客户档位给价。触发于用户询问「查 xxx 价格和库存」「PVC 管 dn20 B 档」「这个产品有货吗」等场景。另一 LLM 可直接执行 scripts/run.py 得到统一 JSON。"
---

# 价格 + 库存统一查询（inventory-price-query）

## 触发条件

- 用户询问某产品「有没有货」「库存多少」「B 档价格」「价格和库存」。
- 上游流程需要同时获取价格与库存信息用于报价填充或补货决策。

## 目的与能力

与 **Agent Team version3** 完全一致的查询与选型逻辑：**先通过 match_quotation 匹配拿到 code，再用 code 查库存**。

1. **匹配/价格**：先 `match_quotation`（历史报价 + 万鼎字段匹配并集）得到候选或唯一 chosen；若无候选再 `match_wanding_price`（仅万鼎）。多候选时**必须**调用 `select_wanding_match`（LLM 选型），得到最终 chosen 与 `code`。
2. **查库存**：用上一步得到的 `code` 调用 `get_inventory_by_code(code)` 查库存；仅当未匹配到（无 code）时才退化为 `search_inventory(keywords)`（Resolver → table_agent）。
3. **拼装**：合并价格与库存结果输出统一 JSON。不写 Neon。

## 可执行脚本（供另一 LLM 直接调用）

执行 **scripts/run.py** 完成一次查询。脚本自动选择运行模式：

### 模式 1：HTTP 模式（推荐，与其他 3 个 Skill 一致）

设置 `BASE_URL` 环境变量指向已部署的 v3 后端即可，**无需本地 v3 源码**。

```bash
export BASE_URL=http://your-backend:8000   # 或 set BASE_URL=... (Windows)
pip install requests
echo '{"query":"直接 dn50 B档价格"}' | python scripts/run.py
```

- 依赖：Python 3 + `requests`
- 环境变量：只需 `BASE_URL`
- 内部走 `POST /api/query`，由服务端完整执行 match_quotation → select_wanding_match → get_inventory_by_code
- 输出中 `items[]` 字段不含结构化 code/price（agent 返回自然语言），完整信息在 `explanation`

### 模式 2：本地模式（有 v3 源码时）

不设 `BASE_URL`，脚本自动检测本地 v3 根目录。

```bash
# 在 Agent Team version3 根目录下
python /path/to/inventory-price-query/scripts/run.py <<< '{"query":"PVC 管 dn20 B 档"}'
```

- 依赖：本地 v3 源码 + 数据文件（价格库 Excel、映射表）+ 环境变量（ZHIPU_API_KEY、AOL_ACCESS_TOKEN 等）
- 输出中 `items[]` 含结构化 code / unit_price_incl_tax

---

**输入格式**（两种模式通用）：
- `{ "query": "自然语言描述" }`
- `{ "product_name": "...", "spec": "...", "customer_level": "B" }`
- 可选 `"use_quotation_union": true`（默认，本地模式有效）：先走历史+万鼎并集；`false` 则仅用万鼎。

## 输出格式

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "产品名称",
        "code": "物料编码",
        "customer_level": "B",
        "unit_price_incl_tax": 12.5,
        "unit_price_excl_tax": null,
        "available_qty": null,
        "specification": "dn20"
      }
    ],
    "explanation": "库存格式化文本，含具体可售数量，如：#C11 Tee dn20 库存有 50"
  }
}
```

> `available_qty` 固定为 `null`；实际库存数量以文本形式在 `explanation` 中。调用方 LLM 可直接读 `explanation` 展示给用户。

失败时：`{ "success": false, "error": { "code": "...", "message": "..." } }`。

## 内部调用约定（与 version3 一致）

1. **价格**：优先 `execute_inventory_tool("match_quotation", {"keywords": phrase, "customer_level": level})`（历史+万鼎并集）；若无候选再 `match_wanding_price`。可选入参 `use_quotation_union: false` 则仅用 `match_wanding_price`。
2. **选型**：当返回 `needs_selection` 且无 `chosen` 时，**必须**调用 `execute_inventory_tool("select_wanding_match", {"keywords": phrase, "candidates": candidates, "match_source": match_source})`，用其返回的 chosen；若 LLM 返回无把握（_suggestions），不取 candidates[0]，在 explanation 中说明「需人工确认」并附选项。
3. **库存**：**先匹配后查库存**——先通过 match_quotation（或 match_wanding_price + select_wanding_match）拿到 `code`；有 code 时调用 `get_inventory_by_code(code)`；无 code 时才调用 `search_inventory(keywords)`。
4. **禁止**：不得用 `run_inventory_agent` 以 JSON-forcing prompt 方式调用再解析 LLM 输出——这绕过 Resolver 且结果不稳定。

## 参考路径

| 说明 | 路径 |
|------|------|
| 入口脚本 | `.cursor/skills/inventory-price-query/scripts/run.py` |
| 工具执行 | `Agent Team version3/backend/tools/inventory/services/inventory_agent_tools.py` `execute_inventory_tool` |
| 询价并集 | `Agent Team version3/backend/tools/inventory/services/match_and_inventory.py` `match_quotation_union` |
| 万鼎定价 | `Agent Team version3/backend/tools/inventory/services/wanding_fuzzy_matcher.py` |
| LLM 选型 | `Agent Team version3/backend/tools/inventory/services/llm_selector.py` `llm_select_best` |
| Resolver | `Agent Team version3/backend/tools/inventory/services/resolver.py` |
| 选型 Skill | `.cursor/skills/wanding-select/SKILL.md` |
