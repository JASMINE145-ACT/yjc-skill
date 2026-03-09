#!/usr/bin/env python3
"""
inventory-price-query Skill 入口脚本。
与 Agent Team version3 完全一致：报价单+万鼎（历史+万鼎并集）+ LLM 选型 + 查库存。

运行模式（自动选择）：
  HTTP 模式（优先）：设置 BASE_URL 环境变量指向已部署的 v3 后端，调 POST /api/query。
    - 另一台电脑只需 BASE_URL + pip install requests，与其他 3 个 Skill 一致。
  本地模式（兜底）：在 Agent Team version3 根目录下执行，或设置 AGENT_TEAM_V3_ROOT。
    - 直接 import Python 模块，需要本地 v3 源码 + 数据文件 + 所有环境变量。

输入：stdin 或第一参数文件，JSON { "query": "自然语言" } 或 { "product_name", "spec", "customer_level", "use_quotation_union"? }。
输出：stdout 统一 JSON { "success", "data": { "items", "explanation" }, "error"? }。
"""
from __future__ import annotations

import json
import os
import re
import sys


# ──────────────────────────────────────────────
# 模式检测
# ──────────────────────────────────────────────

BASE_URL = os.environ.get("BASE_URL", "").strip().rstrip("/")


def _resolve_v3_root() -> str | None:
    v3_root = os.environ.get("AGENT_TEAM_V3_ROOT", "").strip()
    if not v3_root and os.path.isdir("Agent Team version3"):
        v3_root = os.path.abspath("Agent Team version3")
    if not v3_root and os.path.isdir("backend"):
        v3_root = os.getcwd()
    if not v3_root:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for _ in range(4):
            script_dir = os.path.dirname(script_dir)
        candidate = os.path.join(script_dir, "Agent Team version3")
        if os.path.isdir(candidate):
            v3_root = candidate
    return v3_root if v3_root and os.path.isdir(v3_root) else None


# ──────────────────────────────────────────────
# HTTP 模式（BASE_URL 可用时）
# ──────────────────────────────────────────────

def _run_http(phrase: str, customer_level: str) -> None:
    """POST /api/query → 返回 agent 自然语言答案作为 explanation。"""
    try:
        import requests
    except ImportError:
        _out({"success": False, "error": {"code": "no_requests", "message": "请安装 requests: pip install requests"}})
        sys.exit(1)

    # 在 query 里带上档位信息，让 agent 走完整流程（match_quotation + select + get_inventory）
    full_query = phrase
    if customer_level and customer_level != "B":
        full_query = f"{phrase} {customer_level}档价格"

    try:
        resp = requests.post(
            f"{BASE_URL}/api/query",
            json={"query": full_query},
            timeout=60,
        )
        data = resp.json()
        if resp.status_code != 200 or not data.get("success"):
            _out({
                "success": False,
                "error": {"code": "api_error", "message": data.get("error") or resp.text[:300]},
            })
            sys.exit(1)
        answer = (data.get("data") or {}).get("answer") or ""
        _out({
            "success": True,
            "data": {
                # HTTP 模式下 items 结构化字段不可用（agent 返回自然语言）
                "items": [{"name": phrase, "code": "", "customer_level": customer_level,
                           "unit_price_incl_tax": None, "unit_price_excl_tax": None,
                           "available_qty": None, "specification": ""}],
                "explanation": answer,
            },
        })
    except Exception as e:
        _out({"success": False, "error": {"code": "runtime_error", "message": str(e)}})
        sys.exit(1)


# ──────────────────────────────────────────────
# 本地模式（直接 import v3 Python 模块）
# ──────────────────────────────────────────────

def _parse_price_result(price_text: str):
    """解析 match_quotation / match_wanding_price 的 result：single/chosen、needs_selection/candidates、unmatched 或纯文本。"""
    if not price_text or "{" not in price_text:
        return None, None, None
    try:
        data = json.loads(price_text)
    except Exception:
        m = re.search(r"\{[^{}]*\}", price_text)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                return None, None, None
        else:
            return None, None, None
    chosen = data.get("chosen")
    candidates = data.get("candidates") or []
    needs_selection = bool(data.get("needs_selection")) and not chosen
    match_source = data.get("match_source", "")
    if data.get("unmatched"):
        return None, [], match_source
    if chosen:
        return chosen, candidates, match_source
    if needs_selection and candidates:
        return None, candidates, match_source
    return chosen, candidates, match_source


