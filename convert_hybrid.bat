@echo off
REM ============================================================================
REM convert_hybrid.bat - FoxPro to DevExpress Hybrid Conversion
REM ============================================================================
REM Usage: convert_hybrid.bat <input.frx> <output_folder>
REM 
REM This script:
REM   1. Runs FoxPro to export FRX to JSON
REM   2. Runs Python to convert JSON to REPX
REM ============================================================================

setlocal enabledelayedexpansion

REM Configuration - UPDATE THESE PATHS IF NEEDED
SET VFP_PATH="C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe"
SET PYTHON_PATH=.venv\Scripts\python.exe

REM Check arguments
if "%~1"=="" (
    echo Usage: convert_hybrid.bat ^<input.frx^> ^<output_folder^>
    echo.
    echo Example: convert_hybrid.bat FoxPro_Ebill.frx output\FoxPro_Ebill
    exit /b 1
)

SET FRX_FILE=%~1
SET OUTPUT_FOLDER=%~2

if "%OUTPUT_FOLDER%"=="" (
    SET OUTPUT_FOLDER=output\%~n1
)

REM Create temp folder
if not exist "temp" mkdir temp

REM Get base name for JSON file
for %%F in ("%FRX_FILE%") do set BASENAME=%%~nF
SET JSON_FILE=temp\%BASENAME%.json

echo ============================================================================
echo FoxPro to DevExpress Hybrid Converter
echo ============================================================================
echo.
echo Input:  %FRX_FILE%
echo JSON:   %JSON_FILE%
echo Output: %OUTPUT_FOLDER%
echo.

REM Step 1: Check if VFP9 is available
where %VFP_PATH% >nul 2>&1
if errorlevel 1 (
    echo ERROR: Visual FoxPro 9 ^(vfp9.exe^) not found in PATH
    echo.
    echo Please either:
    echo   1. Install VFP9 and add to PATH
    echo   2. Update VFP_PATH in this script
    echo   3. Use the Python-only converter: python src\converter_pdf_layout_v2.py
    exit /b 1
)

REM Step 2: Run FoxPro export
echo [Step 1/2] Exporting FRX to JSON using FoxPro...
echo Command: %VFP_PATH% foxpro\export_frt_to_json.prg "%FRX_FILE%" "%JSON_FILE%"
echo.

%VFP_PATH% -c foxpro\config.fpw foxpro\export_frt_to_json.prg "%FRX_FILE%" "%JSON_FILE%"

if errorlevel 1 (
    echo ERROR: FoxPro export failed
    exit /b 1
)

if not exist "%JSON_FILE%" (
    echo ERROR: JSON file was not created
    exit /b 1
)

echo.
echo JSON export complete: %JSON_FILE%
echo.

REM Step 3: Run Python converter
echo [Step 2/2] Converting JSON to REPX using Python...
echo.

if not exist "%PYTHON_PATH%" (
    SET PYTHON_PATH=python
)

%PYTHON_PATH% src\converter_frx_v3.py "%JSON_FILE%" "%OUTPUT_FOLDER%"

if errorlevel 1 (
    echo ERROR: Python conversion failed
    exit /b 1
)

echo.
echo ============================================================================
echo Conversion complete!
echo ============================================================================
echo Output folder: %OUTPUT_FOLDER%
echo.

REM List generated files
dir /b "%OUTPUT_FOLDER%\*.*" 2>nul

endlocal
