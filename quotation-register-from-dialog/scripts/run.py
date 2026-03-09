#!/usr/bin/env python3
"""
quotation-register-from-dialog Skill 入口脚本。
输入：stdin 或第一参数文件，JSON { "raw_text": "报价单：\\n行1\\n行2...", "customer_level"?, "source"? }。
输出：stdout { "success", "data": { "draft_id", "draft_no", "line_count", "message" }, "error"? }。
依赖：requests。环境变量 BASE_URL（默认 http://localhost:8000）。
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print(json.dumps({
        "success": False,
        "error": {"code": "no_requests", "message": "请安装 requests: pip install requests"},
    }, ensure_ascii=False))
    sys.exit(1)


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")


def main() -> None:
    raw = _read_input()
    try:
        inp = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        _out({"success": False, "error": {"code": "invalid_input", "message": str(e)}})
        sys.exit(1)

    raw_text = (inp.get("raw_text") or "").strip()
    if not raw_text:
        _out({"success": False, "error": {"code": "missing_raw_text", "message": "需要 raw_text"}})
        sys.exit(1)

    # 提取「报价单：」后的内容（支持中文冒号和英文冒号）
    for sep in ("报价单：", "报价单:", "quotation:", "Quotation:"):
        if sep in raw_text:
            raw_text = raw_text.split(sep, 1)[-1].strip()
            break

    lines = _parse_quotation_lines(raw_text)
    if not lines:
        _out({"success": False, "error": {"code": "no_lines", "message": "未解析出报价行"}})
        sys.exit(1)

    name = f"对话-报价单-{datetime.now().strftime('%Y%m%d-%H%M')}"
    body = {
        "name": name,
        "source": inp.get("source") or "nl",
        "lines": lines,
    }
    if inp.get("customer_level"):
        body["customer_level"] = inp["customer_level"].strip().upper()

    try:
        resp = requests.post(f"{BASE_URL}/api/quotation-drafts", json=body, timeout=30)
        data = resp.json()
        if resp.status_code != 200 or not data.get("success"):
            _out({
                "success": False,
                "error": {"code": "api_error", "message": data.get("detail") or data.get("error") or resp.text[:300]},
            })
            sys.exit(1)
        result = data.get("data") or {}
        _out({
            "success": True,
            "data": {
                "draft_id": result.get("draft_id"),
                "draft_no": result.get("draft_no"),
                "line_count": len(lines),
                "message": f"已登记报价草稿，共 {len(lines)} 行。",
            },
        })
    except Exception as e:
        _out({"success": False, "error": {"code": "runtime_error", "message": str(e)}})
        sys.exit(1)


def _parse_quotation_lines(text: str) -> list[dict]:
    """将文本按行解析为 lines：product_name, specification, qty。

    约定：末尾连续数字（可带件/个/m 等单位）为数量，其余全部为 product_name。
    不在脚本层切分 product_name/specification，交由后端 inventory_agent 处理。
    """
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 从行末提取数量（末尾数字，可选单位词）
        qty = 0.0
        m = re.search(r"([\d.]+)\s*(?:件|个|根|套|条|m|米|pcs|pc|箱|卷)?\s*$", line, re.IGNORECASE)
        if m:
            try:
                qty = float(m.group(1))
            except (TypeError, ValueError):
                pass
            # product_name 为去掉末尾数量+单位后的部分
            product_name = line[: m.start()].strip()
        else:
            product_name = line

        if not product_name:
            continue
        out.append({"product_name": product_name, "specification": "", "qty": qty})
    return out


def _read_input() -> str:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def _out(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
