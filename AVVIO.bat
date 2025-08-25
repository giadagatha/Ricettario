@echo off
title Avvio del Ricettario
echo ================================
echo     AVVIO DEL RICETTARIO
echo ================================

REM Verifica che Python sia disponibile
where python >nul 2>nul
IF ERRORLEVEL 1 (
    echo Errore: Python non trovato nel PATH.
    pause
    exit /b
)

REM Verifica che l'ambiente virtuale esista
IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo Errore: ambiente virtuale non trovato.
    echo Crealo con: python -m venv .venv
    pause
    exit /b
)

REM Attiva l'ambiente virtuale
call ".venv\Scripts\activate.bat"

REM Verifica che Streamlit sia installato
python -m streamlit --version >nul 2>nul
IF ERRORLEVEL 1 (
    echo Streamlit non è installato. Lo installo ora...
    pip install streamlit
)

REM Avvia l'app Streamlit
echo Avvio dell'app Streamlit...
python -m streamlit run app.py

REM Controllo errori
IF %ERRORLEVEL% NEQ 0 (
    echo Si è verificato un errore durante l'esecuzione di Streamlit.
)

start "" /min python -m streamlit run app.py
exit
