# 四大 Skill 测试计划与所需信息

## 1. 建议的测试类型

| Skill | 单元测试（推荐） | 集成测试（可选） |
|-------|------------------|------------------|
| **inventory-price-query** | ① 输入校验：无效 JSON、缺 query/product_name → `invalid_input` / `missing_input`；② 无 V3 根目录时 → `no_v3_root`；③ 在 **mock** `run_inventory_agent` 与 `match_fuzzy_candidates` 下，校验 stdout JSON 结构（success, data.items, data.explanation） | 在 `AGENT_TEAM_V3_ROOT` 有效且后端/库存可用时，用最小 fixture 跑一次真实调用（可跳过） |
| **oos-shortage-register** | ① 解析：`_parse_oos_line` / `_parse_shortage_line` / `_is_num` 多种输入；② 输入校验：无效 JSON、unsupported_mode、无 text/records → no_records；③ **Mock requests**：校验 POST `/api/oos/add`、`/api/shortage/add` 的 URL/body，以及 stdout 的 inserted_count / message | 对真实 BASE_URL 发 1 条无货/1 条缺货（可跳过） |
| **quotation-register-from-dialog** | ① 解析：`_parse_quotation_lines` 及「报价单：」提取逻辑；② 输入校验：缺 raw_text、无报价行 → missing_raw_text / no_lines；③ **Mock requests**：POST `/api/quotation-drafts` 的 body 与 stdout 的 draft_id, line_count | 对真实 BASE_URL 提交 1 条报价草稿（可跳过） |
| **replenishment-register** | ① 解析：`_parse_replenishment_lines`（含「补货：」多行）；② 输入校验：缺 raw_text、无补货行 → missing_raw_text / no_lines；③ **Mock requests**：POST `/api/replenishment-drafts` 的 body 与 stdout 的 replenishment_id, line_count | 对真实 BASE_URL 提交 1 条补货草稿（可跳过） |

说明：

- **单元测试**：不依赖真实后端与 Agent Team version3 目录，可通过 mock HTTP 与（对 inventory-price-query）mock 内部 import 实现；部分逻辑需通过 subprocess 调用 `scripts/run.py` 并解析 stdout（如 inventory 的 no_v3_root）。
- **集成测试**：需要可用的 BASE_URL 和（仅 inventory-price-query）AGENT_TEAM_V3_ROOT；若你选择「跳过集成测试」，则只写单元 + mock 的用例。

---

## 2. What I need from you（请逐项填写）

请提供以下信息，以便实现并运行上述测试；填完后另一轮对话或 agent 可直接据此添加测试，无需再猜。

1. **后端 BASE_URL（集成测试）**
   - 填写可用的 Agent Team v3 后端地址，例如：`http://localhost:8000`；或
   - 写 **「跳过集成测试」**：只实现单元测试 + mock HTTP，不实现也不运行依赖真实后端的用例。

2. **Agent Team version3 路径（仅 inventory-price-query）**
   - 填写本机 Agent Team version3 项目根目录的绝对路径，例如：`D:\Projects\agent-jk\Agent Team version3`；或
   - 写 **「跳过 inventory-price-query 测试」**：不为此 Skill 编写/运行任何测试（包括 no_v3_root 的单元测试仍可写，不依赖该路径）。

3. **测试数据偏好**
   - **最小 fixture**：每个用例用最少数据（如一条产品名、一行「报价单」、一行「补货」、一行无货/缺货）—— 推荐；
   - 或 **真实/脱敏数据**：你提供一份脱敏的示例 JSON/文本，测试将基于此（请附上或说明文件路径）。

4. **测试代码放置位置**
   - **A**：每个 Skill 各自目录下，例如 `.cursor/skills/<skill-name>/tests/`（如 `tests/test_run.py`），或  
   - **B**：统一放在 `Agent Team version3/tests/` 下，用子目录或前缀区分四个 Skill，或  
   - **C**：在 agent-jk 根下建单一目录，如 `agent-jk/tests/skills/`，下面再分子目录。  
   请选 **A / B / C**（可附带你希望的子目录名，如 `tests/` 或 `skill_tests/`）。

5. **Python 与测试运行器**
   - 是否统一用 **pytest**？若否，请说明期望的 runner（如 unittest）。
   - Python 版本或虚拟环境是否有要求（如仅 3.10+、必须用 repo 内 venv）？若无，将按当前环境与 `scripts/run.py` 的 shebang 为准。

6. **其他约束**
   - 是否需要将测试加入 CI（如 GitHub Actions）？若是，请说明工作流文件路径或「由你后续添加」。
   - 是否有禁止的依赖（例如不希望测试里用 `responses` 或 `httpx` 做 HTTP mock）？若无，将默认用 `unittest.mock.patch("requests.post")` 或 `responses` 库（二选一，会注明）。

---

请按 1～6 直接回复（可复制上述小标题并填写）。收到后即可开始实现测试并给出运行命令与结果说明。
