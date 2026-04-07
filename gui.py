"""
Минималистичный кроссплатформенный GUI для ArcParse.
Работает на Linux и Windows с использованием Tkinter.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import threading
import os
import sys
import subprocess
from datetime import datetime

from config import TASKS, RESULTS_DIR
from downloader import download_all_tasks
from parser import read_configs_from_file, read_mtproto_from_file
from testers import test_xray_configs
from testers_mtproto import test_mtproto_configs, test_mtproto_configs_and_save
from ui import Colors


class ArcParseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("arqParse - VPN Config Manager")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Установка минимального размера
        self.root.minsize(600, 400)
        
        # Стиль
        style = ttk.Style()
        style.theme_use('clam')
        
        # Конфигурация цветов
        bg_color = "#f0f0f0"
        button_color = "#0078d4"
        success_color = "#107c10"
        warning_color = "#ffb900"
        
        self.root.configure(bg=bg_color)
        
        # Флаги
        self.is_running = False
        self.stop_flag = False
        
        # Главная фрейм
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Заголовок
        header = ttk.Label(
            main_frame,
            text="arqParse - VPN Config Parser & Tester",
            font=("Helvetica", 16, "bold")
        )
        header.grid(row=0, column=0, columnspan=5, pady=10)
        
        # Панель управления
        control_frame = ttk.LabelFrame(main_frame, text="Управление", padding="10")
        control_frame.grid(row=1, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=10)
        control_frame.columnconfigure(1, weight=1)
        
        # Кнопки управления
        ttk.Button(
            control_frame,
            text="📥 Скачать конфиги",
            command=self.start_download
        ).grid(row=0, column=0, padx=5, pady=5)
        
        ttk.Button(
            control_frame,
            text="⚡ Тестировать все",
            command=self.start_full_test
        ).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(
            control_frame,
            text="📂 Открыть результаты",
            command=self.open_results
        ).grid(row=0, column=2, padx=5, pady=5)
        
        self.stop_btn = ttk.Button(
            control_frame,
            text="⏹ Остановить",
            command=self.stop_operation,
            state=tk.DISABLED
        )
        self.stop_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # Кнопка очистки лога
        ttk.Button(
            control_frame,
            text="🗑 Очистить лог",
            command=self.clear_log
        ).grid(row=0, column=4, padx=5, pady=5)
        
        # Панель задач
        tasks_frame = ttk.LabelFrame(main_frame, text="Быстрые действия по задачам", padding="10")
        tasks_frame.grid(row=2, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=10)
        tasks_frame.columnconfigure(1, weight=1)
        
        row = 0
        col = 0
        for i, task in enumerate(TASKS):
            ttk.Button(
                tasks_frame,
                text=f"🧪 Тест: {task['name']}",
                command=lambda t=task: self.start_single_test(t)
            ).grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E))
            
            col += 1
            if col >= 2:
                col = 0
                row += 1
        
        # Окно логов
        log_frame = ttk.LabelFrame(main_frame, text="Логирование", padding="5")
        log_frame.grid(row=3, column=0, columnspan=5, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Скролируемый текст для логов
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            width=100,
            wrap=tk.WORD,
            font=("Courier", 9)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Конфигурация тегов для цветов
        self.log_text.tag_configure("info", foreground="#0078d4")
        self.log_text.tag_configure("success", foreground="#107c10")
        self.log_text.tag_configure("warning", foreground="#ffb900")
        self.log_text.tag_configure("error", foreground="#d13438")
        self.log_text.tag_configure("title", foreground="#106ebe", font=("Courier", 9, "bold"))
        
        # Панель статуса
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=5)
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Статус:").grid(row=0, column=0, padx=5)
        self.status_label = ttk.Label(
            status_frame,
            text="Готово",
            foreground="#107c10"
        )
        self.status_label.grid(row=0, column=1, padx=5, sticky=tk.W)
        
        # Прогресс-бар
        ttk.Label(status_frame, text="Прогресс:").grid(row=1, column=0, padx=5)
        self.progress = ttk.Progressbar(
            status_frame,
            mode='determinate',
            length=300
        )
        self.progress.grid(row=1, column=1, padx=5, sticky=(tk.W, tk.E))
        self.progress_label = ttk.Label(status_frame, text="0%")
        self.progress_label.grid(row=1, column=2, padx=5)
        
        self.log("arqParse GUI запущен", "title")
    
    def log(self, message, tag="info"):
        """Добавляет сообщение в лог."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.root.update()
    
    def clear_log(self):
        """Очищает окно логов."""
        if messagebox.askyesno("Подтверждение", "Очистить лог?"):
            self.log_text.delete(1.0, tk.END)
    
    def set_status(self, status, color="info"):
        """Устанавливает текст статуса."""
        self.status_label.config(text=status)
        if color == "success":
            self.status_label.config(foreground="#107c10")
        elif color == "error":
            self.status_label.config(foreground="#d13438")
        elif color == "warning":
            self.status_label.config(foreground="#ffb900")
        else:
            self.status_label.config(foreground="#0078d4")
    
    def update_progress(self, current, total):
        """Обновляет прогресс-бар."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress['value'] = percent
            self.progress_label.config(text=f"{percent}%")
        self.root.update()
    
    def start_download(self):
        """Запускает скачивание конфигов в отдельном потоке."""
        if self.is_running:
            messagebox.showwarning("Ошибка", "Операция уже выполняется")
            return
        
        self.is_running = True
        self.stop_flag = False
        self.stop_btn.config(state=tk.NORMAL)
        self.set_status("Скачивание конфигов...", "info")
        self.progress['value'] = 0
        
        thread = threading.Thread(target=self._download_thread)
        thread.daemon = True
        thread.start()
    
    def _download_thread(self):
        """Поток для скачивания."""
        try:
            self.log("Начинаю скачивание конфигов...", "title")
            
            results = download_all_tasks(TASKS, max_age_hours=24, force=False)
            
            self.update_progress(50, 100)
            
            # Обработка результатов - правильный формат
            if results.get('failed'):
                for failed in results['failed']:
                    self.log(f"Ошибка скачивания: {failed}", "error")
            
            downloaded_count = len(results.get('downloaded', []))
            skipped_count = len(results.get('skipped', []))
            total_count = downloaded_count + skipped_count
            
            self.log(f"Скачивание завершено: {total_count} файлов", "success")
            
            self.set_status("Скачивание завершено", "success")
            self.update_progress(100, 100)
            messagebox.showinfo("Успех", "Конфиги успешно скачаны")
            
        except Exception as e:
            self.log(f"Ошибка: {str(e)}", "error")
            self.set_status("Ошибка при скачивании", "error")
            messagebox.showerror("Ошибка", f"Ошибка скачивания: {str(e)}")
        finally:
            self.is_running = False
            self.stop_btn.config(state=tk.DISABLED)
            self.update_progress(0, 100)
    
    def start_full_test(self):
        """Запускает полное тестирование."""
        if self.is_running:
            messagebox.showwarning("Ошибка", "Операция уже выполняется")
            return
        
        self.is_running = True
        self.stop_flag = False
        self.stop_btn.config(state=tk.NORMAL)
        self.set_status("Выполняю полное тестирование...", "info")
        self.progress['value'] = 0
        
        thread = threading.Thread(target=self._full_test_thread)
        thread.daemon = True
        thread.start()
    
    def _full_test_thread(self):
        """Поток для полного тестирования."""
        try:
            self.log("Начинаю полное тестирование всех конфигов...", "title")
            
            for i, task in enumerate(TASKS):
                if self.stop_flag:
                    self.log("Тестирование остановлено пользователем", "warning")
                    break
                
                self.log(f"\n📋 Тестирую: {task['name']}", "title")
                self._test_task(task)
                
                progress = int((i + 1) / len(TASKS) * 100)
                self.update_progress(progress, 100)
            
            if not self.stop_flag:
                self.log("\nВсе тесты завершены ✓", "success")
                self.set_status("Тестирование завершено", "success")
                
                # Добавляю логику как в основном main.py
                self.merge_vpn_configs()
                self.ask_push_to_github()
                
                messagebox.showinfo("Успех", "Тестирование завершено успешно")
            
        except Exception as e:
            self.log(f"Ошибка при тестировании: {str(e)}", "error")
            self.set_status("Ошибка при тестировании", "error")
            messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
        finally:
            self.is_running = False
            self.stop_btn.config(state=tk.DISABLED)
    
    def start_single_test(self, task):
        """Запускает тестирование одной задачи."""
        if self.is_running:
            messagebox.showwarning("Ошибка", "Операция уже выполняется")
            return
        
        self.is_running = True
        self.stop_flag = False
        self.stop_btn.config(state=tk.NORMAL)
        self.set_status(f"Тестирую {task['name']}...", "info")
        self.progress['value'] = 0
        
        def test_thread():
            try:
                self.log(f"\n📋 Тестирование: {task['name']}", "title")
                self._test_task(task)
                self.log(f"✓ Тестирование {task['name']} завершено", "success")
                self.set_status(f"Тест '{task['name']}' завершен", "success")
                messagebox.showinfo("Успех", f"Тест '{task['name']}' завершен")
            except Exception as e:
                self.log(f"Ошибка: {str(e)}", "error")
                self.set_status("Ошибка при тестировании", "error")
                messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
            finally:
                self.is_running = False
                self.stop_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=test_thread)
        thread.daemon = True
        thread.start()
    
    def _test_task(self, task):
        """Выполняет тестирование задачи."""
        self.log(f"Читаю конфиги из {len(task['raw_files'])} файлов...", "info")
        
        if task['type'] == 'xray':
            configs = []
            for raw_file in task['raw_files']:
                if os.path.exists(raw_file):
                    configs.extend(read_configs_from_file(raw_file))
            
            if not configs:
                self.log("Конфиги не найдены для тестирования", "warning")
                return
            
            self.log(f"Найдено {len(configs)} конфигов для тестирования", "info")
            
            # Запускаем тестирование - правильный порядок параметров
            working, passed, failed = test_xray_configs(
                configs=configs,
                target_url=task['target_url'],
                max_ping_ms=task['max_ping_ms'],
                required_count=task['required_count'],
                log_func=self.log,
                progress_func=self._progress_callback,
                out_file=task['out_file'],
                profile_title=task['profile_title'],
                config_type=task['name']
            )
            
            self.log(f"Результаты: ✓{passed} | ✗{failed} | 🔄{working}", "success")
        
        elif task['type'] == 'mtproto':
            configs = read_mtproto_from_file(task['raw_files'][0]) if os.path.exists(task['raw_files'][0]) else []
            
            if not configs:
                self.log("MTProto конфиги не найдены", "warning")
                return
            
            self.log(f"Найдено {len(configs)} MTProto конфигов для тестирования", "info")
            
            # Запускаем тестирование MTProto - используем функцию с сохранением
            working, passed, failed = test_mtproto_configs_and_save(
                configs=configs,
                max_ping_ms=task['max_ping_ms'],
                required_count=task['required_count'],
                out_file=task['out_file'],
                profile_title=task['profile_title'],
                log_func=self.log,
                progress_func=self._progress_callback,
            )
            
            self.log(f"Результаты MTProto: ✓{passed} | ✗{failed} | 🔄{working}", "success")
    
    def _progress_callback(self, current, total):
        """Callback для обновления прогресса."""
        self.update_progress(current, total)
    
    def stop_operation(self):
        """Останавливает текущую операцию."""
        self.stop_flag = True
        self.log("Остановка операции...", "warning")
    
    def open_results(self):
        """Открывает папку с результатами."""
        try:
            if sys.platform == "win32":
                os.startfile(RESULTS_DIR)
            elif sys.platform == "darwin":
                os.system(f"open {RESULTS_DIR}")
            else:  # Linux
                os.system(f"xdg-open {RESULTS_DIR}")
            self.log(f"Открыта папка: {RESULTS_DIR}", "success")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {str(e)}")
    
    def merge_vpn_configs(self):
        """Объединяет top_vpn.txt и top_bypass.txt в all_top_vpn.txt.
        Дедупликация по базовой части URL (без #fragment)."""
        top_vpn_file = os.path.join(RESULTS_DIR, "top_vpn.txt")
        top_bypass_file = os.path.join(RESULTS_DIR, "top_bypass.txt")
        all_top_vpn_file = os.path.join(RESULTS_DIR, "all_top_vpn.txt")

        try:
            all_configs = []

            # Читаем из top_vpn.txt
            if os.path.exists(top_vpn_file):
                with open(top_vpn_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            all_configs.append(line)

            # Читаем из top_bypass.txt
            if os.path.exists(top_bypass_file):
                with open(top_bypass_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            all_configs.append(line)

            # Дедупликация по базовой части URL
            seen = set()
            configs = []
            for config in all_configs:
                key = config.split('#')[0].strip()
                if key not in seen:
                    seen.add(key)
                    configs.append(config)
            
            # Сохраняем объединённый файл
            if configs:
                os.makedirs(os.path.dirname(os.path.abspath(all_top_vpn_file)), exist_ok=True)
                with open(all_top_vpn_file, 'w', encoding='utf-8') as f:
                    f.write("#profile-title: arqVPN Free | Все\n")
                    f.write("#profile-update-interval: 48\n")
                    f.write("#support-url: https://t.me/arqhub\n")
                    f.write("\n")
                    for config in configs:
                        f.write(f"{config}\n")
                
                self.log(f"✓ Объединено {len(configs)} конфигов в all_top_vpn.txt", "success")
        except Exception as e:
            self.log(f"Ошибка при объединении: {str(e)}", "error")
    
    def ask_push_to_github(self):
        """Спрашивает об обновлении на GitHub."""
        response = messagebox.askyesno(
            "Обновление GitHub",
            "Обновить результаты в репозитории GitHub?"
        )
        
        if response:
            # Запускаем в отдельном потоке чтобы не блокировать UI
            thread = threading.Thread(target=self._push_to_github_thread)
            thread.daemon = True
            thread.start()
    
    def _push_to_github_thread(self):
        """Поток для push в GitHub."""
        try:
            self.log("\nОбновление репозитория...", "title")

            project_dir = os.path.dirname(os.path.abspath(__file__))

            # Поиск файлов результатов
            result_files = []
            for file in ["top_vpn.txt", "top_bypass.txt", "top_MTProto.txt", "all_top_vpn.txt"]:
                file_path = os.path.join(RESULTS_DIR, file)
                if os.path.exists(file_path):
                    result_files.append(os.path.join(RESULTS_DIR, file))

            if not result_files:
                self.log("Нет файлов результатов для обновления", "warning")
                return

            # Добавляем файлы
            for file_path in result_files:
                subprocess.run(
                    ["git", "add", file_path],
                    check=True,
                    capture_output=True,
                    cwd=project_dir
                )

            self.log(f"Добавлено {len(result_files)} файлов результатов", "info")

            # Проверяем изменения
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
                cwd=project_dir
            )

            if not status_result.stdout.strip():
                self.log("Нет изменений для коммита", "warning")
                return

            # Коммит
            commit_msg = f"Update VPN configs results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True,
                capture_output=True,
                cwd=project_dir
            )

            self.log("Коммит создан", "info")

            # Push
            push_result = subprocess.run(
                ["git", "push"],
                capture_output=True,
                text=True,
                check=False,
                cwd=project_dir
            )

            if push_result.returncode == 0:
                self.log("✓ Результаты успешно обновлены на GitHub!", "success")
                messagebox.showinfo("Успех", "Результаты успешно обновлены на GitHub!")
            else:
                error_msg = push_result.stderr or push_result.stdout
                self.log(f"Ошибка при отправке на GitHub: {error_msg.strip()}", "error")
                self.log("Коммит создан локально, но не отправлен на GitHub", "warning")
                messagebox.showwarning(
                    "Предупреждение",
                    "Коммит создан локально, но не удалось отправить на GitHub.\n"
                    "Проверьте подключение и попробуйте позже: git push"
                )

        except subprocess.CalledProcessError as e:
            self.log(f"Ошибка Git: {str(e)}", "error")
        except Exception as e:
            self.log(f"Ошибка: {str(e)}", "error")
            messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")


def main():
    """Запуск GUI приложения."""
    root = tk.Tk()
    app = ArcParseGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
