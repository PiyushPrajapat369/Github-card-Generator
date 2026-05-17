# 🚀 GitHub Developer Profile Card Generator

A modern, cloud-native web application that analyzes GitHub profiles using **Gemini AI** and generates beautiful, shareable developer cards with dynamic metrics and personalized AI-driven developer archetypes.

Developed with a microservices architecture featuring a high-performance **FastAPI backend** and a lightweight, responsive **frontend served via Nginx**.

---

## 🎨 Features & Highlights

*   **🔍 AI-Powered Insights**: Scrapes GitHub profile metrics and runs them through Google Gemini LLM to analyze coding styles, strengths, and developer personality traits.
*   **⚡ Serverless-Ready & Resilient**: Built with stateless containerization guidelines. Card assets are dynamically regenerated on-the-fly to handle horizontal auto-scaling and ephemeral storage behavior seamlessly.
*   **🌊 Server-Sent Events (SSE)**: Utilizes streaming responses (`EventSource`) to show real-time progress updates (e.g., "Fetching profile...", "Analyzing language distribution...", "Generating AI summary...") for a engaging user experience.
*   **🐳 Dockerized Microservices**: Features fully dockerized containers for both backend (`python:3.12-slim` + `uv`) and frontend (`nginx:alpine`) setup.
*   **🌌 Rich Visuals & Design**: Fully responsive, beautiful modern typography, dynamic gradients, and sleek cards.
*   **🛠️ Direct Deployment Scripts**: Integrated PowerShell/Command script configurations to deploy instantly to Google Cloud Run with single-click automation.

---

## 🏗️ Architecture

The app is built as two highly decoupled, scalable services:

```
🌐 Web Browser (User)
       │ (HTTPS Requests)
       ├──────────────────────────────┐
       ▼                              ▼
🚀 Nginx Frontend              🐍 FastAPI Backend
(Static Assets on Port 80)      (Port 8080 or dynamic)
       │                              │
       │ (HTML/CSS Assets)            ├─► [🐙 GitHub API] (Fetch user metadata)
       ▼                              ├─► [🧠 Gemini API] (LLM character analysis)
🌐 App Loaded in Browser              └─► (Returns SSE and Compiled Cards)
```

1.  **FastAPI Backend (`backend`)**: Scrapes the public GitHub profile, fetches language distributions, orchestrates the Gemini API prompts, and serves beautiful dynamically compiled cards.
2.  **Nginx Frontend (`frontend`)**: Simple, fast responsive landing page that queries the backend using EventSource to stream generation steps and render the resulting card.

---

## ⚙️ Project Setup & Configuration

### Prerequisites
- Python 3.12+ (if running backend locally without Docker)
- A GitHub Personal Access Token (for rate-limit prevention)
- A Google Gemini API Key

### Environment Variables
To get started, clone the repository, copy the `.env.example` file to `.env`, and provide your API keys:

```bash
# Copy example environment variables
cp .env.example .env
```

Open `.env` and fill out your details:
```env
# Gemini API Key (Required for the LLM orchestration)
GEMINI_API_KEY=your_gemini_api_key_here

# GitHub Token (Optional but highly recommended to avoid API rate limiting)
GITHUB_TOKEN=your_github_token_here

# Server settings
HOST=0.0.0.0
PORT=8000
ENV=development
```

---

## 🚀 Running the App Locally

### Method 1: Using Docker Compose (Recommended)
Launch the entire multi-container app with a single command:
```bash
docker-compose up --build
```
Once built, visit `http://localhost:80` in your browser.

### Method 2: Manual Local Running
1.  **Backend Setup**:
    ```bash
    cd backend
    pip install -r requirements.txt
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
2.  **Frontend Setup**:
    Simply open the `frontend/index.html` file in your browser, or serve it using any simple static files server. Note: You will need to set up local CORS access or matching API endpoints.

---

## ☁️ Deploying to Google Cloud Run

We have included scripts to build, configure, and launch this project in GCP without requiring Docker to be installed locally (it uses Google Cloud Build on the cloud):

-   **Windows (Command Prompt)**: Run `.\deploy_to_cloud_run.bat`
-   **Windows (PowerShell)**: Run `powershell -ExecutionPolicy Bypass -File .\deploy_to_cloud_run.ps1`

The automated scripts will:
1. Validate your GCP CLI configuration and authenticate.
2. Select your active project.
3. Automatically secure, extract, and apply environment variables (excluding key storage in repo).
4. Deploy the FastAPI backend and use its live endpoint to configure the Nginx frontend dynamically!

---

## 🛡️ License

This project is licensed under the MIT License - feel free to build on top of it!
