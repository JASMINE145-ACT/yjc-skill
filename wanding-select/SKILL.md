---
name: wanding-select
description: "万鼎选型：完全依赖两 tool——① 筛选（match_wanding_price / get_wanding_candidates）② LLM 选型（select_wanding_match / llm_select_best）。有问题从筛选逻辑与 LLM 选择逻辑完善，不另写规则引擎。"
---

# 万鼎选型 Skill（开盒即用）

## 目的与原则

- **完全依赖两个 tool**：① **筛选**：match_wanding_price（或脚本 get_wanding_candidates 调 match_wanding_price_candidates）取候选；② **选型**：select_wanding_match（llm_select_best）从候选中选 1 条。选型结果必须来自 LLM 选型，不另写规则引擎。
- **接受输入**：用户给出关键词（及可选期望 code/名称用于判断对错）。
- **判断**：选型后对比期望，回复「选对」或「选错」及理由；无期望则回复选中项与选型依据。
- **有问题时**：从**筛选逻辑**（wanding_fuzzy_matcher：关键词归一化、同义词、规格等价）与 **LLM 选择逻辑**（llm_selector：业务知识、prompt）完善，不在此 Skill 或批量脚本里堆规则。

---

## 开盒即用：前置条件与首次检查

**重要：以下所有命令都必须在「Agent Team version3」项目根目录下执行。**

```bash
cd "Agent Team version3"   # 或你的 version3 实际路径
```

### 前置条件

| 项 | 说明 |
|----|------|
| Python | 已安装 Python 3，命令行可执行 `python` 或 `python3` |
| 项目 | 存在目录 `Agent Team version3`，且内含 `scripts/`、`data/`、`backend/` |
| 价格库 | `data/万鼎价格库_管材与国标管件_标准格式.xlsx` 存在；或设置环境变量 `PRICE_LIBRARY_PATH` 指向该文件 |
| 依赖 | 脚本会用到 `openpyxl`、`pandas`，缺则 `pip install openpyxl pandas` |

### 首次使用检查（建议先跑一次）

在 **Agent Team version3** 目录下执行：

```bash
python scripts/get_wanding_candidates.py "90度弯头" --json
```

- 若输出 JSON 中 `candidates` 非空，说明价格库与路径正常，**开盒即用**。
- 若 `candidates` 为空且确认数据库有该品名，见下文「常见问题」。

### Windows 下中文关键词乱码

在 PowerShell/CMD 中直接传中文可能乱码导致候选为空。可用任一种方式避免：

1. **用 Python 内调用**（推荐）：不通过命令行传中文，而是在 Python 里写死关键词并调用 `get_candidates(keywords)`，再打印或写文件。
2. **批量脚本**：使用 `run_skill_lookup_batch.py`，关键词写在脚本内（UTF-8），由脚本逐条取候选并输出 JSON。

---

## 单条流程（1 条关键词 → 选型 → 写 log）

1. **接受输入**  
   - 必选：**关键词**（如 90度弯头带检查口、32*20内丝三通、PVC50止水节）。  
   - 可选：**期望 code**（如 8020020643）、**期望名称**（如 90°弯头(带检查口)PVC-U排水配件白色 dn50），用于最后判断选型是否正确。

2. **取候选**（在 **Agent Team version3** 目录下）  
   ```bash
   python scripts/get_wanding_candidates.py "<关键词>"
   ```  
   或输出 JSON：  
   ```bash
   python scripts/get_wanding_candidates.py "<关键词>" --json
   ```

3. **选型**  
   必须通过 **select_wanding_match**（即 llm_select_best）从候选中选一条；单条时可由 Cursor 代用户调该工具或由 Agent 调 tool，选型结果以工具返回为准。无合适时工具返回无匹配。

4. **判断**（必须输出）  
   - 若用户给了**期望 code 或期望名称**：对比选中项与期望，明确回复 **「选对」** 或 **「选错」**，并简述理由。  
   - 若用户未给期望：回复**选中结果**（code + matched_name）并**简要说明选型依据**。

5. **写入 log**（必须执行，在 **Agent Team version3** 目录下）  
   ```bash
   python scripts/append_wanding_log.py --keywords "<关键词>" --expected-code "<期望code或空>" --expected-name "<期望名称或空>" --list-contains 是或否 [--no-candidates | --candidates-json <JSON或文件路径>] [--no-selection | --selected-code <code> --selected-name "<名称>"] [--llm-correct 是或否]
   ```  
   - 无候选：`--no-candidates`，`--list-contains` 否。  
   - 有候选、有选中：`--selected-code`、`--selected-name`，有期望时加 `--llm-correct` 是/否。  
   - 有候选、无匹配：`--no-selection`，`--llm-correct` 否。  
   - 候选可保存为 JSON 文件，用 `--candidates-json 文件路径` 传入。

---

## 批量流程（多条关键词 → 一次取候选 → 选型并写 log）

适用于多行询价表或固定测试集（如 8 条），避免在命令行多次传中文。

### 步骤 1：批量取候选

在 **Agent Team version3** 目录下：

```bash
python scripts/run_skill_lookup_batch.py > logs/batch_candidates.json
```

