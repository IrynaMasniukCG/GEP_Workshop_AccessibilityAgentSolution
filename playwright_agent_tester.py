import os
import asyncio
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
import websockets
from playwright.async_api import async_playwright

load_dotenv()
api_key = os.getenv("LLM_API_KEY")
knowledgebase_id = os.getenv("KNOWLEDGEBASE_ID")

class PlaywrightAgentTester:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.session_id = str(uuid.uuid4())
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None
        self.test_results = []

    async def setup_browser(self, headless: bool = False):
        """Initialize Playwright browser and page"""
        print(f"🚀 Setting up browser for URL: {self.target_url}")
        
        self.playwright = await async_playwright().start()
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--start-maximized']
        )
        
        # Create context
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Create page
        self.page = await self.context.new_page()
        
        # Navigate to URL
        try:
            response = await self.page.goto(self.target_url, wait_until='domcontentloaded', timeout=30000)
            print(f"✅ Page loaded successfully: Status {response.status}")
            return True
        except Exception as e:
            print(f"❌ Failed to load page: {str(e)}")
            return False

    async def capture_page_info(self):
        """Capture information about the current page"""
        if not self.page:
            return None

        try:
            page_info = {
                "url": self.page.url,
                "title": await self.page.title(),
                "viewport": self.page.viewport_size,
                "timestamp": datetime.now().isoformat()
            }
            
            # Create screenshots directory
            os.makedirs("screenshots", exist_ok=True)
            screenshot_path = f"screenshots/page_{self.session_id}.png"
            await self.page.screenshot(path=screenshot_path, full_page=True)
            page_info["screenshot"] = screenshot_path
            
            print(f"📸 Screenshot saved: {screenshot_path}")
            return page_info
            
        except Exception as e:
            print(f"⚠️ Error capturing page info: {str(e)}")
            return None

    async def connect_to_agent_and_test(self, prompt: str, workspace_id: str = None):
        """Connect to generative engine and perform testing"""
        if not api_key:
            print("❌ Error: LLM_API_KEY not found in .env file")
            return None

        uri = "wss://ws.generative.engine.capgemini.com/"
        headers = [("x-api-key", api_key)]

        # Capture page state
        page_info = await self.capture_page_info()
        
        # Enhanced prompt with context
        enhanced_prompt = f"""
You are a web accessibility testing assistant analyzing a webpage.

Current Page Information:
- URL: {page_info.get('url', 'N/A') if page_info else 'N/A'}
- Title: {page_info.get('title', 'N/A') if page_info else 'N/A'}

User Request: {prompt}

Please provide detailed accessibility testing analysis and recommendations.
"""

        try:
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
                        "workspaceId": workspace_id,
                        "files": [],
                        "modelKwargs": {
                            "maxTokens": 1024,
                            "temperature": 0.6,
                            "streaming": True,
                            "topP": 0.9
                        }
                    }
                }

                await websocket.send(json.dumps(payload))
                print("\n🤖 Agent analyzing the page...\n")

                full_response = ""
                try:
                    while True:
                        message = await websocket.recv()
                        parsed_message = json.loads(message)
                        
                        if 'data' in parsed_message and 'content' in parsed_message['data']:
                            content = parsed_message['data']['content']
                            full_response += content
                            print(content, end='', flush=True)
                            
                except websockets.exceptions.ConnectionClosed:
                    print("\n\n✅ Agent response complete")
                    
                return full_response
                
        except Exception as e:
            print(f"\n❌ Error connecting to agent: {str(e)}")
            return None

    async def cleanup(self):
        """Close browser and cleanup"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("\n🧹 Cleanup complete")


async def main():
    """Main execution function"""
    
    # ============ CONFIGURATION ============
    TARGET_URL = "https://www.tauron.pl"
    TEST_PROMPT = "Make screnshoots and analyze the color contrast of elements of this webpage to detect accessibility issues, use Knowledgebase for the guidelines and criteria"
    WORKSPACE_ID = knowledgebase_id
    HEADLESS = False  # Set True to hide browser window
    # =======================================
    
    print("=" * 60)
    print("🧪 Playwright Agent Tester - Accessibility Testing")
    print("=" * 60)
    
    # Initialize tester
    tester = PlaywrightAgentTester(TARGET_URL)
    
    try:
        # Setup browser
        success = await tester.setup_browser(headless=HEADLESS)
        
        if not success:
            print("❌ Failed to setup browser. Exiting...")
            return
        
        # Wait for page to stabilize
        print("⏳ Waiting for page to load completely...")
        await asyncio.sleep(3)
        
        # Connect to AI agent
        print("\n" + "=" * 60)
        agent_response = await tester.connect_to_agent_and_test(
            prompt=TEST_PROMPT,
            workspace_id=WORKSPACE_ID
        )
        
        if agent_response:
            print("\n" + "=" * 60)
            print("✅ Testing completed successfully!")
        else:
            print("\n❌ Agent analysis failed")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        await tester.cleanup()
        print("\n" + "=" * 60)
        print("🏁 Test session ended")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
