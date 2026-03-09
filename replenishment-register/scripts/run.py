#!/usr/bin/env python3
"""
replenishment-register Skill 入口脚本。
输入：stdin 或第一参数文件，JSON { "raw_text": "补货：PVC 管 dn20 100\\n补货：ITEM123 50", "name"?, "warehouse"?, "priority"? }。
输出：stdout { "success", "data": { "replenishment_id", "draft_no", "line_count", "message" }, "error"? }。
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

    lines = _parse_replenishment_lines(raw_text)
    if not lines:
        _out({"success": False, "error": {"code": "no_lines", "message": "未解析出补货行（需包含「补货：」或「补货:」）"}})
        sys.exit(1)

    name = (inp.get("name") or "").strip() or f"补货-{datetime.now().strftime('%Y%m%d-%H%M')}"
    body: dict = {"name": name, "lines": lines}
    # 可选字段：若后端 API 支持则一并写入
    for field in ("warehouse", "expected_date", "priority", "remark"):
        if inp.get(field):
            body[field] = inp[field]

    try:
        resp = requests.post(f"{BASE_URL}/api/replenishment-drafts", json=body, timeout=60)
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
                "replenishment_id": result.get("draft_id"),
                "draft_no": result.get("draft_no"),
                "line_count": len(lines),
                "message": f"已登记补货草稿，共 {len(lines)} 行。",
            },
        })
    except Exception as e:
        _out({"success": False, "error": {"code": "runtime_error", "message": str(e)}})
        sys.exit(1)


def _parse_replenishment_lines(text: str) -> list[dict]:
    """解析「补货：/补货:产品 数量」或「补货：编码 数量」，支持中英文冒号。"""
    out = []
    for line in text.split("\n"):
        line = line.strip()
        # 同时识别中文冒号「补货：」和英文冒号「补货:」
        m_prefix = re.search(r"补货[：:]", line)
        if not m_prefix:
            continue
        after = line[m_prefix.end():].strip()
        if not after:
            continue
        # 末尾数字为数量（可带件/个/根等单位）
        m_qty = re.search(r"([\d.]+)\s*(?:件|个|根|套|条|m|米|pcs|pc|箱|卷)?\s*$", after, re.IGNORECASE)
        if m_qty:
            quantity = float(m_qty.group(1))
            product_part = after[: m_qty.start()].replace("数量", "").strip()
        else:
            quantity = 0.0
            product_part = after.replace("数量", "").strip()
        if not product_part:
            continue
        out.append({"product_or_code": product_part, "quantity": quantity})
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
