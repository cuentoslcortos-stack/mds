@echo off
REM ============================================================
REM  Sistema MDS - acceso desde el celu (misma wifi)
REM  Levanta el motor RAG en 0.0.0.0 e imprime la URL de red.
REM ============================================================
title Sistema MDS - Red local
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" -Red
echo.
pause
