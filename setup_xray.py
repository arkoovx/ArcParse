"""
Автоопределение ОС/архитектуры и установка правильного Xray бинарника.

При запуске проверяет:
  1. Текущую ОС (Windows/Linux/macOS) и архитектуру (amd64/arm64)
  2. Есть ли уже правильный бинарник
  3. Если нет — скачивает актуальный релиз с GitHub Xray-core
"""

import os
import sys
import platform
import zipfile
import shutil
import tempfile
import urllib.request
import json

from config import BIN_DIR

# Последний релиз Xray-core
XRAY_RELEASE_API = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"

# Маппинг платформы -> имя файла в релизе
# Формат: (sys_platform, machine) -> xray_filename_in_release
PLATFORM_MAP = {
    ("win32", "AMD64"): "Xray-windows-64.zip",
    ("win32", "ARM64"): "Xray-windows-arm64-v8a.zip",
    ("linux", "x86_64"): "Xray-linux-64.zip",
    ("linux", "aarch64"): "Xray-linux-arm64-v8a.zip",
    ("linux", "armv7l"): "Xray-linux-arm32-v7a.zip",
    ("darwin", "x86_64"): "Xray-macos-64.zip",
    ("darwin", "arm64"): "Xray-macos-arm64-v8a.zip",
}


def get_platform_info() -> tuple:
    """Возвращает (sys_platform, machine) кортеж."""
    return (sys.platform, platform.machine())


def get_xray_filename() -> str:
    """Возвращает имя бинарника для текущей платформы."""
    plat = get_platform_info()
    if plat in PLATFORM_MAP:
        return PLATFORM_MAP[plat]
    raise RuntimeError(f"Неподдерживаемая платформа: {plat[0]} / {plat[1]}")


def get_expected_binary_name() -> str:
    """Возвращает ожидаемое имя бинарника Xray для текущей ОС."""
    return "xray.exe" if sys.platform == "win32" else "xray"


def is_binary_valid(binary_path: str) -> bool:
    """
    Проверяет, что бинарник Xray является рабочим исполняемым файлом
    для текущей платформы.
    """
    if not os.path.exists(binary_path):
        return False

    try:
        # На Windows пробуем запустить с --version
        if sys.platform == "win32":
            import subprocess
            result = subprocess.run(
                [binary_path, "--version"],
                capture_output=True,
                timeout=5
            )
            # Если вернулся 0 и в выводе есть "Xray" — всё ок
            if result.returncode == 0 and b"Xray" in result.stdout:
                return True
            return False
        else:
            # На Linux/macOS проверяем execute bit и file header
            if not os.access(binary_path, os.X_OK):
                return False
            import subprocess
            result = subprocess.run(
                [binary_path, "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0 and b"Xray" in result.stdout:
                return True
            return False
    except Exception:
        return False


def download_xray_binary(log_func=None) -> bool:
    """
    Скачивает и устанавливает правильный Xray бинарник для текущей платформы.
    Возвращает True при успехе.
    """
    def _log(msg, tag="info"):
        if log_func:
            log_func(msg, tag)
        else:
            print(msg)

    try:
        platform_name = get_xray_filename()
        expected_binary = get_expected_binary_name()
        _log(f"Платформа: {sys.platform} / {platform.machine()}, нужен: {platform_name}", "info")

        # Скачиваем ZIP с GitHub
        _log("Загрузка Xray-core с GitHub...", "info")

        # Сначала получаем информацию о последнем релизе
        req = urllib.request.Request(
            XRAY_RELEASE_API,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "arqParse"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            release_info = json.loads(resp.read().decode("utf-8"))

        # Ищем нужный ассет
        asset_url = None
        for asset in release_info.get("assets", []):
            if asset["name"] == platform_name:
                asset_url = asset["browser_download_url"]
                break

        if not asset_url:
            _log(f"Не найден ассет {platform_name} в релизе {release_info.get('tag_name', 'latest')}", "error")
            _log("Доступные ассеты:", "error")
            for asset in release_info.get("assets", [])[:10]:
                _log(f"  - {asset['name']}", "error")
            return False

        _log(f"Скачивание: {platform_name}...", "info")
        req = urllib.request.Request(
            asset_url,
            headers={"User-Agent": "arqParse"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            zip_data = resp.read()

        # Распаковываем во временную директорию
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "xray.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_data)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)

            # Ищем бинарник xray/xray.exe в распакованном
            src_binary = None
            for root, dirs, files in os.walk(tmpdir):
                if expected_binary in files:
                    src_binary = os.path.join(root, expected_binary)
                    break

            if not src_binary:
                _log(f"Не найден {expected_binary} в архиве!", "error")
                return False

            # Копируем в bin директорию
            os.makedirs(BIN_DIR, exist_ok=True)
            dst_binary = os.path.join(BIN_DIR, expected_binary)

            shutil.copy2(src_binary, dst_binary)

            # Удаляем старые/неправильные бинарники
            for old_name in ["xray", "xray.exe"]:
                old_path = os.path.join(BIN_DIR, old_name)
                if old_path != dst_binary and os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass

            # На Linux/macOS делаем исполняемым
            if sys.platform != "win32":
                os.chmod(dst_binary, 0o755)

            # Проверяем что работает
            if is_binary_valid(dst_binary):
                _log(f"✓ Xray-core установлен: {dst_binary}", "success")
                return True
            else:
                _log("✗ Установленный бинарник не прошёл проверку", "error")
                return False

    except Exception as e:
        _log(f"✗ Ошибка установки Xray: {e}", "error")
        return False


def ensure_xray(log_func=None) -> str:
    """
    Гарантирует наличие рабочего Xray бинарника.
    Возвращает путь к бинарнику или пустую строку при ошибке.
    """
    def _log(msg, tag="info"):
        if log_func:
            log_func(msg, tag)
        else:
            print(msg)

    from config import XRAY_BIN
    expected_binary = get_expected_binary_name()

    # Проверяем текущий бинарник
    if is_binary_valid(XRAY_BIN):
        _log(f"Xray готов: {XRAY_BIN}", "success")
        return XRAY_BIN

    # Проверяем, может есть другой бинарник с правильным именем
    alt_binary = os.path.join(BIN_DIR, expected_binary)
    if alt_binary != XRAY_BIN and is_binary_valid(alt_binary):
        _log(f"Xray готов: {alt_binary}", "success")
        return alt_binary

    # Текущий бинарник невалиден — скачаем новый
    _log("Xray бинарник отсутствует или не подходит для этой ОС", "warning")
    _log("Скачивание актуальной версии...", "info")

    if download_xray_binary(log_func):
        # Ещё раз проверяем
        if is_binary_valid(XRAY_BIN):
            return XRAY_BIN
        alt_binary = os.path.join(BIN_DIR, expected_binary)
        if is_binary_valid(alt_binary):
            return alt_binary

    _log("Не удалось установить Xray. Тестирование Xray конфигов будет недоступно.", "error")
    return ""
