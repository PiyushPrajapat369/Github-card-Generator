"""
FastAPI application for the GitHub Dev Card Generator backend.
Orchestrates the github_card_agent and exposes REST / SSE streaming endpoints.
"""

import os
import json
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from dotenv import load_dotenv

# Load Environment Configuration
load_dotenv()

# Setup FastAPI App
app = FastAPI(
    title="GitHub Dev Card Generator Backend",
    description="FastAPI app with Google ADK agent runner and FastMCP tools.",
    version="1.1.0"
)

# Enable CORS for the Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CardRequest(BaseModel):
    username: str = Field(..., description="The GitHub username to analyze.")


# Safely import the github_card_agent and ADK runner services
try:
    from google.adk.runners import InMemoryRunner
    from google.adk.sessions import InMemorySessionService
    from google.adk.memory import InMemoryMemoryService
    from agent import github_card_agent
    from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card
    
    # 2. Sets up InMemorySessionService and InMemoryMemoryService
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()
    
    # 3. Creates a Runner bound to the agent
    runner = InMemoryRunner(
        agent=github_card_agent
    )
    ADK_AVAILABLE = True
except Exception as e:
    print(f"WARNING: Google ADK dependencies failed to load ({e}). Running in direct fallback mode.")
    ADK_AVAILABLE = False
    from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card


# 6. GET /health endpoint for Cloud Run health checks
@app.get("/health")
@app.get("/api/health")
def health_check():
    """Simple API status checks and system configurations."""
    return {
        "status": "healthy",
        "adk_loaded": ADK_AVAILABLE,
        "github_token_configured": bool(os.getenv("GITHUB_TOKEN")),
        "gemini_api_key_configured": bool(os.getenv("GEMINI_API_KEY"))
    }


# 5. GET /card/{username} endpoint to serve saved cards from static/cards/
@app.get("/card/{username}", response_class=HTMLResponse)
@app.get("/static/cards/{username}.html", response_class=HTMLResponse)
async def serve_card(username: str):
    """Serves compiled developer cards from disk, or dynamically compiles on-the-fly if missing."""
    username = username.strip().lower()
    file_path = os.path.join("static", "cards", f"{username}.html")
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    if not os.path.exists(file_path):
        try:
            print(f"Stateless Cache Miss: Dynamically compiling card for {username}...")
            github_data = await scrape_github(username)
            analysis = await analyze_profile(github_data)
            content = generate_card_html(username, github_data, analysis)
            save_card(username, content)
            return HTMLResponse(content=content)
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Developer card for '{username}' was missing and could not be generated dynamically: {e}"
            )
            
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read cached card: {e}")


# 4. POST /generate endpoint
@app.post("/generate")
@app.post("/api/generate")
async def generate_card(request: CardRequest):
    """
    POST generate endpoint that:
    - Creates or reuses a session by username.
    - Runs the agent with message 'Generate a dev card for {username}'.
    - Streams the agent events and returns the final card URL and HTML.
    """
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")
        
    async def event_generator():
        # Create or reuse session based on username
        session_id = f"session_{username.lower()}"
        user_id = "user_client"
        prompt = f"Generate a dev card for {username}"
        
        yield f"event: status\ndata: {json.dumps({'message': f'Initializing agent pipeline for user: {username}'})}\n\n"
        
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not ADK_AVAILABLE or not gemini_key:
            # Direct Mocking Fallback Pipeline Stream
            yield f"event: status\ndata: {json.dumps({'message': 'Bypassing agent (local fallback). Scraping GitHub data...'})}\n\n"
            github_data = await scrape_github(username)
            yield f"event: status\ndata: {json.dumps({'message': 'Running profile AI analysis...'})}\n\n"
            analysis = await analyze_profile(github_data)
            yield f"event: status\ndata: {json.dumps({'message': 'Compiling beautiful HTML Dev Card...'})}\n\n"
            html = generate_card_html(username, github_data, analysis)
            yield f"event: status\ndata: {json.dumps({'message': 'Saving card layout to disk...'})}\n\n"
            save_card(username, html)
            
            card_url = f"/card/{username.lower()}"
            yield f"event: result\ndata: {json.dumps({'success': True, 'card_url': card_url, 'html': html, 'analysis': analysis, 'mode': 'Direct Fallback'})}\n\n"
            return
            
        try:
            from google.genai import types
            new_message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            
            yield f"event: status\ndata: {json.dumps({'message': f'Orchestrating agent for username: {username}'})}\n\n"
            
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message
            ):
                # Stream thought logs/events
                if hasattr(event, "content") and event.content:
                    text_chunk = ""
                    if hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                text_chunk += part.text
                    elif isinstance(event.content, str):
                        text_chunk = event.content
                        
                    if text_chunk:
                        yield f"event: thought\ndata: {json.dumps({'chunk': text_chunk})}\n\n"
                        
            # Read compiled card from disk (or run compiler fallback if needed)
            card_path = os.path.join("static", "cards", f"{username.lower()}.html")
            if not os.path.exists(card_path):
                yield f"event: status\ndata: {json.dumps({'message': 'Agent finished. Compiling card layout...'})}\n\n"
                github_data = await scrape_github(username)
                analysis = await analyze_profile(github_data)
                html = generate_card_html(username, github_data, analysis)
                save_card(username, html)
            else:
                with open(card_path, "r", encoding="utf-8") as f:
                    html = f.read()
                github_data = await scrape_github(username)
                analysis = await analyze_profile(github_data)
                
            card_url = f"/card/{username.lower()}"
            yield f"event: result\ndata: {json.dumps({'success': True, 'card_url': card_url, 'html': html, 'analysis': analysis, 'mode': 'ADK Agent Orchestration'})}\n\n"
            
        except Exception as e:
            yield f"event: status\ndata: {json.dumps({'message': f'Agent runner error: {e}. Executing immediate fallback...'})}\n\n"
            github_data = await scrape_github(username)
            analysis = await analyze_profile(github_data)
            html = generate_card_html(username, github_data, analysis)
            save_card(username, html)
            card_url = f"/card/{username.lower()}"
            yield f"event: result\ndata: {json.dumps({'success': True, 'card_url': card_url, 'html': html, 'analysis': analysis, 'mode': 'Fallback'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    # Executed on port 8080 as requested
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8080))
    print(f"Starting FastAPI on {host}:{port}...")
    uvicorn.run("main:app", host=host, port=port, reload=True)
