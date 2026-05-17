"""
FastMCP Server defining 4 core tools for the GitHub Dev Card Generator.
Tools: scrape_github, analyze_profile, generate_card_html, save_card.
"""

import os
import httpx
import json
from typing import Dict, Any, List
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Initialize FastMCP Server
mcp = FastMCP("GitHub Dev Card Tools")

GITHUB_API_URL = "https://api.github.com"


class ProfileAnalysisSchema(BaseModel):
    developer_vibe: str = Field(description="A 1-sentence personality vibe of the developer.")
    top_skills: List[str] = Field(description="Exactly 3 top skills or tags.")
    fun_fact: str = Field(description="A clever or funny inference based on their repos.")
    card_theme: str = Field(description="One of: 'hacker', 'builder', 'researcher', 'designer', 'open-source-hero'.")


def get_github_headers() -> Dict[str, str]:
    """Helper to construct headers with optional GITHUB_TOKEN."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


@mcp.tool
async def scrape_github(username: str) -> Dict[str, Any]:
    """
    Scrapes the public GitHub REST API for profile and repository statistics.
    
    Args:
        username (str): The GitHub username to scrape.
        
    Returns:
        Dict[str, Any]: Profile stats, top 6 repos (name, stars, language, description),
                        and aggregated language data.
    """
    username = username.strip()
    profile_url = f"{GITHUB_API_URL}/users/{username}"
    repos_url = f"{GITHUB_API_URL}/users/{username}/repos"
    
    try:
        async with httpx.AsyncClient() as client:
            headers = get_github_headers()
            
            # Fetch profile
            profile_response = await client.get(profile_url, headers=headers, timeout=10.0)
            if profile_response.status_code != 200:
                raise ValueError(f"GitHub profile not found or rate limited: {profile_response.status_code}")
            
            profile_data = profile_response.json()
            
            # Fetch repositories (up to 100)
            repos_response = await client.get(
                repos_url,
                headers=headers,
                params={"per_page": 100, "sort": "updated"},
                timeout=10.0
            )
            repos = repos_response.json() if repos_response.status_code == 200 else []
            
            # Extract top 6 repos sorted by stars (descending)
            sorted_repos = sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)
            top_6_repos = []
            for r in sorted_repos[:6]:
                top_6_repos.append({
                    "name": r.get("name"),
                    "stars": r.get("stargazers_count", 0),
                    "language": r.get("language") or "Markdown",
                    "description": r.get("description") or "No description provided."
                })
                
            # Aggregate most used languages
            language_counts = {}
            for r in repos:
                lang = r.get("language")
                if lang:
                    language_counts[lang] = language_counts.get(lang, 0) + 1
                    
            # Normalize and sort most used languages
            total_langs = sum(language_counts.values()) or 1
            most_used_languages = {
                lang: round((count / total_langs) * 100, 1)
                for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
            }
            
            total_stars = sum(r.get("stargazers_count", 0) for r in repos)
            
            return {
                "username": username,
                "name": profile_data.get("name") or username,
                "bio": profile_data.get("bio") or "A creative developer on GitHub.",
                "location": profile_data.get("location") or "Earth",
                "public_repos": profile_data.get("public_repos", 0),
                "followers": profile_data.get("followers", 0),
                "total_stars": total_stars,
                "avatar_url": profile_data.get("avatar_url"),
                "top_6_repos": top_6_repos,
                "most_used_languages": most_used_languages,
                "is_mock": False
            }
            
    except Exception as e:
        print(f"Scraper error for {username} ({e}). Falling back to robust mock data.")
        
        # High fidelity customized mock fallback for flawless local testing and demoing
        mock_languages = {
            "Python": 45.0,
            "TypeScript": 30.0,
            "HTML": 15.0,
            "Docker": 10.0
        }
        
        return {
            "username": username,
            "name": f"{username.capitalize()} (Demo Profile)",
            "bio": f"Expert full-stack engineer and automation hacker building agent systems.",
            "location": "San Francisco, CA",
            "public_repos": 38,
            "followers": 142,
            "total_stars": 288,
            "avatar_url": f"https://api.dicebear.com/7.x/bottts/svg?seed={username}",
            "top_6_repos": [
                {"name": "autonomo-agent-sdk", "stars": 128, "language": "Python", "description": "Highly modular Google ADK runner interface for agent orchestration."},
                {"name": "fastmcp-tools", "stars": 64, "language": "Python", "description": "FastMCP server definitions and modular plugin decorators."},
                {"name": "next-neon-dashboard", "stars": 42, "language": "TypeScript", "description": "Glassmorphism UI dashboard featuring live terminal streaming."},
                {"name": "resilient-fastapi-app", "stars": 31, "language": "Python", "description": "FastAPI templates with robust local fallback logic and SSE streams."},
                {"name": "docker-uv-scaffold", "stars": 15, "language": "Docker", "description": "Optimized multi-stage Dockerfiles leveraging Astral uv speed."},
                {"name": "dotfiles", "stars": 8, "language": "Shell", "description": "My bespoke developer workflow environment configurations."}
            ],
            "most_used_languages": mock_languages,
            "is_mock": True
        }


@mcp.tool
async def analyze_profile(github_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invokes Gemini 2.5 Flash to analyze GitHub data and generate rich developer vibes and skills.
    
    Args:
        github_data (Dict[str, Any]): The scraped GitHub profile and repository information.
        
    Returns:
        Dict[str, Any]: JSON payload containing developer_vibe, top_skills, fun_fact, and card_theme.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if gemini_key:
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=gemini_key)
            prompt = (
                f"Analyze this GitHub profile data for user {github_data.get('username')}:\n"
                f"{json.dumps(github_data, indent=2)}\n\n"
                "Return a structured JSON output with: \n"
                "1. developer_vibe: Exactly one sentence capturing their developer personality.\n"
                "2. top_skills: List of exactly 3 skills (technical or architectural).\n"
                "3. fun_fact: Something clever or funny inferred from their repository names or language combinations.\n"
                "4. card_theme: Select the best category that describes them from exactly these 5 choices:\n"
                "   - 'hacker' (focuses on systems, automation, Python/C/Rust, shells, tooling)\n"
                "   - 'builder' (focuses on full-stack, frameworks, large functional apps, clean coding)\n"
                "   - 'researcher' (focuses on algorithms, data science, academic papers, AI/ML models)\n"
                "   - 'designer' (focuses on frontend, visuals, graphics, CSS, highly polished user interfaces)\n"
                "   - 'open-source-hero' (focuses on widely starred repos, libraries, tooling for others, high followers)\n"
            )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ProfileAnalysisSchema,
                ),
            )
            
            # Safely validate and parse output
            result = ProfileAnalysisSchema.model_validate_json(response.text)
            return result.model_dump()
            
        except Exception as e:
            print(f"Gemini generation error: {e}. Cascading into robust deterministic fallback.")
            
    # Deterministic fallback logic to guarantee flawless local execution
    languages = list(github_data.get("most_used_languages", {}).keys())
    top_repo = github_data.get("top_6_repos", [{}])[0].get("name", "projects")
    followers = github_data.get("followers", 0)
    
    # Simple rule-based classification
    if followers > 100:
        theme = "open-source-hero"
        vibe = f"A community-focused builder whose public libraries are empowering other creators worldwide."
        skills = ["Community Building", "Library Design", "API Architecture"]
        fact = "You have amassed an army of followers ready to clone any repository you push to main!"
    elif any(l in ["HTML", "CSS", "TypeScript", "JavaScript"] for l in languages[:2]):
        theme = "designer"
        vibe = "An artistic pixel-perfectionist combining full-stack speed with striking glassmorphic visuals."
        skills = ["Responsive Styling", "React/TypeScript", "UI Interaction Design"]
        fact = "Your UI designs are so smooth they should require a motion sickness warning."
    elif any(l in ["Python", "Rust", "Go", "C++"] for l in languages[:2]):
        theme = "hacker"
        vibe = "A backend automation specialist who commands standard input and output like absolute poetry."
        skills = ["System Automation", "Python Orchestration", "CLI Development"]
        fact = f"You probably spent 4 hours writing a script to automate a task that takes 4 seconds."
    else:
        theme = "builder"
        vibe = "A high-velocity pragmatic developer who transforms complex diagrams into fully deployed production systems."
        skills = ["Containerization", "Full-Stack Deployment", "Modular Engineering"]
        fact = f"Your repository '{top_repo}' proves that you write code faster than most people drink coffee."
        
    return {
        "developer_vibe": vibe,
        "top_skills": skills,
        "fun_fact": fact,
        "card_theme": theme
    }


@mcp.tool
def generate_card_html(username: str, github_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """
    Generates a stunning, self-contained HTML developer card based on themes.
    
    Args:
        username (str): GitHub username.
        github_data (Dict[str, Any]): Profile and repo statistics.
        analysis (Dict[str, Any]): AI assessments and visual theme.
        
    Returns:
        str: Self-contained, highly stylized HTML string.
    """
    theme = analysis.get("card_theme", "builder").lower().strip()
    avatar_url = github_data.get("avatar_url") or f"https://api.dicebear.com/7.x/bottts/svg?seed={username}"
    display_name = github_data.get("name") or username
    vibe = analysis.get("developer_vibe", "Passionate software builder.")
    skills = analysis.get("top_skills", ["Python", "Full-Stack", "Docker"])
    followers = github_data.get("followers", 0)
    public_repos = github_data.get("public_repos", 0)
    fun_fact = analysis.get("fun_fact", "Writing code daily.")
    
    # Render all 3 top repos in an ultra-compact list layout matching user image
    repos_html = ""
    for r in github_data.get("top_6_repos", [])[:3]:
        desc = r.get("description") or "No description provided."
        stars = r.get("stars", 0)
        repos_html += f"""
        <div class="repo-item">
            <div class="repo-left">
                <div class="repo-name">{r['name']}</div>
                <div class="repo-desc">{desc}</div>
            </div>
            <div class="repo-right">
                <i class="fa-solid fa-star"></i> {stars}
            </div>
        </div>
        """
        
    # Render skill badges
    skills_html = ""
    for s in skills:
        skills_html += f'<span class="skill-badge">{s}</span>'
        
    # CSS Visual Theme Palette Mapping exactly styled like the user's premium green design
    themes = {
        "builder": {
            "bg": "#034f37",            # Deep premium emerald/forest green (matches screenshot green)
            "inner_bg": "#023e29",      # Contrast darker green for inner boxes
            "border": "#01301f",        # Ultra-sleek darker green border
            "accent": "#34d399",        # Mint/emerald green accent
            "text": "#ffffff",          # Clean white text
            "subtext": "#a7f3d0",       # Light mint subtext/labels
            "badge_bg": "rgba(2, 62, 41, 0.6)", # Badges translucent green bg
            "badge_border": "rgba(52, 211, 153, 0.2)",
            "font": "'Inter', sans-serif"
        },
        "hacker": {
            "bg": "#0b0f19",            # Deep dark cyber card bg
            "inner_bg": "#040810",      # Rich black contrast box bg
            "border": "#1e293b",        # Slate border
            "accent": "#00ffcc",        # Bright neon cyan accent
            "text": "#ffffff",
            "subtext": "#81e6d9",
            "badge_bg": "rgba(4, 8, 16, 0.6)",
            "badge_border": "rgba(0, 255, 204, 0.2)",
            "font": "'Fira Code', monospace"
        },
        "researcher": {
            "bg": "#1e1b4b",            # Royal deep indigo card bg
            "inner_bg": "#110e3b",      # Contrast dark purple-indigo bg
            "border": "#312e81",        # Indigo border
            "accent": "#c084fc",        # Soft lavender/purple accent
            "text": "#ffffff",
            "subtext": "#e9d5ff",
            "badge_bg": "rgba(17, 14, 59, 0.6)",
            "badge_border": "rgba(192, 132, 252, 0.2)",
            "font": "'Outfit', sans-serif"
        },
        "designer": {
            "bg": "#4c0519",            # Deep rose/burgundy card bg
            "inner_bg": "#31000b",      # Deeper contrast dark rose bg
            "border": "#881337",        # Rose-crimson border
            "accent": "#fb7185",        # Soft pastel rose/pink accent
            "text": "#ffffff",
            "subtext": "#ffe4e6",
            "badge_bg": "rgba(49, 0, 11, 0.6)",
            "badge_border": "rgba(251, 113, 133, 0.2)",
            "font": "'Outfit', sans-serif"
        },
        "open-source-hero": {
            "bg": "#451a03",            # Deep bronze/amber card bg
            "inner_bg": "#2d0f00",      # Contrast dark rust bg
            "border": "#78350f",        # Bronze border
            "accent": "#fbbf24",        # Golden/amber yellow accent
            "text": "#ffffff",
            "subtext": "#fef3c7",
            "badge_bg": "rgba(45, 15, 0, 0.6)",
            "badge_border": "rgba(251, 191, 36, 0.2)",
            "font": "'Outfit', sans-serif"
        }
    }
    
    cfg = themes.get(theme, themes["builder"])
    
    # Beautiful responsive HTML/CSS layout
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{display_name}'s Developer Card</title>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Inter:wght@400;600;800&family=Outfit:wght@400;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            background: #090d16;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            font-family: {cfg['font']}, sans-serif;
            color: {cfg['text']};
        }}
        
        .card-container {{
            background: {cfg['bg']};
            border-radius: 24px;
            width: 100%;
            max-width: 340px;
            padding: 16px 18px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
            position: relative;
            font-family: {cfg['font']}, sans-serif;
        }}
        
        /* Profile Header */
        .profile-section {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }}
        
        .avatar-frame {{
            position: relative;
            display: inline-block;
        }}
        
        .avatar-img {{
            width: 60px;
            height: 60px;
            border-radius: 12px;
            border: 2px solid {cfg['accent']};
            display: block;
            object-fit: cover;
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .pro-badge {{
            position: absolute;
            bottom: -5px;
            left: 50%;
            transform: translateX(-50%);
            background: {cfg['accent']};
            color: {cfg['inner_bg']};
            font-size: 0.52rem;
            font-weight: 900;
            padding: 1.5px 6px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }}
        
        .meta-text {{
            display: flex;
            flex-direction: column;
            gap: 2px;
            overflow: hidden;
        }}
        
        .meta-name {{
            font-size: 1.15rem;
            font-weight: 800;
            line-height: 1.15;
            color: {cfg['text']};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .meta-tag {{
            font-size: 0.78rem;
            font-weight: 600;
            color: {cfg['subtext']};
        }}
        
        /* Bio / Vibe Block */
        .vibe-block {{
            font-size: 0.85rem;
            line-height: 1.35;
            color: {cfg['text']};
            margin: 10px 0 12px 0;
            text-align: center;
        }}
        
        /* Stats Grid - 2 Columns styled like user screenshot */
        .stats-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 12px;
        }}
        
        .stat-card {{
            background: {cfg['inner_bg']};
            border: 1px solid {cfg['border']};
            border-radius: 12px;
            padding: 8px 6px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 1.3rem;
            font-weight: 800;
            color: {cfg['accent']};
            margin-bottom: 2px;
        }}
        
        .stat-label {{
            font-size: 0.58rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: {cfg['subtext']};
        }}
        
        /* Skill badges */
        .skills-section {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 6px;
            margin-bottom: 12px;
        }}
        
        .skill-badge {{
            background: {cfg['badge_bg']};
            border: 1px solid {cfg['badge_border']};
            border-radius: 20px;
            padding: 4px 10px;
            font-size: 0.7rem;
            font-weight: 600;
            color: {cfg['accent']};
            transition: all 0.2s ease;
        }}
        
        .skill-badge:hover {{
            transform: scale(1.05);
            background: {cfg['accent']};
            color: {cfg['inner_bg']};
        }}
        
        /* Repositories Title */
        .section-title {{
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            color: {cfg['accent']};
            margin-bottom: 8px;
            text-align: center;
        }}
        
        /* Repo Items - Sleek Rounded Card Rows */
        .repos-container {{
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 12px;
        }}
        
        .repo-item {{
            background: {cfg['inner_bg']};
            border: 1px solid {cfg['border']};
            border-radius: 12px;
            padding: 8px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            transition: all 0.25s ease;
        }}
        
        .repo-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            border-color: {cfg['accent']};
        }}
        
        .repo-left {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            overflow: hidden;
            flex: 1;
        }}
        
        .repo-name {{
            font-size: 0.85rem;
            font-weight: 700;
            color: {cfg['accent']};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .repo-desc {{
            font-size: 0.7rem;
            color: rgba(255, 255, 255, 0.6);
            line-height: 1.3;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .repo-right {{
            display: flex;
            align-items: center;
            gap: 4px;
            color: #fbbf24;
            font-weight: 700;
            font-size: 0.78rem;
            flex-shrink: 0;
        }}
        
        /* Footer Fun Fact matching user screenshot style */
        .funfact-box {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 0 4px;
            margin-top: 6px;
        }}
        
        .funfact-icon {{
            font-size: 0.9rem;
            flex-shrink: 0;
        }}
        
        .funfact-text {{
            font-size: 0.7rem;
            line-height: 1.35;
            color: {cfg['subtext']};
            font-style: italic;
        }}
    </style>
</head>
<body>

    <div class="card-container">
        <!-- Header -->
        <div class="profile-section">
            <div class="avatar-frame">
                <img class="avatar-img" src="{avatar_url}" alt="{display_name}" />
                <span class="pro-badge">PRO</span>
            </div>
            <div class="meta-text">
                <div class="meta-name">{display_name}</div>
                <div class="meta-tag">@{username}</div>
            </div>
        </div>
        
        <!-- Vibe Statement -->
        <div class="vibe-block">
            {vibe}
        </div>
        
        <!-- Skills -->
        <div class="skills-section">
            {skills_html}
        </div>
        
        <!-- Stats Grid - 2 Columns styled like user screenshot -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{public_repos}</div>
                <div class="stat-label">Repositories</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{followers}</div>
                <div class="stat-label">Followers</div>
            </div>
        </div>
        
        <!-- Featured Projects Title -->
        <div class="section-title">Featured Projects</div>
        <div class="repos-container">
            {repos_html}
        </div>
        
        <!-- Fun Fact Footer -->
        <div class="funfact-box">
            <span class="funfact-icon">💡</span>
            <span class="funfact-text">{fun_fact}</span>
        </div>

    </div>

</body>
</html>
"""
    return html


@mcp.tool
def save_card(username: str, html: str) -> str:
    """
    Saves a generated self-contained HTML developer card to static/cards directory.
    
    Args:
        username (str): Target GitHub username.
        html (str): The self-contained HTML card content.
        
    Returns:
        str: Relative URL path referencing the saved developer card.
    """
    username = username.strip().lower()
    
    # Save path relative to where main backend processes run
    static_cards_dir = os.path.join("static", "cards")
    os.makedirs(static_cards_dir, exist_ok=True)
    
    file_path = os.path.join(static_cards_dir, f"{username}.html")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)
            
        relative_url = f"/static/cards/{username}.html"
        print(f"Saved card for {username} to {file_path}")
        return relative_url
    except Exception as e:
        error_msg = f"Failed to save dev card html on server disk: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)


if __name__ == "__main__":
    mcp.run()
