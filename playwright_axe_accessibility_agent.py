import os
import asyncio
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
import websockets
from playwright.async_api import async_playwright
from axe_playwright_python.async_playwright import Axe

# ==================== ENV ====================
load_dotenv()
api_key = os.getenv("LLM_API_KEY")
knowledgebase_id = os.getenv("KNOWLEDGEBASE_ID")

# ==================== MAIN CLASS ====================
class PlaywrightAgentTester:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.session_id = str(uuid.uuid4())
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    # ---------- Browser Setup ----------
    async def setup_browser(self, headless: bool = False):
        print(f"🚀 Opening {self.target_url}")
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=["--start-maximized"]
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )

        self.page = await self.context.new_page()

        try:
            response = await self.page.goto(
                self.target_url,
                wait_until="domcontentloaded",
                timeout=30000
            )
            print(f"✅ Page loaded: {response.status}")
            return True
        except Exception as e:
            print(f"❌ Page load failed: {e}")
            return False

    # ---------- Page Info + Screenshot ----------
    async def capture_page_info(self):
        os.makedirs("screenshots", exist_ok=True)
        screenshot_path = f"screenshots/page_{self.session_id}.png"

        await self.page.screenshot(path=screenshot_path, full_page=True)

        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "viewport": self.page.viewport_size,
            "timestamp": datetime.now().isoformat(),
            "screenshot": screenshot_path
        }

    # ---------- Axe Automated Accessibility ----------
    async def run_axe_accessibility_checks(self):
        print("🧩 Running automated accessibility checks (axe-core)...")

        axe = Axe()

        results = await axe.run(
            self.page,
            options={
                "runOnly": {
                    "type": "tag",
                    "values": ["wcag2a", "wcag2aa"]
                }
            }
        )

        # ✅ AxeResults has NO stable public API.
        # The only safe approach is to extract its internal JSON payload.
        axe_data = results.__dict__

        # Some versions nest results; normalize here
        if "violations" not in axe_data:
            for value in axe_data.values():
                if isinstance(value, dict) and "violations" in value:
                    axe_data = value
                    break

        violations = axe_data.get("violations", [])

        normalized = []
        for v in violations:
            normalized.append({
                "id": v["id"],
                "impact": v.get("impact"),
                "description": v["description"],
                "help": v["help"],
                "helpUrl": v["helpUrl"],
                "wcag": [t for t in v.get("tags", []) if t.startswith("wcag")],
                "elements": [
                    {
                        "target": n.get("target"),
                        "html": n.get("html")
                    }
                    for n in v.get("nodes", [])
                ]
            })

        return {
            "summary": {
                "total_violations": len(normalized),
                "critical": len([v for v in normalized if v["impact"] == "critical"]),
                "serious": len([v for v in normalized if v["impact"] == "serious"]),
                "moderate": len([v for v in normalized if v["impact"] == "moderate"])
            },
            "violations": normalized
        }

    # ---------- Report Builder ----------
    def build_accessibility_report(self, page_info, axe_results):
        return {
            "metadata": {
                "session_id": self.session_id,
                "page": page_info
            },
            "automated_checks": axe_results
        }

    # ---------- AI Agent ----------
    async def connect_to_agent_and_test(self, prompt, knowledgebase_id, page_info, axe_results):
        uri = "wss://ws.generative.engine.capgemini.com/"
        headers = [("x-api-key", api_key)]

        enhanced_prompt = f"""
You are a web accessibility testing assistant analyzing a webpage.

Page:
URL: {page_info['url']}
Title: {page_info['title']}

Automated accessibility results (axe-core):
{json.dumps(axe_results, indent=2)}

Tasks:
1. Summarize automated accessibility findings.
2. Identify the most critical WCAG failures.
3. Provide step-by-step manual testing instructions.

User request: {prompt}

Please provide detailed accessibility testing analysis and recommendations.
"""
    
        async with websockets.connect(uri, additional_headers=headers) as websocket:
            payload = {
                "action": "run",
                "modelInterface": "multimodal",
                "adapterInterfaceVersion": "v2",
                "data": {
                    "mode": "chain",
                    "text": enhanced_prompt,
                    "modelName": "amazon.nova-lite-v1:0",
                    "provider": "bedrock",
                    "sessionId": self.session_id,
                    "workspaceId": knowledgebase_id,
                    "files": [],
                    "modelKwargs": {
                        "maxTokens": 1200,
                        "temperature": 0.4,
                        "streaming": True
                    }
                }
            }

            await websocket.send(json.dumps(payload))

            print("\n🤖 Agent analyzing the results...\n")
            
            full_response = ""
            try:
                while True:
                    msg = await websocket.recv()
                    data = json.loads(msg)
                    if "data" in data and "content" in data["data"]:
                        chunk = data["data"]["content"]
                        full_response += chunk
                        print(chunk, end="", flush=True)

            except websockets.exceptions.ConnectionClosed:
                print("\n\n✅ Agent response complete")

            return full_response

    # ---------- Cleanup ----------
    async def cleanup(self):
        """Close browser and cleanup"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("🧹 Cleanup complete")

# ==================== MAIN ====================
async def main():
    TARGET_URL = "https://www.trojmiasto.pl/"
    TEST_PROMPT = "Audit this website for accessibility issues."
    WORKSPACE_ID = knowledgebase_id
    HEADLESS = False

    print("=" * 60)
    print("🧪 GEP Accessibility AI Agent Solution - Accessibility Testing")
    print("=" * 60)

    # Initialize tester
    tester = PlaywrightAgentTester(TARGET_URL)

    try:
        if not await tester.setup_browser(headless=HEADLESS):
            return

        # Wait for page to stabilize
        print("⏳ Waiting for page to load completely...")
        await asyncio.sleep(3)

        page_info = await tester.capture_page_info()
        axe_results = await tester.run_axe_accessibility_checks()

        report = tester.build_accessibility_report(page_info, axe_results)

        os.makedirs("reports", exist_ok=True)
        report_path = f"reports/accessibility_report_{tester.session_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Accessibility report saved: {report_path}")

        await tester.connect_to_agent_and_test(
            TEST_PROMPT,
            WORKSPACE_ID,
            page_info,
            axe_results
        )
    
    finally:
        await tester.cleanup()
        print("\n" + "=" * 60)
        print("🏁 Test session ended")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
