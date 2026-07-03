# GEP_Workshop_AccessibilityAgentSolution

Accessibility Agent Solution

GEP_AccessibilityAgent

Prerequisites:

Python 3.13
PyCharm (or IDE of your choice)
Git

GEP Studio Set Up
Navigate to https://generative.engine.capgemini.com/
Go to Studio and create new Free Studio
Get the General API Key from Studio Details > Settings
Reference: https://degreed.com/videos/getting-started-with-the-generative-engine-platform-api?d=44211197&inputtype=video&orgsso=capgemini&inputType=Video

Local Environment Set Up
1. Create and active virtual environment (venv)
Run in terminal
   python -m venv venv
Activate venv
  venv\Scripts\activate
2. Install requirements
    pip install -r requirements.txt
Install Playwright browsers:

  python -m playwright install
OR

Install only selected Playwright browser such as Chromium:

    python -m playwright install chromium
3. Create .env
See .env_example
Set LLM_API_KEY
Set KNOWLEDGEBASE_ID
4. Run the Accessibility Agent
Run in terminal:

python file_name.py
Run from IDE:

Right-click file_name.py
Select 'Run ...'
