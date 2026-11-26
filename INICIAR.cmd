@echo off
REM ============================================================
REM  Sistema MDS - doble click para arrancar
REM  Levanta el motor RAG local y abre el navegador.
REM ============================================================
title Sistema MDS
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1"
echo.
pause
