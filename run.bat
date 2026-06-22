@echo off
echo Starting Auto Subtitler...
echo Activating Anaconda environment...
call C:\ProgramData\anaconda3\Scripts\activate.bat
echo Please wait while the application loads...
echo.

python app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ----------------------------------------------------
    echo The application stopped with an error. 
    echo Please check the output above to diagnose the issue.
    echo ----------------------------------------------------
    pause
)
