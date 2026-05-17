# GitHub Dev Card Generator - Google Cloud Run Orchestrated Deployment Script
# This script automates the complete multi-service deployment flow to Google Cloud Run.

$ErrorActionPreference = "Stop"
$clearScreen = Clear-Host

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   *** GitHub Dev Card Generator - Cloud Run Deployer *** " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "This script builds and deploys both your backend and frontend"
Write-Host "services to Google Cloud Run in a fully connected architecture."
Write-Host ""

# 1. Verify gcloud installation
Write-Host "[1/7] Verifying Google Cloud SDK installation..." -ForegroundColor Blue
$gcloudCheck = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloudCheck) {
    Write-Host "[ERROR] Error: Google Cloud SDK (gcloud) is not installed or not in your system PATH." -ForegroundColor Red
    Write-Host "Please install it from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    Write-Host "After installation, open a new PowerShell window and run this script again." -ForegroundColor Yellow
    Exit
}
Write-Host "[OK] Google Cloud SDK is ready!" -ForegroundColor Green
Write-Host ""

# 2. Check GCP Authentication
Write-Host "[2/7] Checking Google Cloud Authentication..." -ForegroundColor Blue
$authList = gcloud auth list --format="value(account)" 2>$null
if (-not $authList) {
    Write-Host "[AUTH] No active account discovered. Initiating Google Cloud login..." -ForegroundColor Yellow
    gcloud auth login
} else {
    Write-Host "[OK] Active Google Account detected: $authList" -ForegroundColor Green
}
Write-Host ""

# 3. Select Google Cloud Project
Write-Host "[3/7] Project Setup and Selection..." -ForegroundColor Blue
Write-Host "Fetching available Google Cloud projects..." -ForegroundColor Gray
$projects = gcloud projects list --format="value(projectId)"
if (-not $projects) {
    Write-Host "[WARNING] No GCP projects discovered. Let's create a new one, or enter your project ID manually." -ForegroundColor Yellow
    $projectId = Read-Host -Prompt "Enter your GCP Project ID (e.g. my-github-cards)"
} else {
    Write-Host "Available Projects:" -ForegroundColor Gray
    $index = 1
    $projArray = @()
    foreach ($p in $projects) {
        Write-Host "  [$index] $p"
        $projArray += $p
        $index++
    }
    Write-Host "  [$index] Enter a custom Project ID manually"
    
    $choice = Read-Host -Prompt "Select a project [1-$index]"
    if ($choice -as [int] -and [int]$choice -ge 1 -and [int]$choice -lt $index) {
        $projectId = $projArray[[int]$choice - 1]
    } else {
        $projectId = Read-Host -Prompt "Enter your GCP Project ID"
    }
}

$projectId = $projectId.Trim()
if (-not $projectId) {
    Write-Host "[ERROR] Error: Project ID cannot be empty." -ForegroundColor Red
    Exit
}

Write-Host "Setting active project to: $projectId..." -ForegroundColor Gray
gcloud config set project $projectId
Write-Host "[OK] Project configured successfully!" -ForegroundColor Green
Write-Host ""

# 4. Enable Google Cloud APIs
Write-Host "[4/7] Enabling Required Cloud APIs (Cloud Run and Cloud Build)..." -ForegroundColor Blue
Write-Host "This might take a minute if this is a fresh project..." -ForegroundColor Gray
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --quiet
Write-Host "[OK] APIs enabled successfully!" -ForegroundColor Green
Write-Host ""

# 5. Extract Credentials from .env
Write-Host "[5/7] Preparing Environment Variables and Credentials..." -ForegroundColor Blue
$geminiKey = ""
$githubToken = ""

# Locate .env file
$envPath = ""
if (Test-Path ".env") { $envPath = ".env" }
elseif (Test-Path "backend/.env") { $envPath = "backend/.env" }

if ($envPath) {
    Write-Host "Discovered active credentials in $envPath. Parsing..." -ForegroundColor Gray
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line.Split('=', 2)
            if ($parts.Length -eq 2) {
                $k = $parts[0].Trim()
                $v = $parts[1].Trim()
                if ($k -eq "GEMINI_API_KEY") { $geminiKey = $v }
                if ($k -eq "GITHUB_TOKEN") { $githubToken = $v }
            }
        }
    }
}

# If keys are missing or placeholders, prompt the user
if (-not $geminiKey -or $geminiKey -like "*AIzaSy*placeholder*") {
    $geminiKey = Read-Host -Prompt "Enter your GEMINI_API_KEY (Required for AI generation)"
}
if (-not $githubToken -or $githubToken -like "*ghp_*placeholder*") {
    $githubToken = Read-Host -Prompt "Enter your GITHUB_TOKEN (Highly recommended to bypass rate limits)"
}

$geminiKey = $geminiKey.Trim()
$githubToken = $githubToken.Trim()

if (-not $geminiKey) {
    Write-Host "[ERROR] Error: Gemini API Key is required." -ForegroundColor Red
    Exit
}

Write-Host "[OK] Credentials successfully compiled!" -ForegroundColor Green
Write-Host ""

# 6. Deploy Backend Service to Cloud Run
Write-Host "[6/7] Deploying Backend Service to Cloud Run..." -ForegroundColor Blue
Write-Host "Building container image using Cloud Build and deploying service..." -ForegroundColor Gray
Write-Host "Please wait, this will take about 1-2 minutes..." -ForegroundColor Gray

gcloud run deploy github-card-backend `
    --source ./backend `
    --region us-central1 `
    --allow-unauthenticated `
    --set-env-vars="GEMINI_API_KEY=$geminiKey,GITHUB_TOKEN=$githubToken,ENV=production,HOST=0.0.0.0" `
    --quiet

# Retrieve the backend service URL
$backendUrl = gcloud run services describe github-card-backend --region us-central1 --format="value(status.url)"
if (-not $backendUrl) {
    Write-Host "[ERROR] Error: Failed to retrieve deployed Backend URL." -ForegroundColor Red
    Exit
}

Write-Host "[OK] Backend deployed successfully! URL: $backendUrl" -ForegroundColor Green
Write-Host ""

# 7. Deploy Frontend Service to Cloud Run
Write-Host "[7/7] Deploying Frontend Service to Cloud Run..." -ForegroundColor Blue
Write-Host "Injecting Backend URL ($backendUrl) into Frontend Container..." -ForegroundColor Gray
Write-Host "Building and deploying frontend to Cloud Run..." -ForegroundColor Gray

gcloud run deploy github-card-frontend `
    --source ./frontend `
    --region us-central1 `
    --allow-unauthenticated `
    --port 80 `
    --set-env-vars="BACKEND_URL=$backendUrl" `
    --quiet

$frontendUrl = gcloud run services describe github-card-frontend --region us-central1 --format="value(status.url)"

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "*** SUCCESS! Your application is fully deployed! ***" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Link Frontend URL:  $frontendUrl" -ForegroundColor Cyan
Write-Host "Link Backend URL:   $backendUrl" -ForegroundColor Gray
Write-Host ""
Write-Host "You can open the Frontend URL in your browser to generate your cards!" -ForegroundColor Green
Write-Host "Press any key to exit..."
[void]$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
