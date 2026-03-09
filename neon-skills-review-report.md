# Neon 四大 Skill 审查报告：计划符合性 + 可移植性

**审查依据**：`c:\Users\m1774\.cursor\plans\neon-skills-refactor_1aebe1e0.plan.md`  
**审查对象**：inventory-price-query、oos-shortage-register、quotation-register-from-dialog、replenishment-register（各 SKILL.md + scripts/run.py）

---

## A) 计划符合性（Plan compliance）

### A.1 各 Skill 与计划二～五的逐项对照

| 计划章节 | Skill | 目的/触发 | 输入/输出契约 | 内部约定（后端/Neon） | 偏差说明 |
|----------|--------|------------|----------------|------------------------|----------|
| **二** | inventory-price-query | ✓ 目的与触发与计划一致 | ✓ 自然语言/结构化输入；输出 `success`/`data.items`（name, code, customer_level, unit_price_incl_tax, unit_price_excl_tax, available_qty, specification）/explanation/error | ✓ 只调 inventory_agent、wanding_fuzzy_matcher，不直写 Neon | 无 |
| **三** | oos-shortage-register | ✓ 登记无货/缺货、记到系统 | ✓ mode 三选一；file/text/records；输出 inserted_count、message | ✓ 无货：persist_out_of_stock_records / DataService / POST /api/oos/add；缺货：insert_shortage_records / POST /api/shortage/add；禁止绕开 | run.py 仅实现 oos_from_text、shortage_from_text；oos_from_file 在 SKILL 中说明由 run_quotation_agent + persist_out_of_stock_records 处理，符合计划 |
| **四** | quotation-register-from-dialog | ✓ 检测「报价单：」即调用；只解析+落库 | ✓ raw_text 必填；输出 draft_id、line_count、message（SKILL 多 draft_no，为合理扩展） | ✓ 解析后 POST /api/quotation-drafts；禁止只写本地 | 无 |
| **五** | replenishment-register | ✓ 「补货：」+ 产品/数量；只建草稿 | ✓ raw_text；输出 replenishment_id、line_count、message（含 draft_no） | ✓ POST /api/replenishment-drafts；DataService.insert_replenishment_draft；不直接改库存 | 计划五写 routes_procurement，Neon 映射文档与 SKILL 写 routes_quotation；以实际实现为准，表名 replenishment_drafts/line 一致 |

### A.2 计划「六、文档对齐」与「七、实施步骤」

- **六、文档对齐**  
  - 计划要求：claude.md 增加「Neon 业务 Skill 与后端映射」；代码准则审核报告补充 4 个 Skill 与 routes/Neon 表关系。  
  - 本次仅审阅 4 个 Skill 目录及 `Agent Team version3/doc/Neon_Skill_后端与表映射.md`。  
  - **结论**：`Neon_Skill_后端与表映射.md` 已存在，且与 4 个 Skill 的「参考路径」「内部约定」一致（inventory 只读、其余写 Neon 对应表）。Skill 自身未要求维护 claude.md/审核报告，文档对齐是否已做需在项目根目录及 doc 中另行确认。

- **七、实施步骤**  
  - 计划要求：不新增平行落库路径、复用既有 DataService/routes、最终文档与实现一致。  
  - **结论**：4 个 Skill 的 SKILL.md 与 run.py 均约定「只通过既有 HTTP API 或 DataService/后端模块」落库，无「直接写 DB」或「仅写本地文件」的约定；与计划一致。

### A.3 计划符合性小结

- **无重大偏离**：目的、触发、输入/输出、内部调用约定与计划二～五一致。  
- **小差异**：  
  - 计划四输出未写 `draft_no`，Skill 3 增加该字段，利于前端/后续流程，可保留。  
  - 计划五写 routes_procurement，映射文档与 Skill 4 写 routes_quotation（POST /api/replenishment-drafts）；若实现确在 routes_quotation，建议在计划或映射文档中统一表述，避免歧义。

---

## B) 可移植性（Portability）

**目标**：另一台机器（无「agent-jk」或「Agent Team version3」同路径）仅拥有 (1) 4 个 skill 目录、(2) 对 Agent Team v3 后端的访问（如 URL），能否直接使用这些 Skill。

### B.1 inventory-price-query

| 检查项 | 结论 | 说明 |
|--------|------|------|
| **SKILL.md 路径假设** | ❌ 强依赖本机结构 | 示例：`cd "Agent Team version3"`、`python ../.cursor/skills/inventory-price-query/scripts/run.py`；明确写「必须在 Agent Team version3 项目根目录下执行，或设置 AGENT_TEAM_V3_ROOT」 |
| **run.py 路径/环境** | ❌ 依赖本地代码树 | 使用 `AGENT_TEAM_V3_ROOT`；未设置时依次尝试：`cwd/Agent Team version3`、`cwd/backend`、从脚本路径上溯 4 级再拼 `Agent Team version3`。会 `os.chdir(v3_root)` 并 `sys.path.insert(0, v3_root)`，直接 import `backend.tools.inventory...`。**必须本地存在 Agent Team version3 源码**，不能仅靠 HTTP。 |
| **可移植结论** | **不可移植** | 仅「复制 skill 目录 + 设 BASE_URL」不足；必须在该机上有 Agent Team version3 目录并设置 `AGENT_TEAM_V3_ROOT`（或满足脚本的目录推测逻辑）。 |

