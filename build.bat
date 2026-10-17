@echo off
echo Compilando Image Upscaler by Jair Lima...

pyinstaller ^
  --onefile ^
  --windowed ^
  --add-data "bin;bin" ^
  --add-data "models;models" ^
  --name "ImageUpscaler by Jair Lima" ^
  upscaler_gui.py

if errorlevel 1 (
    echo ERRO na compilacao.
    pause & exit /b 1
)

echo.
echo Copiando para ~/bin...
copy /y "dist\ImageUpscaler by Jair Lima.exe" "%USERPROFILE%\bin\"

echo.
echo Pronto! Executavel disponivel em:
echo   %USERPROFILE%\bin\ImageUpscaler by Jair Lima.exe
pause
