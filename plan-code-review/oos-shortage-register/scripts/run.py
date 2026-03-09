#!/usr/bin/env python3
"""
oos-shortage-register Skill 入口脚本。
输入：stdin 或第一参数文件，JSON { "mode": "oos_from_text"|"shortage_from_text", "text"?: "...", "records"?: [...] }。
输出：stdout { "success", "data": { "inserted_count", "message" }, "error"? }。
依赖：requests。环境变量 BASE_URL（默认 http://localhost:8000）指向 Agent Team v3 后端。
"""
from __future__ import annotations

import json
import os
import sys

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

    mode = (inp.get("mode") or "").strip()
    if mode not in ("oos_from_text", "shortage_from_text"):
        _out({
            "success": False,
            "error": {
                "code": "unsupported_mode",
                "message": "本脚本仅支持 oos_from_text、shortage_from_text；oos_from_file 请用 run_quotation_agent + persist_out_of_stock_records",
            },
        })
        sys.exit(1)

    records = inp.get("records")
    text = (inp.get("text") or "").strip()
    if not records and text:
        # 简单从一段话拆成多条：按行或按句
        lines = [ln.strip() for ln in text.replace("；", "\n").split("\n") if ln.strip()]
        if mode == "shortage_from_text":
            records = [_parse_shortage_line(ln) for ln in lines]
        else:
            records = [_parse_oos_line(ln) for ln in lines]
        records = [r for r in records if r.get("product_name")]

    if not records:
        _out({"success": False, "error": {"code": "no_records", "message": "需要 text 或 records"}})
        sys.exit(1)

    inserted = 0
    errors = []
    for r in records:
        if mode == "shortage_from_text":
            body = {
                "product_name": (r.get("product_name") or "").strip(),
                "specification": (r.get("specification") or "").strip(),
                "quantity": float(r.get("quantity") or 0),
                "available_qty": float(r.get("available_qty") or 0),
            }
            url = f"{BASE_URL}/api/shortage/add"
        else:
            body = {
                "product_name": (r.get("product_name") or "").strip(),
                "specification": (r.get("specification") or "").strip(),
                "quantity": float(r.get("quantity") or 0),
                "unit": (r.get("unit") or "").strip(),
            }
            url = f"{BASE_URL}/api/oos/add"

        if not body["product_name"]:
            continue
        try:
            resp = requests.post(url, json=body, timeout=30)
            if resp.status_code == 200 and resp.json().get("success"):
                inserted += 1
            else:
                errors.append(resp.text[:200])
        except Exception as e:
            errors.append(str(e))

    msg = f"已登记 {inserted} 条。"
    if errors:
        msg += " 部分失败: " + "; ".join(errors[:3])
    _out({"success": True, "data": {"inserted_count": inserted, "message": msg}})


def _parse_oos_line(line: str) -> dict:
    # 简单解析：整行当 product_name，或 "名称 规格 数量"
    parts = line.split()
    if len(parts) >= 3 and _is_num(parts[-1]):
        return {"product_name": " ".join(parts[:-2]), "specification": parts[-2], "quantity": float(parts[-1])}
    if len(parts) >= 2 and _is_num(parts[-1]):
        return {"product_name": " ".join(parts[:-1]), "quantity": float(parts[-1])}
    return {"product_name": line, "quantity": 0}


def _parse_shortage_line(line: str) -> dict:
    d = _parse_oos_line(line)
    d.setdefault("available_qty", 0)
    return d


def _is_num(s: str) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _read_input() -> str:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def _out(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
