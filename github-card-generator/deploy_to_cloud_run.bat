@echo off
REM Windows Command Prompt Entry Point for Cloud Run Deployment

echo Starting Google Cloud Run Orchestrated Deployment Pipeline...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_to_cloud_run.ps1"
pause