def _run_local(phrase: str, spec: str, product_name: str, customer_level: str,
               use_quotation_union: bool, v3_root: str) -> None:
    orig_cwd = os.getcwd()
    try:
        if os.path.abspath(v3_root) != os.path.abspath(orig_cwd):
            os.chdir(v3_root)
        if v3_root not in sys.path:
            sys.path.insert(0, v3_root)

        from backend.tools.inventory.services.inventory_agent_tools import execute_inventory_tool

        code = ""
        name = product_name or phrase
        unit_price_incl = None
        match_source = ""
        explanation_extra: list[str] = []

        # 1) 价格：优先 match_quotation（历史+万鼎并集），无候选时再 match_wanding_price
        price_text = ""
        if use_quotation_union:
            out = execute_inventory_tool("match_quotation", {"keywords": phrase, "customer_level": customer_level})
            if out.get("success"):
                price_text = out.get("result", "")
        pre_chosen, pre_candidates, _ = _parse_price_result(price_text)
        if not price_text or (not pre_chosen and not pre_candidates):
            out = execute_inventory_tool("match_wanding_price", {"keywords": phrase, "customer_level": customer_level})
            if out.get("success"):
                price_text = out.get("result", "")

        chosen, candidates, match_source = _parse_price_result(price_text)
        if not chosen and candidates:
            # needs_selection：调 select_wanding_match（LLM 选型）
            sel_out = execute_inventory_tool(
                "select_wanding_match",
                {"keywords": phrase, "candidates": candidates, "match_source": match_source or "字段匹配"},
            )
            sel_text = (sel_out.get("result") or "") if sel_out.get("success") else ""
            if sel_text and "{" in sel_text:
                try:
                    sel_data = json.loads(sel_text)
                    chosen = sel_data.get("chosen")
                except Exception:
                    pass
            if not chosen and sel_text and ("无把握" in sel_text or "options" in sel_text or "请人工" in sel_text):
                explanation_extra.append("价格多候选需人工确认，请根据说明选择。")
                explanation_extra.append(sel_text[:500])
            elif not chosen and candidates:
                cand_lines = "\n".join(
                    f"  {i+1}. {c.get('matched_name','')} | {customer_level}档: {c.get('unit_price','')} | code: {c.get('code','')}"
                    for i, c in enumerate(candidates[:5])
                )
                explanation_extra.append("价格多候选，LLM 未选出唯一结果，请人工确认：\n" + cand_lines)

        if chosen:
            code = str(chosen.get("code", "")).strip()
            name = chosen.get("matched_name") or name
            raw_price = chosen.get("unit_price")
            unit_price_incl = float(raw_price) if raw_price is not None else None
            if match_source:
                explanation_extra.append(f"匹配来源: {match_source}")

        # 2) 库存：有 code 时用 get_inventory_by_code，否则 search_inventory
        if code:
            inv_out = execute_inventory_tool("get_inventory_by_code", {"code": code})
        else:
            inv_out = execute_inventory_tool("search_inventory", {"keywords": phrase})
        inventory_text = inv_out.get("result", "") if inv_out.get("success") else f"库存查询失败: {inv_out.get('error', '')}"

        if explanation_extra:
            inventory_text = inventory_text + "\n\n" + "\n".join(explanation_extra)

        items = [{
            "name": name,
            "code": code,
            "customer_level": customer_level,
            "unit_price_incl_tax": unit_price_incl,
            "unit_price_excl_tax": None,
            "available_qty": None,
            "specification": spec or "",
        }]
        _out({"success": True, "data": {"items": items, "explanation": inventory_text}})
    except Exception as e:
        _out({"success": False, "error": {"code": "runtime_error", "message": str(e)}})
        sys.exit(1)
    finally:
        os.chdir(orig_cwd)


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def main() -> None:
    raw = _read_input()
    try:
        inp = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        _out({"success": False, "error": {"code": "invalid_input", "message": str(e)}})
        sys.exit(1)

    query = (inp.get("query") or "").strip()
    product_name = (inp.get("product_name") or "").strip()
    spec = (inp.get("spec") or "").strip()
    customer_level = (inp.get("customer_level") or "B").strip().upper() or "B"
    use_quotation_union = inp.get("use_quotation_union", True)

    if not query and not product_name:
        _out({"success": False, "error": {"code": "missing_input", "message": "需要 query 或 product_name"}})
        sys.exit(1)

    phrase = query or f"{product_name} {spec}".strip()

    # 模式选择：BASE_URL 优先（HTTP 模式），否则本地模式
    if BASE_URL:
        _run_http(phrase, customer_level)
        return

    v3_root = _resolve_v3_root()
    if not v3_root:
        _out({
            "success": False,
            "error": {
                "code": "no_config",
                "message": "请设置 BASE_URL（指向已部署的 v3 后端），或在 Agent Team version3 根目录下执行 / 设置 AGENT_TEAM_V3_ROOT",
            },
        })
        sys.exit(1)

    _run_local(phrase, spec, product_name, customer_level, use_quotation_union, v3_root)


def _read_input() -> str:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def _out(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
