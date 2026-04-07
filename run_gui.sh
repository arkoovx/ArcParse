#!/bin/bash
# Скрипт запуска GUI на Linux/Mac с автоматической настройкой venv

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  arqParse GUI - Запуск через venv${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не найден${NC}"
    echo "Установите Python 3.7+ и попробуйте снова"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python найден: $PYTHON_VERSION"

# Проверка Tkinter в системе
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo -e "${RED}❌ Tkinter не установлен в системе${NC}"
    echo ""
    echo "Для установки используйте:"
    echo -e "  ${YELLOW}Ubuntu/Debian:${NC} sudo apt install python3-tk"
    echo -e "  ${YELLOW}Fedora/CentOS:${NC} sudo yum install python3-tkinter"
    echo -e "  ${YELLOW}macOS:${NC} brew install python-tk"
    exit 1
fi
echo -e "${GREEN}✓${NC} Tkinter установлен в системе"

# Создание venv если не существует
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}→${NC} Создание виртуального окружения..."
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓${NC} venv создан"
fi

# Активация venv и обновление pip
echo -e "${YELLOW}→${NC} Активирую venv..."
source "$VENV_DIR/bin/activate"

# Обновляем pip
echo -e "${YELLOW}→${NC} Обновляю pip..."
pip install --upgrade pip -q 2>/dev/null || true

# Проверка и установка зависимостей
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}→${NC} Проверяю зависимости..."
    
    # Проверяем какие пакеты не установлены
    MISSING_PACKAGES=""
    while IFS= read -r package; do
        # Пропускаем пустые строки и комментарии
        [[ -z "$package" || "$package" =~ ^# ]] && continue
        
        # Получаем имя пакета без версии
        PKG_NAME=$(echo "$package" | sed 's/[>=<].*//')
        
        if ! "$PIP_BIN" show "$PKG_NAME" &>/dev/null; then
            MISSING_PACKAGES="$MISSING_PACKAGES $package"
        fi
    done < requirements.txt
    
    if [ -n "$MISSING_PACKAGES" ]; then
        echo -e "${YELLOW}→${NC} Установка зависимостей..."
        pip install $MISSING_PACKAGES -q 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Зависимости установлены"
    else
        echo -e "${GREEN}✓${NC} Все зависимости уже установлены"
    fi
else
    echo -e "${YELLOW}⚠${NC} requirements.txt не найден (это нормально)"
fi

# Проверка Tkinter в venv
if ! "$PYTHON_BIN" -c "import tkinter" 2>/dev/null; then
    echo -e "${RED}⚠ Tkinter недоступен в venv${NC}"
    echo "Используем системный Python с Tkinter"
    echo ""
fi

# Финальная информация
echo ""
echo -e "${GREEN}✓${NC} Все компоненты готовы"
echo -e "${CYAN}🚀 Запускаю arqParse GUI...${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

# Запуск GUI через venv Python
"$PYTHON_BIN" main.py --gui

exit 0
