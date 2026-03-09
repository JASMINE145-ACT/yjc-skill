# -*- coding: utf-8 -*-
"""
Skill 页面前后端联调测试（Playwright）：
1. 登录页 mock 登录
2. 进入 skill.html，等待 networkidle
3. 校验 pdf / xlsx 两个 skill 卡片存在
4. 截图保存
"""
import os
import sys
from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://localhost:3000"
SKILL_URL = f"{FRONTEND_URL}/skill.html"
LOGIN_URL = f"{FRONTEND_URL}/login.html"
SCREENSHOT_DIR = os.environ.get("TEMP", os.path.dirname(__file__))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. 在每次加载页面前注入 token，这样 skill.html 内的重定向判断能读到
            page.add_init_script(
                "localStorage.setItem('token', 'mock_token_e2e'); localStorage.setItem('user', JSON.stringify({email:'test@skill.e2e'}));"
            )
            # 2. 打开 Skills 页（dev server 可能使 navigation 不结束，用 domcontentloaded）
            page.goto(SKILL_URL, wait_until="domcontentloaded", timeout=20000)
            # 3. 等待 GET /skills 返回并渲染（固定等待 + 轮询标题）
            page.wait_for_timeout(4000)
            pdf_ok = page.get_by_role("heading", name="pdf").is_visible()
            xlsx_ok = page.get_by_role("heading", name="xlsx").is_visible()
            if not pdf_ok or not xlsx_ok:
                page.wait_for_timeout(6000)
                pdf_ok = page.get_by_role("heading", name="pdf").is_visible()
                xlsx_ok = page.get_by_role("heading", name="xlsx").is_visible()
            if not pdf_ok or not xlsx_ok:
                print("FAIL: pdf or xlsx skill card not visible")
                sys.exit(1)

            print("OK: pdf and xlsx skills visible on skill page")

            # 5. 截图
            path = os.path.join(SCREENSHOT_DIR, "skill_page_test.png")
            page.screenshot(path=path, full_page=True)
            print(f"Screenshot: {path}")

        finally:
            browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
