#!/bin/bash
# Скрипт установки arqSubServer
# Запускать на сервере от root

set -e

SERVER_DIR="/root/arqsubserver"
SERVICE_FILE="/etc/systemd/system/arqsubserver.service"

echo "=== Установка arqSubServer ==="

# 1. Создаём директории
echo "[1/5] Создание директорий..."
mkdir -p "$SERVER_DIR/data"
mkdir -p "$SERVER_DIR/logs"

# 2. Устанавливаем зависимости через venv
echo "[2/5] Создание виртуального окружения..."
python3 -m venv "$SERVER_DIR/venv"
source "$SERVER_DIR/venv/bin/activate"
pip install -r "$SERVER_DIR/requirements.txt"

# 3. Копируем systemd юнит
echo "[3/5] Установка systemd сервиса..."
cp "$SERVER_DIR/arqsubserver.service" "$SERVICE_FILE"
systemctl daemon-reload

# 4. Запускаем
echo "[4/5] Запуск сервиса..."
systemctl enable arqsubserver
systemctl restart arqsubserver

# 5. Проверяем
echo "[5/5] Проверка..."
sleep 2

if systemctl is-active --quiet arqsubserver; then
    echo ""
    echo "✓ arqSubServer запущен на https://194.87.54.75:9000"
    echo ""
    echo "Проверка здоровья:"
    curl -sk https://194.87.54.75:9000/health || echo "(curl недоступен, проверьте вручную)"
    echo ""
    echo "Команды управления:"
    echo "  systemctl status arqsubserver  — статус"
    echo "  systemctl restart arqsubserver — перезапуск"
    echo "  journalctl -u arqsubserver -f  — логи"
else
    echo "✗ Ошибка запуска!"
    echo "Смотрите логи: journalctl -u arqsubserver -n 50"
    exit 1
fi
