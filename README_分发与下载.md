# Neon 四大 Skill：打包与分发

封装好后，他人可**下载**并在自己电脑上直接使用。按以下方式打包与说明即可。

## 打包方式

每个 Skill 均为**独立目录**，可直接打成 zip 分发：

| 分发包 | 目录 | 他人下载后 |
|--------|------|------------|
| `oos-shortage-register.zip` | `oos-shortage-register/`（含 SKILL.md、scripts/run.py） | 解压 → 安装 requests → 设 BASE_URL → 即用 |
| `quotation-register-from-dialog.zip` | `quotation-register-from-dialog/` | 同上 |
| `replenishment-register.zip` | `replenishment-register/` | 同上 |
| `inventory-price-query.zip` | `inventory-price-query/` | 解压 → 本机需有 Agent Team version3 源码 → 设 AGENT_TEAM_V3_ROOT 或在 v3 根目录执行 → 使用 |

**操作**：在仓库中选中每个 skill 目录（如 `agent-jk/.cursor/skills/oos-shortage-register`），右键压缩为 zip，或命令行：

```bash
cd .cursor/skills
zip -r oos-shortage-register.zip oos-shortage-register
zip -r quotation-register-from-dialog.zip quotation-register-from-dialog
zip -r replenishment-register.zip replenishment-register
zip -r inventory-price-query.zip inventory-price-query
```

## 对方使用前提

- **后端已部署**：对方（或你司）已部署 Agent Team v3 后端，并有一个可访问的 BASE_URL（如 `http://localhost:8000` 或公网域名）。
- **三个「无货/报价/补货」Skill**：只需 Python 3、`pip install requests`、设置 `BASE_URL`，**不需要**下载本仓库或 Agent Team version3 源码。
- **一个「价格+库存」Skill**：需要对方电脑上有 Agent Team version3 源码并配置好环境，或等后端提供「价格+库存」HTTP API 后改用仅 BASE_URL 的脚本。

## 每个 Skill 内的使用说明

各 Skill 的 **SKILL.md** 开头已包含 **「下载后使用」** 小节，说明：解压位置、依赖、环境变量、运行命令。对方解压后看 SKILL.md 即可按步骤操作，无需再看本仓库。

## 分发渠道

- 网盘、内部文件服务器、Git 仓库 release 附件等，上传上述 zip 即可。
- 若希望对方用 Cursor 触发：对方将解压后的目录放到其 Cursor 项目的 `.cursor/skills/` 下，或放到用户级 skills 目录（依 Cursor 约定）；LLM 也可直接执行各 skill 的 `scripts/run.py` 获取 JSON，不依赖 Cursor 路径。
