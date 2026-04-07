"""
Современный GUI для arqParse.
Чёрная тема, фиолетовые акценты.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys
import subprocess
import webbrowser
from datetime import datetime

from config import TASKS, RESULTS_DIR
from downloader import download_all_tasks
from parser import read_configs_from_file, read_mtproto_from_file
from testers import test_xray_configs
from testers_mtproto import test_mtproto_configs, test_mtproto_configs_and_save
import auth as auth_module


# ─── Чёрная тема + фиолетовые акценты ────────────────────────
BG         = "#0d0d0d"
BG_CARD    = "#161616"
BG_HOVER   = "#1e1e1e"
BG_INPUT   = "#111111"
ACCENT     = "#8b5cf6"
ACCENT_DK  = "#7c3aed"
ACCENT_LG  = "#a78bfa"
TEXT       = "#e4e4e7"
TEXT_DIM   = "#71717a"
TEXT_MUTED = "#52525b"
GREEN      = "#22c55e"
YELLOW     = "#facc15"
RED        = "#ef4444"
PROGRESS_T = "#1a1a1a"
PROGRESS_F = "#8b5cf6"
BORDER     = "#262626"


class _Btn(tk.Frame):
    """Кастомная кнопка без артефактов ttk."""
    def __init__(self, master, text="", bg_color=BG_CARD, fg_color=TEXT,
                 font=("Segoe UI", 11), active_bg=BG_HOVER, border=False,
                 command=None, bold=False, pady=8, padx=14, **kw):
        bd = 0 if not border else 1
        super().__init__(master, bg=bg_color, bd=bd, highlightthickness=0, **kw)
        self._bg = bg_color
        self._active_bg = active_bg
        self._command = command
        self._disabled = False

        self.label = tk.Label(self, text=text, bg=bg_color, fg=fg_color,
                              font=font, cursor="hand2")
        if bold:
            self.label.config(font=(font[0], font[1], "bold"))
        self.label.pack(fill=tk.BOTH, expand=True, padx=padx, pady=pady)

        self.bind("<Button-1>", self._click)
        self.label.bind("<Button-1>", self._click)
        self.bind("<Enter>", self._enter)
        self.label.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.label.bind("<Leave>", self._leave)

    def _click(self, e):
        if not self._disabled and self._command:
            self._command()

    def _enter(self, e):
        if not self._disabled:
            self.config(bg=self._active_bg)
            self.label.config(bg=self._active_bg)

    def _leave(self, e):
        if not self._disabled:
            self.config(bg=self._bg)
            self.label.config(bg=self._bg)

    def config(self, **kw):
        if "state" in kw:
            st = kw.pop("state")
            self._disabled = (st == tk.DISABLED)
            if self._disabled:
                self.label.config(fg=TEXT_MUTED, cursor="")
            else:
                self.label.config(cursor="hand2")
        super().config(**kw)
        if "bg" in kw:
            self._bg = kw["bg"]


class ArcParseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("arqParse")
        self.root.geometry("420x800")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # ─── Флаги ─────────────────────────────────────────────
        self.is_running = False
        self.stop_flag = False
        self.skip_flag = False
        self.stop_event = None
        self.skip_event = None

        # ─── Проверяем сессию ──────────────────────────────────
        if auth_module.is_logged_in():
            self._show_main_app()
        else:
            self._show_login_screen()

    # ════════════════════════ ЭКРАН ВХОДА ══════════════════════
    def _show_login_screen(self):
        self.login_frame = tk.Frame(self.root, bg=BG)
        self.login_frame.pack(fill=tk.BOTH, expand=True)

        # Центрируем контент
        center = tk.Frame(self.login_frame, bg=BG)
        center.pack(fill=tk.BOTH, expand=True, padx=32, pady=50)

        # Логотип
        tk.Label(center, text="arqParse", bg=BG, fg=TEXT,
                 font=("Segoe UI", 28, "bold")).pack(pady=(0, 2))
        tk.Label(center, text="Тестирование VPN конфигов", bg=BG,
                 fg=TEXT_DIM, font=("Segoe UI", 11)).pack()

        # Карточка
        card = tk.Frame(center, bg=BG_CARD, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill=tk.X, pady=(36, 0), ipady=4)

        # Режим (переключатель Вход / Регистрация)
        mode_row = tk.Frame(card, bg=BG_CARD)
        mode_row.pack(fill=tk.X, padx=16, pady=(16, 8))

        self.auth_mode = tk.StringVar(value="login")

        tk.Radiobutton(mode_row, text="Вход", variable=self.auth_mode,
                       value="login", bg=BG_CARD, fg=TEXT, selectcolor=BG,
                       font=("Segoe UI", 11), activebackground=BG_CARD,
                       activeforeground=TEXT, highlightthickness=0, border=0,
                       command=self._update_auth_btn_text).pack(side=tk.LEFT, expand=True)
        tk.Radiobutton(mode_row, text="Регистрация", variable=self.auth_mode,
                       value="register", bg=BG_CARD, fg=TEXT, selectcolor=BG,
                       font=("Segoe UI", 11), activebackground=BG_CARD,
                       activeforeground=TEXT, highlightthickness=0, border=0,
                       command=self._update_auth_btn_text).pack(side=tk.LEFT, expand=True)

        # Поля
        fields = tk.Frame(card, bg=BG_CARD)
        fields.pack(fill=tk.X, padx=16)

        self._add_field(fields, "Логин", show=False)
        self._add_field(fields, "Пароль", show=True)

        # Кнопка
        btn_pad = tk.Frame(card, bg=BG_CARD)
        btn_pad.pack(fill=tk.X, padx=16, pady=(14, 16))

        self.auth_btn = _Btn(btn_pad, text="Войти", bg_color=ACCENT, fg_color="#fff",
                             font=("Segoe UI", 12, "bold"), active_bg=ACCENT_DK,
                             command=self._do_auth, pady=10)
        self.auth_btn.pack(fill=tk.X)

        # Enter
        self.login_pass.bind("<Return>", lambda e: self._do_auth())
        self.login_user.bind("<Return>", lambda e: self.login_pass.focus())

        # by arq
        link_row = tk.Frame(center, bg=BG)
        link_row.pack(pady=(20, 0))
        tk.Label(link_row, text="by ", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        al = tk.Label(link_row, text="arq", bg=BG, fg=ACCENT_LG,
                      font=("Segoe UI", 10, "bold"), cursor="hand2")
        al.pack(side=tk.LEFT)
        al.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/arqhub"))

    def _add_field(self, parent, label_text, show=False):
        tk.Label(parent, text=label_text, bg=BG_CARD, fg=TEXT_DIM,
                 font=("Segoe UI", 9), anchor=tk.W).pack(fill=tk.X, pady=(6, 2))
        entry = tk.Entry(parent, bg=BG_INPUT, fg=TEXT, font=("Segoe UI", 11),
                         relief=tk.FLAT, bd=0, highlightthickness=1,
                         highlightbackground=BORDER, insertbackground=TEXT,
                         show="●" if show else "")
        entry.pack(fill=tk.X, ipady=6, pady=(0, 8))
        if show:
            self.login_pass = entry
        else:
            self.login_user = entry

    def _update_auth_btn_text(self):
        """Обновляет текст кнопки при переключении Вход/Регистрация."""
        if not self.auth_btn._disabled:
            if self.auth_mode.get() == "register":
                self.auth_btn.label.config(text="Зарегистрироваться")
            else:
                self.auth_btn.label.config(text="Войти")

    def _do_auth(self):
        username = self.login_user.get().strip()
        password = self.login_pass.get()
        server = auth_module.DEFAULT_SERVER

        if not username or len(username) < 3:
            messagebox.showerror("Ошибка", "Логин минимум 3 символа")
            return
        if not password or len(password) < 6:
            messagebox.showerror("Ошибка", "Пароль минимум 6 символов")
            return

        self.auth_btn._disabled = True
        if self.auth_mode.get() == "register":
            self.auth_btn.label.config(text="Регистрация...", fg=TEXT_DIM)
        else:
            self.auth_btn.label.config(text="Подключение...", fg=TEXT_DIM)
        self.root.update()

        def auth_thread():
            try:
                if self.auth_mode.get() == "register":
                    result = auth_module.register(username, password, server)
                else:
                    result = auth_module.login(username, password, server)
                self.root.after(0, lambda: self._on_auth_success(result))
            except auth_module.AuthError as exc:
                err = str(exc)
                self.root.after(0, lambda: self._show_auth_error(err))
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda: self._show_auth_error(err))

        threading.Thread(target=auth_thread, daemon=True).start()

    def _show_auth_error(self, msg):
        self.auth_btn._disabled = False
        mode = self.auth_mode.get()
        self.auth_btn.label.config(text="Войти" if mode == "login" else "Зарегистрироваться",
                                   fg="#fff")
        messagebox.showerror("Ошибка", msg)

    def _on_auth_success(self, result):
        self.login_frame.destroy()
        self._show_main_app()

    # ════════════════════════ ОСНОВНОЙ ЭКРАН ═══════════════════
    def _show_main_app(self):
        session = auth_module.get_session()
        self.current_user = session["username"] if session else None

        # ─── Верх ──────────────────────────────────────────────
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill=tk.X, padx=24, pady=(16, 8))

        tk.Label(top, text="arqParse", bg=BG, fg=TEXT,
                 font=("Segoe UI", 24, "bold")).pack(anchor=tk.W)

        status_row = tk.Frame(top, bg=BG)
        status_row.pack(fill=tk.X, pady=(4, 0))

        if self.current_user:
            tk.Label(status_row, text=f"👤  {self.current_user}", bg=BG,
                     fg=TEXT_DIM, font=("Segoe UI", 10)).pack(side=tk.LEFT)

            _Btn(status_row, text="📋  Ссылка подписки", bg_color=BG, fg_color=ACCENT_LG,
                 font=("Segoe UI", 9), active_bg=BG_HOVER,
                 command=self._copy_sub_url, padx=6, pady=4).pack(side=tk.RIGHT)

            _Btn(status_row, text="Выйти", bg_color=BG, fg_color=TEXT_DIM,
                 font=("Segoe UI", 9), active_bg=BG_HOVER,
                 command=self._do_logout, padx=6, pady=4).pack(side=tk.RIGHT, padx=(0, 4))

        # MTProto подсказка
        mt_row = tk.Frame(top, bg=BG)
        mt_row.pack(fill=tk.X, pady=(6, 0))
        tk.Label(mt_row, text="MTProto можно добавить в тг через  ", bg=BG,
                 fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(side=tk.LEFT)
        bot_link = tk.Label(mt_row, text="@arqvpn_bot", bg=BG, fg=ACCENT_LG,
                            font=("Segoe UI", 10, "bold"), cursor="hand2")
        bot_link.pack(side=tk.LEFT)
        bot_link.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/arqvpn_bot"))
        bot_link.bind("<Enter>", lambda e: bot_link.config(font=("Segoe UI", 10, "bold underline")))
        bot_link.bind("<Leave>", lambda e: bot_link.config(font=("Segoe UI", 10, "bold")))

        # ─── Главная кнопка ────────────────────────────────────
        self.start_btn = _Btn(self.root, text="⚡  Начать тест", bg_color=ACCENT,
                              fg_color="#fff", font=("Segoe UI", 15, "bold"),
                              active_bg=ACCENT_DK, command=self.start_full_test,
                              pady=14)
        self.start_btn.pack(fill=tk.X, padx=24, pady=(12, 4))

        # ─── Доп. опции ────────────────────────────────────────
        self.advanced_open = False
        self.check_vars = {}

        self.adv_btn = _Btn(self.root, text="▾  Дополнительные настройки",
                            bg_color=BG_CARD, fg_color=TEXT_DIM,
                            font=("Segoe UI", 10), active_bg=BG_HOVER,
                            command=self.toggle_advanced, pady=8)
        self.adv_btn.pack(fill=tk.X, padx=24, pady=(4, 0))

        self.adv_container = tk.Frame(self.root, bg=BG)

        card = tk.Frame(self.adv_container, bg=BG_CARD,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill=tk.X, padx=24, pady=8)

        tk.Label(card, text="Выбрать задачи", bg=BG_CARD, fg=TEXT_DIM,
                 font=("Segoe UI", 10)).pack(anchor=tk.W, padx=14, pady=(10, 4))

        for task in TASKS:
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill=tk.X, padx=14, pady=2)
            var = tk.BooleanVar(value=True)
            self.check_vars[task['name']] = {'var': var, 'task': task}
            cb = tk.Checkbutton(row, text=task['name'], variable=var,
                                bg=BG_CARD, fg=TEXT, selectcolor=BG_INPUT,
                                activebackground=BG_CARD, activeforeground=TEXT,
                                highlightthickness=0, bd=0, font=("Segoe UI", 10))
            cb.pack(side=tk.LEFT)

        acts = tk.Frame(card, bg=BG_CARD)
        acts.pack(fill=tk.X, padx=14, pady=(8, 10))

        _Btn(acts, text="📥  Скачать конфиги", bg_color=BG_INPUT, fg_color=TEXT_DIM,
             font=("Segoe UI", 10), active_bg=BG_HOVER,
             command=self.start_download, pady=6).pack(side=tk.LEFT, fill=tk.X,
                                                       expand=True, padx=(0, 3))
        _Btn(acts, text="📂  Результаты", bg_color=BG_INPUT, fg_color=TEXT_DIM,
             font=("Segoe UI", 10), active_bg=BG_HOVER,
             command=self.open_results, pady=6).pack(side=tk.LEFT, fill=tk.X,
                                                     expand=True, padx=(3, 0))

        # ─── Управление ────────────────────────────────────────
        ctrl = tk.Frame(self.root, bg=BG)
        ctrl.pack(fill=tk.X, padx=24, pady=(4, 0))

        self.skip_btn_w = _Btn(ctrl, text="⏭  Пропустить", bg_color="#1c1917",
                               fg_color=YELLOW, font=("Segoe UI", 10, "bold"),
                               active_bg="#292524", command=self.skip_file,
                               pady=7)
        self.skip_btn_w.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self.skip_btn_w._disabled = True
        self.skip_btn_w.label.config(fg=TEXT_MUTED)

        self.stop_btn_w = _Btn(ctrl, text="⏹  Остановить", bg_color="#1c1917",
                               fg_color=RED, font=("Segoe UI", 10, "bold"),
                               active_bg="#292524", command=self.stop_operation,
                               pady=7)
        self.stop_btn_w.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))
        self.stop_btn_w._disabled = True
        self.stop_btn_w.label.config(fg=TEXT_MUTED)

        # ─── Прогресс ──────────────────────────────────────────
        prog = tk.Frame(self.root, bg=BG)
        prog.pack(fill=tk.X, padx=24, pady=(10, 2))

        self.progress_canvas = tk.Canvas(prog, height=6, bg=PROGRESS_T,
                                         highlightthickness=0, bd=0)
        self.progress_canvas.pack(fill=tk.X)
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, 6, fill=PROGRESS_F, outline="")
        self.progress_label = tk.Label(prog, text="Готов к работе", bg=BG,
                                        fg=TEXT_DIM, font=("Segoe UI", 10))
        self.progress_label.pack(anchor=tk.W, pady=(4, 0))

        # ─── Лог ────────────────────────────────────────────────
        tk.Label(self.root, text="Журнал событий", bg=BG, fg=TEXT_MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=24, pady=(12, 4))

        log_inner = tk.Frame(self.root, bg=BG, padx=24, pady=4)
        log_inner.pack(fill=tk.BOTH, expand=True)

        log_box = tk.Frame(log_inner, bg=BG_CARD, highlightthickness=1,
                           highlightbackground=BORDER)
        log_box.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_box, bg=BG_CARD, fg=TEXT,
                                font=("Segoe UI", 10), wrap=tk.WORD,
                                bd=0, highlightthickness=0, padx=10, pady=8,
                                selectbackground=ACCENT, selectforeground="#fff",
                                state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(log_box, orient=tk.VERTICAL, command=self.log_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=sb.set)

        self.log_text.tag_configure("info", foreground=TEXT_DIM)
        self.log_text.tag_configure("success", foreground=GREEN)
        self.log_text.tag_configure("warning", foreground=YELLOW)
        self.log_text.tag_configure("error", foreground=RED)
        self.log_text.tag_configure("title", foreground=ACCENT_LG,
                                    font=("Segoe UI", 10, "bold"))

        self.log("arqParse запущен", "title")

    # ─── Кастомный прогресс-бар ─────────────────────────────────
    def update_progress(self, current, total, suitable=0, required=0):
        if required > 0:
            pct = min(suitable / required, 1.0)
            self.progress_label.config(text=f"{suitable}/{required} подходящих  ({int(pct*100)}%)")
        elif total > 0:
            pct = current / total
            self.progress_label.config(text=f"{int(pct*100)}%")
        else:
            pct = 0

        w = self.progress_canvas.winfo_width()
        if w <= 1:
            w = 372
        self.progress_canvas.coords(self.progress_bar, 0, 0, int(w * pct), 6)
        self.root.update()

    def _do_logout(self):
        if messagebox.askyesno("Выход", "Выйти из аккаунта?", parent=self.root):
            auth_module.clear_session()
            self.root.destroy()
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def _copy_sub_url(self):
        try:
            url = auth_module.get_sub_url()
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.log("Ссылка подписки скопирована", "success")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self.root)

    def toggle_advanced(self):
        self.advanced_open = not self.advanced_open
        if self.advanced_open:
            self.adv_container.pack(fill=tk.X, after=self.adv_btn)
            self.adv_btn.label.config(text="▴  Скрыть настройки")
        else:
            self.adv_container.pack_forget()
            self.adv_btn.label.config(text="▾  Дополнительные настройки")

    # ─── Лог ────────────────────────────────────────────────────
    def log(self, message, tag="info"):
        skip = ("Тестирование ", "Тестирую ")
        if any(message.startswith(p) for p in skip):
            return
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()

    def _enable_control_buttons(self, running):
        if running:
            self.stop_btn_w._disabled = False
            self.stop_btn_w.label.config(fg=RED)
            self.skip_btn_w._disabled = False
            self.skip_btn_w.label.config(fg=YELLOW)
            self.start_btn._disabled = True
            self.start_btn.label.config(fg=TEXT_DIM)
        else:
            self.stop_btn_w._disabled = True
            self.stop_btn_w.label.config(fg=TEXT_MUTED)
            self.skip_btn_w._disabled = True
            self.skip_btn_w.label.config(fg=TEXT_MUTED)
            self.start_btn._disabled = False
            self.start_btn.label.config(fg="#fff")

    # ─── Скачивание ─────────────────────────────────────────────
    def start_download(self):
        if self.is_running:
            messagebox.showwarning("Внимание", "Операция уже выполняется", parent=self.root)
            return
        self.is_running = True
        self.stop_flag = False
        self.skip_flag = False
        self._enable_control_buttons(True)
        self.progress_label.config(text="Скачивание...")
        self._set_progress(0)
        threading.Thread(target=self._download_thread, daemon=True).start()

    def _set_progress(self, pct):
        w = self.progress_canvas.winfo_width()
        if w <= 1:
            w = 372
        self.progress_canvas.coords(self.progress_bar, 0, 0, int(w * pct / 100), 6)

    def _download_thread(self):
        try:
            self.log("Скачивание конфигов...", "title")
            results = download_all_tasks(TASKS, max_age_hours=24, force=False, log_func=self.log)
            d = len(results.get('downloaded', []))
            s = len(results.get('skipped', []))
            f = len(results.get('failed', []))
            if d:
                self.log(f"Скачано: {d}", "success")
            if s:
                self.log(f"Пропущено (актуальны): {s}", "info")
            if f:
                self.log(f"Ошибок: {f}", "error")
            self.progress_label.config(text="Скачивание завершено" if d or s else "Файлы не найдены")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")
        finally:
            self.is_running = False
            self._enable_control_buttons(False)
            self._set_progress(0)
            self.progress_label.config(text="Готово")

    # ─── Полный тест ────────────────────────────────────────────
    def start_full_test(self):
        if self.is_running:
            messagebox.showwarning("Внимание", "Тест уже запущен", parent=self.root)
            return
        sel = [d['task'] for d in self.check_vars.values() if d['var'].get()]
        if not sel:
            messagebox.showwarning("Внимание", "Не выбрано ни одной задачи", parent=self.root)
            return
        self.is_running = True
        self.stop_flag = False
        self.skip_flag = False
        self._enable_control_buttons(True)
        self.progress_label.config(text="Начинаю тестирование...")
        self._set_progress(0)
        threading.Thread(target=self._full_test_thread, args=(sel,), daemon=True).start()

    def _full_test_thread(self, tasks):
        try:
            self.log("Начинаю тестирование", "title")
            user_stopped = False
            for i, task in enumerate(tasks):
                if self.stop_flag:
                    self.log("Тестирование остановлено", "warning")
                    user_stopped = True
                    break
                self.skip_flag = False
                self.stop_event = threading.Event()
                self.skip_event = threading.Event()
                self.log(f"▶  {task['name']}", "title")
                self._test_task(task)
                ws = self.skip_flag
                ws2 = self.stop_flag
                if ws and not ws2:
                    self.log(f"Пропущено: {task['name']}", "warning")
                    self.skip_flag = False
                if ws2:
                    self.log("Тестирование остановлено", "warning")
                    user_stopped = True
                    break
                pct = int((i + 1) / len(tasks) * 100)
                self.update_progress(pct, 100)

            if not user_stopped:
                self.log("Все тесты завершены ✓", "success")
                self.merge_vpn_configs()
                self._ask_update_sub_or_open_folder()
            else:
                self.progress_label.config(text="Остановлено")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")
        finally:
            self.is_running = False
            self._enable_control_buttons(False)
            self._set_progress(0)
            self.progress_label.config(text="Готово")

    # ─── Подписка на сервер ─────────────────────────────────────
    def _upload_subscription(self):
        if not auth_module.is_logged_in():
            return

        # VPN подписка — только all_top_vpn.txt (Обход + Обычные)
        vpn_file = os.path.join(RESULTS_DIR, "all_top_vpn.txt")
        vpn_content = ""
        if os.path.exists(vpn_file):
            with open(vpn_file, 'r', encoding='utf-8') as f:
                vpn_content = f.read().strip()

        # MTProto подписка — отдельно
        mt_file = os.path.join(RESULTS_DIR, "top_MTProto.txt")
        mt_content = ""
        if os.path.exists(mt_file):
            with open(mt_file, 'r', encoding='utf-8') as f:
                mt_content = f.read().strip()

        if not vpn_content and not mt_content:
            self.log("Нет результатов для отправки", "info")
            return

        def up():
            try:
                # Отправляем VPN
                if vpn_content:
                    self.log("Отправка VPN подписки...", "info")
                    auth_module.update_subscription(vpn_content)
                    self.root.after(0, lambda: self.log("VPN подписка обновлена ✓", "success"))

                # Отправляем MTProto
                if mt_content:
                    self.log("Отправка MTProto подписки...", "info")
                    auth_module.update_mtproto(mt_content)
                    self.root.after(0, lambda: self.log("MTProto подписка обновлена ✓", "success"))

            except auth_module.AuthError as e:
                self.root.after(0, lambda: self.log(f"Ошибка авторизации: {e}", "error"))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Ошибка отправки: {e}", "error"))

        threading.Thread(target=up, daemon=True).start()

    # ─── Одиночный тест ─────────────────────────────────────────
    def start_single_test(self, task):
        if self.is_running:
            messagebox.showwarning("Внимание", "Тест уже запущен", parent=self.root)
            return
        self.is_running = True
        self.stop_flag = False
        self.skip_flag = False
        self._enable_control_buttons(True)
        self.progress_label.config(text=f"Тест: {task['name']}")
        self._set_progress(0)

        def tt():
            try:
                self.log(f"▶  {task['name']}", "title")
                self._test_task(task)
                self.log(f"✓  {task['name']} завершён", "success")
                self._ask_update_sub_or_open_folder()
            except Exception as e:
                self.log(f"Ошибка: {e}", "error")
            finally:
                self.is_running = False
                self._enable_control_buttons(False)
                self._set_progress(0)
                self.progress_label.config(text="Готово")
        threading.Thread(target=tt, daemon=True).start()

    # ─── Тест задачи ────────────────────────────────────────────
    def _test_task(self, task):
        self.log("Чтение конфигов...", "info")
        if self.stop_event is None:
            self.stop_event = threading.Event()
        if self.skip_event is None:
            self.skip_event = threading.Event()

        if task['type'] == 'xray':
            configs = []
            for rf in task['raw_files']:
                if os.path.exists(rf):
                    configs.extend(read_configs_from_file(rf))
            if not configs:
                self.log("Конфиги не найдены", "warning")
                return
            self.log(f"Найдено конфигов: {len(configs)}", "info")
            _, passed, _ = test_xray_configs(
                configs=configs, target_url=task['target_url'],
                max_ping_ms=task['max_ping_ms'], required_count=task['required_count'],
                log_func=self.log, progress_func=self._progress_callback,
                out_file=task['out_file'], profile_title=task['profile_title'],
                config_type=task['name'], stop_flag=self.stop_event, skip_flag=self.skip_event,
            )
            self.log(f"Результат: ✓ {passed} рабочих", "success")

        elif task['type'] == 'mtproto':
            configs = read_mtproto_from_file(task['raw_files'][0]) if os.path.exists(task['raw_files'][0]) else []
            if not configs:
                self.log("MTProto конфиги не найдены", "warning")
                return
            self.log(f"Найдено MTProto: {len(configs)}", "info")
            _, passed, _ = test_mtproto_configs_and_save(
                configs=configs, max_ping_ms=task['max_ping_ms'],
                required_count=task['required_count'], out_file=task['out_file'],
                profile_title=task['profile_title'], log_func=self.log,
                progress_func=self._progress_callback,
                stop_flag=self.stop_event, skip_flag=self.skip_event,
            )
            self.log(f"Результат MTProto: ✓ {passed} рабочих", "success")

        self.stop_event = None
        self.skip_event = None

    def _progress_callback(self, current, total, suitable=0, required=0):
        self.update_progress(current, total, suitable, required)

    def skip_file(self):
        self.skip_flag = True
        if self.skip_event:
            self.skip_event.set()
        self.log("Пропуск текущего файла...", "warning")

    def stop_operation(self):
        self.stop_flag = True
        if self.stop_event:
            self.stop_event.set()
        self.log("Остановка тестирования...", "warning")

    def open_results(self):
        try:
            if sys.platform == "win32":
                os.startfile(RESULTS_DIR)
            elif sys.platform == "darwin":
                os.system(f"open {RESULTS_DIR}")
            else:
                os.system(f"xdg-open {RESULTS_DIR}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self.root)

    def _get_affected_files(self, task):
        out = task.get('out_file')
        if not out:
            return []
        affected = [out]
        if task.get('name', '') in ('Base VPN', 'Bypass VPN'):
            af = os.path.join(RESULTS_DIR, "all_top_vpn.txt")
            self.merge_vpn_configs()
            if os.path.exists(af):
                affected.append(af)
        return affected

    def merge_vpn_configs(self):
        tv = os.path.join(RESULTS_DIR, "top_vpn.txt")
        tb = os.path.join(RESULTS_DIR, "top_bypass.txt")
        av = os.path.join(RESULTS_DIR, "all_top_vpn.txt")
        try:
            ac = []
            for fp in [tv, tb]:
                if os.path.exists(fp):
                    with open(fp, 'r', encoding='utf-8') as f:
                        for l in f:
                            l = l.strip()
                            if l and not l.startswith('#'):
                                ac.append(l)
            seen, cfgs = set(), []
            for c in ac:
                k = c.split('#')[0].strip()
                if k not in seen:
                    seen.add(k)
                    cfgs.append(c)
            if cfgs:
                os.makedirs(os.path.dirname(os.path.abspath(av)), exist_ok=True)
                with open(av, 'w', encoding='utf-8') as f:
                    f.write("#profile-title: arqVPN Free | Все\n")
                    f.write("#profile-update-interval: 48\n")
                    f.write("#support-url: https://t.me/arqhub\n\n")
                    for c in cfgs:
                        f.write(f"{c}\n")
                self.log(f"Объединено {len(cfgs)} конфигов в all_top_vpn.txt", "success")
        except Exception as e:
            self.log(f"Ошибка объединения: {e}", "error")

    def _ask_update_sub_or_open_folder(self):
        """После теста спрашивает: обновить подписку/GitHub. Если нет — открыть папку."""
        session = auth_module.get_session()
        username = session.get("username") if session else None

        if username == "admin":
            # Админ — обновление в GitHub
            if messagebox.askyesno("GitHub", "Обновить результаты в репозитории GitHub?",
                                    parent=self.root):
                threading.Thread(target=self._push_to_github_thread, daemon=True).start()
            else:
                self.open_results()
            return

        # Обычный пользователь — обновление подписки
        if not auth_module.is_logged_in():
            self.open_results()
            return

        if messagebox.askyesno("Подписка", "Обновить вашу подписку на сервере?", parent=self.root):
            self._upload_subscription()
        else:
            self.open_results()

    def _push_to_github_thread(self):
        try:
            self.log("Обновление репозитория...", "title")
            pd = os.path.dirname(os.path.abspath(__file__))
            rfs = []
            for fn in ["top_vpn.txt", "top_bypass.txt", "top_MTProto.txt", "all_top_vpn.txt"]:
                fp = os.path.join(RESULTS_DIR, fn)
                if os.path.exists(fp):
                    rfs.append(fp)
            if not rfs:
                self.log("Нет файлов", "warning")
                return
            for fp in rfs:
                subprocess.run(["git", "add", fp], check=True, capture_output=True, cwd=pd)
            sr = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                text=True, check=True, cwd=pd)
            if not sr.stdout.strip():
                self.log("Нет изменений", "warning")
                return
            cm = f"Update results - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", cm], check=True, capture_output=True, cwd=pd)
            pr = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=pd)
            if pr.returncode == 0:
                self.log("Обновлено на GitHub ✓", "success")
            else:
                self.log(f"Ошибка push: {pr.stderr.strip()}", "error")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")


def main():
    root = tk.Tk()
    app = ArcParseGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
