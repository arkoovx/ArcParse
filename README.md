# arqParse

Утилита для скачивания и тестирования VPN конфигов. Отбирает лучшие конфиги по пингу.

### 🚀 Быстрый запуск

**Графический интерфейс (рекомендуется для начинающих):**
```bash
python main.py --gui
```

Или используйте удобные скрипты:
- **Linux/Mac**: `./run_gui.sh`
- **Windows**: `run_gui.bat`

[📖 Подробная документация по GUI](GUI.md)

---

## 📥 Готовые конфиги

Вы можете использовать протестированные конфиги прямо сейчас. Добавьте нужную подписку в ваш VPN клиент:

| Файл | Описание |
|------|---------|
| [all_top_vpn.txt](https://raw.githubusercontent.com/arkoovx/arqParse/refs/heads/main/results/all_top_vpn.txt) | Все рабочие VPN конфиги (объединённые) |
| [top_vpn.txt](https://raw.githubusercontent.com/arkoovx/arqParse/refs/heads/main/results/top_vpn.txt) | Лучшие VPN конфиги |
| [top_bypass.txt](https://raw.githubusercontent.com/arkoovx/arqParse/refs/heads/main/results/top_bypass.txt) | Лучшие обходные конфиги |
| [top_MTProto.txt](https://raw.githubusercontent.com/arkoovx/arqParse/refs/heads/main/results/top_MTProto.txt) | Лучшие Telegram прокси |

### Как использовать

1. **Скопируйте ссылку** из таблицы выше (raw.githubusercontent.com URL)
2. **Откройте ваш VPN клиент** (например: Happ, Clash, v2rayTun, NekoBox)
3. **Добавьте подписку** (Import from URL / Add subscription / Subscribe)
4. **Вставьте скопированную ссылку**

Все это - конфиги, проверенные на мобильном интернете. Блокировки везде разные, поэтому подходит далеко не всем- ведётся работа над более гибким решением.

---

## ⚙️ Обновления результатов

Подписка будет получать свежие рабочие конфиги.

---

## 📚 Для разработчиков

Если вы хотите настроить и запустить arqParse локально, см. **[TECHNICAL.md](TECHNICAL.md)** для полной технической документации.

---

## 🎯 Возможности

- ✅ Скачивание конфигов из разных источников
- ✅ Тестирование Xray (VLESS, VMess, Trojan, Shadowsocks)
- ✅ Тестирование MTProto (Telegram прокси)
- ✅ Сортировка по пингу
- ✅ Автообновление на GitHub
- ✅ Интерфейс

---

## 📄 Лицензия

MIT

---

## 💬 Поддержка

Вопросы? Создайте issue в репозитории или напишите [@arqhub](https://t.me/arqhub) в Telegram.

