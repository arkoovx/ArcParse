"""Тесты для xray_tester_simple.py."""

import os
import sys

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from xray_tester_simple import _create_xray_config


def test_create_xray_config_for_trojan_ws():
    """Проверяет, что trojan URL с query-параметрами корректно парсится."""
    url = (
        "trojan://password@example.com:443"
        "?type=ws&security=tls&path=%2Fws&host=cdn.example.com&sni=example.com"
    )
    conf = _create_xray_config(url, socks_port=20001)
    assert conf is not None

    outbound = conf["outbounds"][0]
    assert outbound["protocol"] == "trojan"
    assert outbound["streamSettings"]["network"] == "ws"
    assert outbound["streamSettings"]["wsSettings"]["path"] == "/ws"
    assert outbound["streamSettings"]["wsSettings"]["headers"]["Host"] == "cdn.example.com"
