@echo off
chcp 65001 >nul
title Lighthouse Media - AI Company

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║     LIGHTHOUSE MEDIA - AI Company System        ║
echo ╚══════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: .env 파일 확인
if not exist ".env" (
    echo [!] .env 파일이 없습니다. 생성합니다...
    set /p APIKEY="Anthropic API Key를 입력하세요: "
    echo ANTHROPIC_API_KEY=%APIKEY%> .env
    echo [OK] .env 파일 생성 완료
    echo.
)

:: node_modules 확인
if not exist "node_modules" (
    echo [*] 패키지 설치 중...
    npm install
    echo.
)

echo [*] 3D 대시보드 시작...
echo [*] 브라우저에서 http://localhost:3000 을 열어주세요
echo.
start http://localhost:3000
node dashboard/server.js
pause