**建议**（便于在另一台机器复用）：  
- 在 SKILL.md「环境」段明确：本 Skill 依赖**本地 Agent Team version3 代码**，需设置 `AGENT_TEAM_V3_ROOT` 或在该项目根目录下执行。  
- 若未来后端暴露「价格+库存」HTTP API，可再提供仅依赖 `BASE_URL` 的脚本变体，实现「仅复制 skill + BASE_URL」的可移植用法。

### B.2 oos-shortage-register

| 检查项 | 结论 | 说明 |
|--------|------|------|
| **SKILL.md 路径假设** | ⚠️ 示例路径为本机 | 示例：`python .cursor/skills/oos-shortage-register/scripts/run.py` 假设在 agent-jk 根目录；未写「任意目录可运行」 |
| **run.py 路径/环境** | ✓ 仅环境变量 | 仅用 `BASE_URL`（默认 `http://localhost:8000`），无硬编码路径或 cwd 依赖；依赖 `requests`。 |
| **可移植结论** | **可移植** | 复制 skill 目录到任意位置，安装 requests，设置 `BASE_URL` 指向 Agent Team v3 后端即可。 |

**建议**：在 SKILL.md「可执行脚本」下环境一条写明：「复制本 skill 到任意目录后，仅需设置 `BASE_URL`（及安装 requests）即可运行，不依赖 agent-jk 或 Agent Team version3 的目录结构。」

### B.3 quotation-register-from-dialog

| 检查项 | 结论 | 说明 |
|--------|------|------|
| **SKILL.md 路径假设** | ⚠️ 示例路径为本机 | `python .cursor/skills/quotation-register-from-dialog/scripts/run.py` |
| **run.py 路径/环境** | ✓ 仅环境变量 | 仅 `BASE_URL`，无其它路径或 cwd 依赖。 |
| **可移植结论** | **可移植** | 同上，复制 skill + 设 `BASE_URL` + requests 即可。 |

**建议**：同 B.2，在 SKILL 中补一句「可复制到任意位置，仅需 BASE_URL」。

### B.4 replenishment-register

| 检查项 | 结论 | 说明 |
|--------|------|------|
| **SKILL.md 路径假设** | ⚠️ 示例路径为本机 | `python .cursor/skills/replenishment-register/scripts/run.py` |
| **run.py 路径/环境** | ✓ 仅环境变量 | 仅 `BASE_URL`。 |
| **可移植结论** | **可移植** | 同上。 |

**建议**：同 B.2。

### B.5 可移植性总结与推荐改动

- **结论**：  
  - **inventory-price-query**：**不能**在「仅复制 skill 目录 + 设 BASE_URL」的机器上使用；必须提供 Agent Team version3 代码并设置 `AGENT_TEAM_V3_ROOT`（或满足其目录推断）。  
  - **oos-shortage-register、quotation-register-from-dialog、replenishment-register**：**可以**在另一台机器使用；只需复制对应 skill 目录、安装 requests、设置 `BASE_URL` 指向 Agent Team v3 后端。

- **推荐改动**（便于另一 LLM/机器使用）：  
  1. **inventory-price-query**：在 SKILL.md 中明确写清「依赖本地 Agent Team version3 代码与 `AGENT_TEAM_V3_ROOT`」；示例中可增加「仅复制 skill 时」的用法说明（设 `AGENT_TEAM_V3_ROOT=/path/to/Agent Team version3`）。  
  2. **其余三个 Skill**：在各自 SKILL.md 的「环境」或「可执行脚本」处增加一句：**「本 skill 可复制到任意目录使用，仅需安装 requests 并设置环境变量 BASE_URL 指向 Agent Team v3 后端（默认 http://localhost:8000）。」**  
  3. **运行示例**：三个 HTTP 型 skill 的示例可改为与路径无关的形式，例如：  
     `python scripts/run.py`（在 skill 目录下执行）或 `python /path/to/skill/scripts/run.py`，避免写死 `.cursor/skills/...`。

---

## 总结表

| Skill | 计划符合 | 可移植（仅 skill + BASE_URL） | 建议 |
|-------|----------|-------------------------------|------|
| inventory-price-query | ✓ | ❌ 需 AGENT_TEAM_V3_ROOT + 本地 v3 代码 | 文档明确依赖；可选：未来提供 HTTP 版脚本 |
| oos-shortage-register | ✓ | ✓ | SKILL 中写明「可复制目录 + BASE_URL」 |
| quotation-register-from-dialog | ✓ | ✓ | 同上 |
| replenishment-register | ✓ | ✓ | 同上 |

**优先行动**：  
1. 在 oos / quotation / replenishment 三个 SKILL.md 中补充「可复制到任意位置，仅需 BASE_URL」的说明。  
2. 在 inventory-price-query 的 SKILL.md 中明确「必须本地有 Agent Team version3 并设置 AGENT_TEAM_V3_ROOT」。  
3. （可选）统一运行示例为「在 skill 目录下执行 `python scripts/run.py`」，减少对 agent-jk 路径的依赖表述。
