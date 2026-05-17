"""
End-to-end testing pipeline for the 4 FastMCP tools.
Calls scrape_github, analyze_profile, and generate_card_html in sequence.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure we can load local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card
    IMPORTS_OK = True
except ImportError as e:
    print(f"Import Error: {e}")
    IMPORTS_OK = False

# Load API keys from environment
load_dotenv()


async def run_pipeline():
    if not IMPORTS_OK:
        print("✗ Pipeline halted: Failed to import MCP tools from mcp_server.py.")
        return

    print("======================================================================")
    print("           FASTCON MCP PIPELINE RUNNER: END-TO-END TEST               ")
    print("======================================================================")
    
    username = "torvalds"
    
    # -------------------------------------------------------------
    # Step 1: Scrape GitHub Profile & Repository Data
    # -------------------------------------------------------------
    print(f"\n[Step 1] Executing scrape_github for username '{username}'...")
    try:
        github_data = await scrape_github(username)
        print("✓ scrape_github COMPLETED SUCCESSFULLY.")
        print(f"  └─ Full Name: {github_data.get('name')}")
        print(f"  └─ Public Repos: {github_data.get('public_repos')}")
        print(f"  └─ Followers Count: {github_data.get('followers')}")
        print(f"  └─ Top Repository: {github_data.get('top_6_repos')[0].get('name') if github_data.get('top_6_repos') else 'None'}")
        print(f"  └─ Top Star Count: {github_data.get('top_6_repos')[0].get('stars') if github_data.get('top_6_repos') else 0} stars")
        print(f"  └─ Core Languages: {list(github_data.get('most_used_languages', {}).keys())[:3]}")
    except Exception as e:
        print(f"✗ scrape_github FAILED with error: {e}")
        return

    # -------------------------------------------------------------
    # Step 2: Pass scraped data to Gemini AI profiling analysis
    # -------------------------------------------------------------
    print(f"\n[Step 2] Passing scraped parameters into analyze_profile...")
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("  [!NOTE] GEMINI_API_KEY environment variable is missing.")
        print("          Running in robust local rule-based fallback classification mode.")
    else:
        print("  [INFO] GEMINI_API_KEY detected. Dispatching API call to Gemini 2.5 Flash...")
        
    try:
        analysis = await analyze_profile(github_data)
        print("✓ analyze_profile COMPLETED SUCCESSFULLY.")
        print(f"  └─ Card Theme: {analysis.get('card_theme')}")
        print(f"  └─ Developer Vibe: \"{analysis.get('developer_vibe')}\"")
        print(f"  └─ Skills Listed: {analysis.get('top_skills')}")
        print(f"  └─ Custom Fun Fact: {analysis.get('fun_fact')}")
    except Exception as e:
        print(f"✗ analyze_profile FAILED with error: {e}")
        return

    # -------------------------------------------------------------
    # Step 3: Generate the self-contained HTML layout card
    # -------------------------------------------------------------
    print(f"\n[Step 3] Rendering visual board using generate_card_html...")
    try:
        html = generate_card_html(username, github_data, analysis)
        print("✓ generate_card_html COMPLETED SUCCESSFULLY.")
        print(f"  └─ Document Size: {len(html)} characters of clean, self-contained HTML/CSS.")
    except Exception as e:
        print(f"✗ generate_card_html FAILED with error: {e}")
        return

    # -------------------------------------------------------------
    # Step 4: Save compiled layout file
    # -------------------------------------------------------------
    print(f"\n[Step 4] Committing file to server static layout disk using save_card...")
    try:
        relative_path = save_card(username, html)
        print("✓ save_card COMPLETED SUCCESSFULLY.")
        print(f"  └─ Served Relative Link: {relative_path}")
        
        # Format clean native file paths for easy opening
        full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "cards", f"{username.lower()}.html"))
        print(f"  └─ Saved Local Absolute Path: {full_path}")
    except Exception as e:
        print(f"✗ save_card FAILED with error: {e}")
        return

    print("\n======================================================================")
    print("             SUMMARY: ALL 4 MCP TOOLS EXECUTED SUCCESSFULLY!          ")
    print("======================================================================")
    print(f"Theme Selected : {analysis.get('card_theme')}")
    print(f"Developer Vibe : \"{analysis.get('developer_vibe')}\"")
    print("======================================================================")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
