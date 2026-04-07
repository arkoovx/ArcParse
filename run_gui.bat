@echo off
REM Скрипт запуска GUI на Windows с автоматической настройкой venv

setlocal enabledelayedexpansion

REM Получение пути скрипта
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

set VENV_DIR=%SCRIPT_DIR%venv
set PYTHON_BIN=%VENV_DIR%\Scripts\python.exe
set PIP_BIN=%VENV_DIR%\Scripts\pip.exe
set ACTIVATE_SCRIPT=%VENV_DIR%\Scripts\activate.bat

REM Заголовок
echo.
echo ════════════════════════════════════════════════════════
echo   arqParse GUI - Запуск через venv
echo ════════════════════════════════════════════════════════
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден
    echo Установите Python 3.7+ и убедитесь что он в PATH
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python найден: %PYTHON_VERSION%

REM Проверка Tkinter в системе
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Tkinter не установлен в системе
    echo При переустановке Python выберите опцию:
    echo   "Install tcl/tk and IDLE"
    echo.
    pause
    exit /b 1
)
echo ✓ Tkinter установлен в системе

REM Создание venv если не существует
if not exist "%VENV_DIR%" (
    echo.
    echo → Создание виртуального окружения...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ❌ Не удалось создать venv
        pause
        exit /b 1
    )
    echo ✓ venv создан
)

REM Активация venv
echo → Активирую venv...
call "%ACTIVATE_SCRIPT%"

REM Обновляем pip
echo → Обновляю pip...
"%PIP_BIN%" install --upgrade pip -q >nul 2>&1

REM Проверка и установка зависимостей
if exist "requirements.txt" (
    echo → Проверяю зависимости...
    
    REM Установка всех зависимостей тихо
    "%PIP_BIN%" install -r requirements.txt -q 2>nul
    if errorlevel 1 (
        echo ✓ Зависимости проверены
    ) else (
        echo ✓ Зависимости установлены
    )
) else (
    echo ⚠ requirements.txt не найден (это нормально)
)

REM Проверка Tkinter в venv
"%PYTHON_BIN%" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo ⚠ Tkinter недоступен в venv
    echo Используем системный Python с Tkinter
)

REM Финальная информация
echo.
echo ✓ Все компоненты готовы
echo 🚀 Запускаю arqParse GUI...
echo ════════════════════════════════════════════════════════
echo.

REM Запуск GUI через venv Python
"%PYTHON_BIN%" main.py --gui

REM Если произошла ошибка, показываем паузу
if errorlevel 1 (
    echo.
    echo ❌ Ошибка при запуске GUI
    pause
)

exit /b 0
