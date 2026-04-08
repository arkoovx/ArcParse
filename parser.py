"""Модуль для парсинга VPN ссылок и MTProto прокси."""

import os
import re
from urllib.parse import parse_qs
from typing import Optional, Dict, List


def parse_mtproto_url(url: str) -> Optional[Dict]:
    """
    Парсит MTProto прокси URL (https://t.me/proxy?server=...&port=...&secret=...).
    """
    try:
        if 't.me/proxy' not in url and 'tg://proxy' not in url:
            return None
        
        # Извлекаем query параметры
        if '?' not in url:
            return None
        
        query = url.split('?', 1)[1]
        params = parse_qs(query)
        
        # Проверяем обязательные параметры
        if not all(k in params for k in ['server', 'port', 'secret']):
            return None
        
        server = params['server'][0]
        port = int(params['port'][0])
        secret = params['secret'][0]
        
        # Валидация
        if port < 1 or port > 65535:
            return None
        
        return {
            'server': server,
            'port': port,
            'secret': secret,
            'url': url
        }
    except Exception:
        return None


def read_configs_from_file(filepath: str) -> List[str]:
    """
    Читает конфиги из файла, пропускает пустые строки и комментарии.
    Возвращает список строк с конфигами.
    Корректно обрабатывает \r\n (Windows) и \n (Unix) окончания строк.
    Разделяет склеенные конфиги (когда несколько URL соединены без переноса).
    """
    configs = []

    if not os.path.exists(filepath):
        return configs

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Нормализуем окончания строк (Windows \r\n -> Unix \n)
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # Очищаем контент от HTML-сущностей и склеиваем разорванные строки
    content = content.replace('&amp;', '&')
    content = content.replace('&lt;', '<')
    content = content.replace('&gt;', '>')
    content = content.replace('&quot;', '"')
    content = content.replace('&#39;', "'")

    # Склеиваем разорванные строки и разделяем склеенные конфиги
    lines = content.split('\n')
    cleaned_lines = []
    current_line = ''

    # Важно: hysteria2 должен идти перед hysteria, ssr перед ss, чтобы избежать частичного совпадения
    config_start_pattern = re.compile(r'(vless|vmess|trojan|ssr|ss|hysteria2|hy2|hysteria|tuic)://')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Проверяем, содержит ли строка начало нового конфига
        # Если да - разделяем на несколько строк
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

    # Фильтруем конфиги
    for line in cleaned_lines:
        line = line.strip()
        # Пропускаем пустые строки, комментарии и заголовки
        if not line or line.startswith('#') or line.startswith('profile-'):
            continue
        configs.append(line)

    return configs


def read_mtproto_from_file(filepath: str) -> List[str]:
    """
    Читает MTProto прокси из файла.
    Возвращает список URL.
    Корректно обрабатывает \r\n (Windows) и \n (Unix) окончания строк.
    Разделяет склеенные прокси (когда несколько URL соединены без переноса).
    """
    proxies = []

    if not os.path.exists(filepath):
        return proxies

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Нормализуем окончания строк (Windows \r\n -> Unix \n)
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # Очищаем контент
    content = content.replace('&amp;', '&')

    # Разделяем склеенные прокси и склеиваем разорванные строки
    lines = content.split('\n')
    cleaned_lines = []
    current_line = ''

    # Паттерн для обнаружения начала MTProto URL
    mtproto_start_pattern = re.compile(r'(https://t\.me/proxy|tg://proxy)')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Проверяем, содержит ли строка начало нового MTProto URL
        matches = list(mtproto_start_pattern.finditer(stripped))
        
        if len(matches) > 1:
            # Если есть накопленная строка - сохраняем
            if current_line:
                cleaned_lines.append(current_line)
                current_line = ''
            
            # Разделяем склеенные прокси
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
                # Строка начинается с прокси
                if current_line:
                    cleaned_lines.append(current_line)
                current_line = stripped
            else:
                # Прокси в середине строки - это продолжение + новый прокси
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

    content = '\n'.join(cleaned_lines)

    # Находим все MTProto ссылки
    pattern = r'(https://t\.me/proxy\?[^\s]+|tg://proxy[^\s]+)'
    matches = re.findall(pattern, content)

    for match in matches:
        line = match.strip()
        if line and ('t.me/proxy' in line or 'tg://proxy' in line):
            # Проверяем что есть обязательные параметры
            if 'server=' in line and 'port=' in line:
                proxies.append(line)

    return proxies
