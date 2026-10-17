@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  Image Upscaler by Jair Lima - Setup
echo ============================================
echo.

REM Instalar dependencias Python
echo [1/3] Instalando dependencias Python...
pip install pillow pyinstaller
if errorlevel 1 (
    echo ERRO: falha ao instalar dependencias.
    pause & exit /b 1
)

REM Baixar Upscayl binary
echo.
echo [2/3] Baixando Upscayl binary (engine de IA)...
set "BIN_URL=https://github.com/upscayl/upscayl-ncnn/releases/download/20251207-174704/upscayl-bin-20251207-174704-windows.zip"
set "BIN_ZIP=%~dp0upscayl-bin.zip"
powershell -Command "Invoke-WebRequest -Uri '%BIN_URL%' -OutFile '%BIN_ZIP%' -UseBasicParsing"
if errorlevel 1 ( echo ERRO ao baixar binary. & pause & exit /b 1 )
powershell -Command "Expand-Archive -Path '%BIN_ZIP%' -DestinationPath '%~dp0_extract_bin' -Force"
for /f "delims=" %%d in ('dir /b /ad "%~dp0_extract_bin"') do copy /y "%~dp0_extract_bin\%%d\upscayl-bin.exe" "%~dp0bin\" >nul
rmdir /s /q "%~dp0_extract_bin" >nul 2>&1
del "%BIN_ZIP%" >nul 2>&1
echo    Binary OK.

REM Baixar modelos
echo.
echo [3/3] Baixando modelos de IA (~130 MB no total)...
set "MBASE=https://raw.githubusercontent.com/upscayl/upscayl/main/resources/models"
set "MDEST=%~dp0models"

for %%M in (ultrasharp-4x remacri-4x upscayl-standard-4x upscayl-lite-4x) do (
    echo    Baixando %%M...
    powershell -Command "Invoke-WebRequest -Uri '%MBASE%/%%M.param' -OutFile '%MDEST%\%%M.param' -UseBasicParsing"
    powershell -Command "Invoke-WebRequest -Uri '%MBASE%/%%M.bin'   -OutFile '%MDEST%\%%M.bin'   -UseBasicParsing"
)

echo.
echo ============================================
echo  Setup concluido!
echo  Execute: python upscaler_gui.py
echo  Ou compile: build.bat
echo ============================================
pause
