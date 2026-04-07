"""Модуль тестирования MTProto прокси."""

import socket
import time
import os
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from parser import parse_mtproto_url


def _test_single_mtproto(url: str, timeout: float) -> Tuple[bool, float, str]:
    """Тестирует один MTProto прокси через TCP соединение."""
    parsed = parse_mtproto_url(url)
    if not parsed:
        return False, float('inf'), url
    
    server = parsed['server']
    port = parsed['port']
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        start = time.time()
        result = sock.connect_ex((server, port))
        elapsed = (time.time() - start) * 1000
        sock.close()
        
        if result == 0:
            return True, elapsed, url
        else:
            return False, float('inf'), url
            
    except Exception:
        return False, float('inf'), url


def test_mtproto_configs(
    configs: List[str],
    max_ping_ms: float,
    required_count: int,
    max_workers: int = 100,
    log_func: callable = None,
    progress_func: callable = None,
    out_file: str = None,
    profile_title: str = None
) -> Tuple[int, int, int]:
    """
    Асинхронно тестирует список MTProto конфигов.
    Останавливает тестирование когда найдено достаточное количество рабочих конфигов.
    
    Args:
        configs: Список MTProto URL
        max_ping_ms: Максимальный пинг
        required_count: Количество конфигов для поиска
        max_workers: Количество потоков
        log_func: Функция для логирования
        progress_func: Функция для обновления прогресса
        out_file: Файл для сохранения результатов
        profile_title: Название профиля
    
    Returns:
        Для консоли: List[Tuple[str, float]]
        Для GUI: Tuple[working, passed, failed]
    """
    def _log(msg, tag="info"):
        if log_func:
            log_func(msg, tag)
    
    def _progress(current, total):
        if progress_func:
            progress_func(current, total)
    
    results = []
    total = len(configs)
    processed = [0]
    lock = threading.Lock()
    stop_flag = threading.Event()
    
    _log(f"Тестирование {total} MTProto конфигов ({max_workers} потоков)...", "info")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(_test_single_mtproto, cfg, 5.0): cfg for cfg in configs}
        
        for future in as_completed(future_to_url):
            if stop_flag.is_set():
                break
            try:
                success, ping_ms, url = future.result()
                
                with lock:
                    processed[0] += 1
                    _progress(processed[0], total)
                    
                    if success and ping_ms <= max_ping_ms:
                        results.append((url, ping_ms))
                        _log(f"✓ {ping_ms:.0f} мс (найдено: {len(results)}/{required_count})", "success")
                        
                        if len(results) >= required_count:
                            stop_flag.set()
                    else:
                        status = "timeout" if ping_ms == float('inf') else f"{ping_ms:.0f} мс"
                        _log(f"✗ {status}", "warning")
            except Exception as e:
                with lock:
                    processed[0] += 1
                    _log(f"Ошибка: {str(e)}", "error")
        
        if stop_flag.is_set():
            executor.shutdown(wait=False, cancel_futures=True)
    
    # Сортируем по пингу
    results.sort(key=lambda x: x[1])
    
    # Возвращаем результаты в зависимости от контекста
    if out_file is not None:
        # GUI режим - сохраняем и возвращаем статистику
        passed = len(results[:required_count])
        failed = processed[0] - len(results)
        working = len(results)
        
        if results:
            try:
                os.makedirs(os.path.dirname(out_file), exist_ok=True)
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(f"#profile-title: {profile_title or 'arqVPN MTProto'}\n")
                    f.write("#profile-update-interval: 48\n")
                    f.write("#support-url: https://t.me/arqhub\n")
                    f.write("\n")
                    for url, ping_ms in results[:required_count]:
                        f.write(f"{url}\n")
                _log(f"✓ Сохранено {len(results[:required_count])} конфигов", "success")
            except Exception as e:
                _log(f"Ошибка сохранения: {str(e)}", "error")
        
        return working, passed, failed
    else:
        # Консольный режим
        return results
