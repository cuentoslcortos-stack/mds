@echo off
REM ============================================================
REM  Sistema MDS - detener el motor RAG
REM ============================================================
title Sistema MDS - Detener
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" -Detener
echo.
pause
