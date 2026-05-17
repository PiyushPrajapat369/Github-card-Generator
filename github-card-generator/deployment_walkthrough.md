 ☁️ Google Cloud Run Deployment Walkthrough & Architecture Guide

This guide details the architecture, configuration, and step-by-step instructions for deploying the **GitHub Dev Card Generator** (FastAPI Backend + Nginx Frontend) onto Google Cloud Run.

---

## 🏗️ Deployment Architecture

The application is split into two modular microservices, allowing independent scaling, enhanced security, and cost efficiency:

```
🌐 User Web Browser
      │ (HTTPS Request)
      ├──────────────────────────────┐
      ▼                              ▼
🚀 Nginx Frontend              🐍 FastAPI Backend
(Cloud Run Service)           (Cloud Run Service)
      │                              │
      │ (HTML Assets)                ├─► [🐙 GitHub API] (Fetch profile)
      ▼                              ├─► [🧠 Gemini API] (Generate AI insights)
🌐 Web Page loaded                   └─► (Returns SSE Streaming HTML)
```

1. **FastAPI Backend Service (`github-card-backend`)**:
   - Built on `python:3.12-slim` using the high-speed `uv` package installer.
   - Orchestrates the profile scraper and Gemini LLM analysis.
   - Listens dynamically on the port specified by Cloud Run (defaulting to `8080`).
   - Run under fully authenticated and secured API environment variables.

2. **Nginx Frontend Service (`github-card-frontend`)**:
   - Built on the ultra-lightweight `nginx:alpine` image.
   - Configured with `envsubst` to dynamically inject the backend API URL at container startup.
   - Listens on port `80`, with incoming requests routed directly from Cloud Run.

---

## ⚡ Stateless & Cloud Run Resilience Upgrades

We have optimized the codebase to be 100% cloud-native, resolving common serverless/stateless container hurdles:

### 1. Stateless On-the-Fly Regeneration Fallback
Because Cloud Run instances are stateless and scale down to zero or scale horizontally, any HTML cards generated on one container instance and saved to local disk (`static/cards/*.html`) may result in **404 Not Found** errors if the user's web browser makes a subsequent `GET` request and hits a new or restarted container instance.

To solve this, we updated [backend/main.py](file:///c:/Users/ASUS/OneDrive/Desktop/ADK%20Google%20session/github-card-generator/backend/main.py#L74-L101) to support **Stateless-Resilience**:
- If a client requests a card via `/card/{username}` and it's missing from local disk, the backend dynamically rebuilds and compiles the card on-the-fly and saves it as a cached item. This self-healing design makes local file state loss completely invisible to the user!

### 2. Dynamic Port Allocation
- We modified the [backend/Dockerfile](file:///c:/Users/ASUS/OneDrive/Desktop/ADK%20Google%20session/github-card-generator/backend/Dockerfile#L30-L32) to use shell-form Execution (`CMD uvicorn...`) with `PORT` expansion (`${PORT:-8080}`). This ensures that uvicorn always binds to the exact port allocated dynamically by Cloud Run, preventing deployment crashes.

---

## 🚀 Step-by-Step Deployment Guide

We created two unified deployment scripts at the project root to automate the entire process:
- 📄 [deploy_to_cloud_run.ps1](file:///c:/Users/ASUS/OneDrive/Desktop/ADK%20Google%20session/github-card-generator/deploy_to_cloud_run.ps1) (PowerShell automation engine)
- ⚙️ [deploy_to_cloud_run.bat](file:///c:/Users/ASUS/OneDrive/Desktop/ADK%20Google%20session/github-card-generator/deploy_to_cloud_run.bat) (Command Prompt entry point)

### Prerequisites
Before deploying, make sure you have the following installed on your machine:
*   [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install)
*   An active Google Cloud Platform account with billing enabled.

---

### 💻 Executing the Deployment

Follow these three simple steps to launch your app:

#### Step 1: Open Your Terminal
Open PowerShell or your preferred terminal inside the project directory:
```powershell
cd "c:\Users\ASUS\OneDrive\Desktop\ADK Google session\github-card-generator"
```

#### Step 2: Run the Deployment Script
Simply run the batch file:
```cmd
.\deploy_to_cloud_run.bat
```
*(Alternatively, run the PowerShell script directly: `powershell -ExecutionPolicy Bypass -File .\deploy_to_cloud_run.ps1`)*

#### Step 3: Follow the Interactive Wizard
The script will perform the following actions automatically:
1. **Verify your local installation** of the Google Cloud SDK.
2. **Log you in securely** via your browser (`gcloud auth login`) if not already authenticated.
3. **List all your active GCP projects** and ask you to select or enter one.
4. **Enable required services** (`run.googleapis.com` and `cloudbuild.googleapis.com`) on your project.
5. **Parse credentials** automatically from your local `.env` files (e.g. `GEMINI_API_KEY`, `GITHUB_TOKEN`). If missing, it will securely prompt you to input them.
6. **Build and Deploy the Backend Service** (`github-card-backend`) directly from your source directory to Cloud Run.
7. **Obtain the secure Backend URL** automatically.
8. **Inject the Backend URL and Deploy the Frontend Service** (`github-card-frontend`) to Cloud Run on port 80.
9. **Display the live URLs** for you to launch and share!

---

*Tip: The `gcloud run deploy --source` command automatically builds your code using cloud resources (Google Cloud Build) and pushes it to Artifact Registry. This means you **do not need Docker installed locally** on your machine to deploy this application!*

---

## 🛠️ Deployment Troubleshooting

| Symptom | Probable Cause | Resolution |
| :--- | :--- | :--- |
| **`gcloud: Command not found`** | Google Cloud SDK not installed or not in PATH | Download and install Google Cloud SDK. Restart your terminal session so the PATH updates. |
| **API Activation Hangs** | First-time API configuration in a fresh GCP project | Enabling Cloud Run and Cloud Build APIs for the first time can take up to 2-3 minutes. Allow the script to run. |
| **`403 Forbidden` API rate limits** | GitHub API rate limiting (without a token) | Ensure a valid `GITHUB_TOKEN` is supplied to the deployment wizard. This grants 5,000 requests/hr. |
| **CORS Errors in Browser** | Mismatched endpoints | The automated script automatically sets `BACKEND_URL` in the frontend container to resolve any CORS cross-talk. |