脚本内建 8 条示例（90度弯头带检查口 PVC50/110、110PVC堵头、Pipa COUNDUIT 20m、Socket 20m、PVC160斜三通/弯头/管子）。要改条目可编辑 `scripts/run_skill_lookup_batch.py` 中的 `ROWS`。

### 步骤 2：选型并追加到 log

```bash
python scripts/run_skill_batch_to_log.py logs/batch_candidates.json
```

会按条调用 **llm_select_best**（与 select_wanding_match 相同逻辑）选型，再与期望对比写 log。**批量与单条均完全依赖两 tool**：候选来自筛选（match_wanding_price_candidates），选型来自 LLM（llm_select_best），不参考期望做选型。

---

## 选型规则（与 llm_selector 业务知识一致，你必须遵守）

【业务知识】
1. 三角阀 ≠ 角阀：询价「三角阀」而候选只有「角阀」时，应判定无匹配。
2. 软管：管材库无软管类产品，询价含「软管」时应返回无匹配。
3. 规格精确匹配优先：dn25 对 dn25，不应选 dn20。
4. PPR 优先于 PVC（同规格下）。
5. 长度 vs 管径：「50cm」表示长度（软管），不应与 dn50（管径）混淆。
6. 等径三通 > 异径三通（除非询价明确指定异径）。
7. 联塑品牌优先（同等条件下）。
8. 【规格转换规则（主径×副径 → 英寸）】
   - 询价中「A*B」「A×B」「AB」（如 32*20、32×20、3220）表示：主径 A（mm）、副径 B（mm）。
   - 副径 B（mm）→ 英寸：15/16/20→1/2"，25→3/4"，32→1"，40→1-1/4"，50→1-1/2"；主径 A 对应 dn20/dn25/dn32/dn40。
   - 示例：「32*20内丝三通」选「内螺纹三通…dn32x1/2"」；「25*20」选 x1/2"。
   - 若关键词仅一个数（如「32弯头」无*20），则只按主径匹配，不推断副径。

---

## 命令速查（均在 Agent Team version3 目录下）

| 用途 | 命令 |
|------|------|
| 单条取候选（可读） | `python scripts/get_wanding_candidates.py "<关键词>"` |
| 单条取候选（JSON） | `python scripts/get_wanding_candidates.py "<关键词>" --json` |
| 单条写 log | `python scripts/append_wanding_log.py --keywords "..." --expected-code "..." ...` |
| 批量取候选 | `python scripts/run_skill_lookup_batch.py > logs/batch_candidates.json` |
| 批量选型+写 log | `python scripts/run_skill_batch_to_log.py logs/batch_candidates.json` |

---

## 使用示例

**示例 1：带期望，需判断对错**  
用户输入：「90度弯头带检查口 PVC50」，期望 code=8020020643。

1. 取候选：`get_wanding_candidates.py "90度弯头带检查口"` 或带 PVC50。  
2. 选型：选「带检查口」+ PVC-U 排水 + dn50 的候选。  
3. **判断**：选中 8020020643 → 回复 **「选对」**；否则 **「选错」** 并说明差异。  
4. 写 log：`append_wanding_log.py` 带上 keywords、expected-code、list-contains、selected-code/name、llm-correct。

**示例 2：仅关键词**  
用户：「用 Cursor 测一下 32*20内丝直接」

1. 取候选 → 选型：32*20→1/2"，选 dn32×1/2" 的那条。  
2. **判断**：回复选中 code、matched_name 及选型依据。  
3. 写 log。

**示例 3：无期望**  
用户：「50直接 不耗 token 测」

1. 取候选 → 选型：优先选「直通(管箍)PVC-U排水配件白色 dn50」。  
2. **判断**：回复选中项或「无匹配」+ 依据。  
3. 写 log。

---

## 常见问题

- **候选为空，但数据库/Excel 里明明有该品名**  
  - 万鼎匹配会同时查「管材」和「国标管件」两个 sheet。确认价格库是 `万鼎价格库_管材与国标管件_标准格式.xlsx` 且两表都有数据。  
  - 确认在 **Agent Team version3** 下执行，或已设置 `PRICE_LIBRARY_PATH` 指向该文件。

- **Windows 下传中文关键词后候选为空**  
  - 多为终端编码导致关键词乱码。用 Python 内调用 `get_candidates(keywords)` 或使用批量脚本（关键词写在脚本内 UTF-8）即可。

- **批量跑 8 条后想改条目**  
  - 编辑 `Agent Team version3/scripts/run_skill_lookup_batch.py` 中的 `ROWS`（每项：名称、规格、期望 code、期望名称），再重新执行批量取候选与 `run_skill_batch_to_log`。

---

## 相关路径

| 说明 | 路径 |
|------|------|
| 取候选脚本 | `Agent Team version3/scripts/get_wanding_candidates.py` |
| 写 log 脚本 | `Agent Team version3/scripts/append_wanding_log.py` |
| 批量取候选 | `Agent Team version3/scripts/run_skill_lookup_batch.py` |
| 批量选型+写 log | `Agent Team version3/scripts/run_skill_batch_to_log.py` |
| 选型结果 log | `Agent Team version3/logs/test_wanding_select.log` |
| 万鼎模糊匹配 | `Agent Team version3/backend/tools/inventory/services/wanding_fuzzy_matcher.py` |
| 业务选型规则来源 | `Agent Team version3/backend/tools/inventory/services/llm_selector.py` |
