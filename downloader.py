"""Модуль для скачивания конфигов."""

import os
import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import CHROME_UA


def get_file_age_hours(filepath: str) -> float:
    """Возвращает возраст файла в часах."""
    if not os.path.exists(filepath):
        return float('inf')
    
    mtime = os.path.getmtime(filepath)
    age = time.time() - mtime
    return age / 3600  # Конвертируем в часы


def clean_config_content(content: str) -> str:
    """
    Очищает контент конфигов:
    - Заменяет HTML-сущности (&amp; -> &, &lt; -> <, и т.д.)
    - Склеивает разорванные строки конфигов
    - Разделяет склеенные конфиги (когда несколько URL соединены без переноса)
    - Корректно обрабатывает \r\n (Windows) и \n (Unix) окончания строк
    """
    # Нормализуем окончания строк (Windows \r\n -> Unix \n)
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # Заменяем HTML-сущности
    content = content.replace('&amp;', '&')
    content = content.replace('&lt;', '<')
    content = content.replace('&gt;', '>')
    content = content.replace('&quot;', '"')
    content = content.replace('&#39;', "'")

    # Склеиваем разорванные строки и разделяем склеенные конфиги
    lines = content.split('\n')
    cleaned_lines = []
    current_line = ''

    # Важно: hysteria2 должен идти перед hysteria, чтобы избежать частичного совпадения
    config_start_pattern = re.compile(r'(vless|vmess|trojan|ssr|ss|hysteria2|hy2|hysteria|tuic)://')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Проверяем, содержит ли строка начало нового конфига
        matches = list(config_start_pattern.finditer(stripped))
        
        if len(matches) > 1:
            # Если есть накопленная строка - сохраняем
            if current_line:
                cleaned_lines.append(current_line)
                current_line = ''
            
            # Разделяем склеенные конфиги
            for i, match in enumerate(matches):
                start = match.start()
                if i + 1 < len(matches):
                    end = matches[i + 1].start()
                    cleaned_lines.append(stripped[start:end])
                else:
                    # Последний матч - начинаем новую накопленную строку
                    current_line = stripped[start:]
        elif len(matches) == 1:
            match = matches[0]
            if match.start() == 0:
                # Строка начинается с конфига
                if current_line:
                    cleaned_lines.append(current_line)
                current_line = stripped
            else:
                # Конфиг в середине строки - это продолжение + новый конфиг
                current_line += stripped[:match.start()]
                if current_line.strip():
                    cleaned_lines.append(current_line.strip())
                current_line = stripped[match.start():]
        else:
            # Это продолжение предыдущей строки - склеиваем
            current_line += stripped

    # Не забываем последнюю строку
    if current_line:
        cleaned_lines.append(current_line)

    return '\n'.join(cleaned_lines)


def _create_session_with_retries() -> requests.Session:
    """Создает сессию requests с автоматическими повторениями при сбоях."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # 3 попытки
        backoff_factor=1,  # 1s, 2s, 4s задержка между попытками
        status_forcelist=[429, 500, 502, 503, 504],  # Повторять на эти коды
        allowed_methods=["GET", "HEAD"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def download_file(url: str, filepath: str, max_age_hours: int = 24, force: bool = False, log_func=None) -> bool:
    """
    Скачивает файл по URL, если он устарел или не существует.
    """
    def _log(msg, tag="info"):
        if log_func:
            log_func(msg, tag)
        else:
            print(msg)

    # Проверяем возраст файла
    if not force:
        age_hours = get_file_age_hours(filepath)
        if age_hours <= max_age_hours:
            _log(f"⏭ {os.path.basename(filepath)} актуален ({age_hours:.1f} ч)", "info")
            return True

    # Создаем директорию если не существует
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    try:
        _log(f"Скачивание {os.path.basename(filepath)}...", "info")
        # Используем контекстный менеджер, чтобы сокеты корректно закрывались
        # даже в случае исключений/таймаутов.
        with _create_session_with_retries() as session:
            response = session.get(url, timeout=30, headers={"User-Agent": CHROME_UA})
            response.raise_for_status()

        # Очищаем контент
        cleaned_content = clean_config_content(response.text)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)

        _log(f"✓ Скачано {os.path.basename(filepath)} ({len(cleaned_content)} байт)", "success")
        return True

    except requests.exceptions.RequestException as e:
        _log(f"✗ Ошибка скачивания {os.path.basename(filepath)}: {e}", "error")
        return False


def download_all_tasks(tasks: list, max_age_hours: int = 24, force: bool = False, log_func=None) -> dict:
    """
    Скачивает все файлы для задач.
    Поддерживает несколько URL для каждой задачи.

    Returns:
        dict с результатами: {'downloaded': [...], 'skipped': [...], 'failed': [...]}
    """
    results = {'downloaded': [], 'skipped': [], 'failed': []}

    for task in tasks:
        # Поддержка как одного URL, так и списка URL
        urls = task.get('urls', [task.get('url')])
        raw_files = task.get('raw_files', [task.get('raw_file')])
        pair_count = min(len(urls), len(raw_files))

        # Явно предупреждаем о частично описанной задаче:
        # zip(urls, raw_files) молча отбрасывает "лишние" элементы.
        if len(urls) != len(raw_files) and log_func:
            log_func(
                f"⚠ {task.get('name', 'Unknown task')}: mismatch urls/raw_files "
                f"({len(urls)} vs {len(raw_files)}), будет обработано пар: {pair_count}",
                "warning",
            )

        for url, filepath in zip(urls[:pair_count], raw_files[:pair_count]):
            if url and filepath:
                # Проверяем нужно ли скачивать
                if not force:
                    age_hours = get_file_age_hours(filepath)
                    if age_hours <= max_age_hours:
                        results['skipped'].append(f"{task['name']}: {os.path.basename(filepath)}")
                        if log_func:
                            log_func(f"⏭ {task['name']}: {os.path.basename(filepath)} актуален", "info")
                        continue

                success = download_file(
                    url=url,
                    filepath=filepath,
                    max_age_hours=max_age_hours,
                    force=force,
                    log_func=log_func,
                )

                if success:
                    results['downloaded'].append(f"{task['name']}: {os.path.basename(filepath)}")
                else:
                    results['failed'].append(f"{task['name']}: {os.path.basename(filepath)}")

    return results
