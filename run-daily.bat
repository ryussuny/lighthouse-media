@echo off
chcp 65001 >nul
title Lighthouse Media - Daily Routine

cd /d "%~dp0"

if not exist ".env" (
    set /p APIKEY="Anthropic API Key를 입력하세요: "
    echo ANTHROPIC_API_KEY=%APIKEY%> .env
)

echo [*] 일일 루틴 실행 (트렌드→기획→스크립트→발행)
echo.
node scripts/daily-routine.js
pause
