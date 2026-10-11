@echo off
chcp 65001 >nul
cd /d "C:\Users\ryuss\lighthouse-media"
set PATH=%PATH%;C:\Users\ryuss\AppData\Local\Microsoft\WinGet\Links
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="ANTHROPIC_API_KEY" set ANTHROPIC_API_KEY=%%b
)
py -u scripts\daily-premium-post.py >> logs\premium.log 2>&1
