import customtkinter
from tkinter import filedialog, messagebox
import os
import shutil
import requests
import zipfile
import threading
import tempfile
import webbrowser
import time
import json # Для сохранения настроек
import sys # Для путей внутри EXE
from bs4 import BeautifulSoup
from pypresence import Presence

# --- КОНФИГУРАЦИЯ ---
CURRENT_VERSION = "1.3"
CONFIG_URL = "https://gist.githubusercontent.com/dima-kovboi/759c72034192738b22adfc7aa9f3bf24/raw/version.json"
TG_CHANNEL = "archive_dimakovboi"
DISCORD_CLIENT_ID = '1461806955902533726'
SETTINGS_FILE = "settings.json" # Файл куда будем сохранять пути

# --- ТЕМА И ЦВЕТА ---
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

COLOR_BG = "#0f0f13"
COLOR_FRAME = "#1a1a24"
COLOR_ACCENT = "#00f2ea"
COLOR_ACCENT_HOVER = "#00c2bb"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_SEC = "#a0a0a0"
COLOR_SUCCESS = "#00ff9d"
COLOR_ERROR = "#ff0055"
COLOR_DISABLED = "#333333"

# --- ФУНКЦИЯ ДЛЯ ПОИСКА РЕСУРСОВ (ЧТОБЫ ИКОНКА РАБОТАЛА В EXE) ---
def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу, работает для dev и для PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AnimatedButton(customtkinter.CTkButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_width = kwargs.get("width", 200)
        self.original_height = kwargs.get("height", 40)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

        if "fg_color" not in kwargs:
            self.configure(fg_color=COLOR_ACCENT, text_color="#000000", font=customtkinter.CTkFont(size=14, weight="bold"))
        if "hover_color" not in kwargs:
            self.configure(hover_color=COLOR_ACCENT_HOVER)
        if "corner_radius" not in kwargs:
            self.configure(corner_radius=8)

    def on_press(self, event):
        self.configure(width=self.original_width * 0.95, height=self.original_height * 0.95)

    def on_release(self, event):
        self.configure(width=self.original_width, height=self.original_height)

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Установщик модов от dimakovboi v{CURRENT_VERSION}")
        self.geometry("900x700")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)

        # --- УСТАНОВКА ИКОНКИ ---
        try:
            self.iconbitmap(resource_path("icon.ico"))
        except:
            pass # Если иконки нет, не крашимся

        # Переменные
        self.selected_mod_name = ""
        self.selected_version_type = ""
        self.install_type = "direct"
        self.source_path = ""
        self.destination_path = ""
        self.latest_version_url = ""
        self.mod_urls = {}
        self.create_subfolder_var = customtkinter.BooleanVar(value=True)
        self.rpc = None

        # --- ЗАГРУЗКА СОХРАНЕНИЙ ---
        self.load_settings()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        self.frames = {}
        self.mod_buttons = {}

        self.setup_main_menu()
        self.setup_version_select()
        self.setup_install_type()
        self.setup_install_process()

        self.show_frame("MainMenu")

        threading.Thread(target=self.load_remote_config, daemon=True).start()
        threading.Thread(target=self.load_tg_news, daemon=True).start()
        threading.Thread(target=self.init_discord_rpc, daemon=True).start()

    # --- СОХРАНЕНИЕ И ЗАГРУЗКА НАСТРОЕК ---
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.source_path = data.get("source_path", "")
                    self.destination_path = data.get("destination_path", "")
                    self.install_type = data.get("install_type", "direct")
            except:
                pass

    def save_settings(self):
        data = {
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "install_type": self.install_type
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f)
        except:
            pass

    # --- DISCORD RPC ---
    def init_discord_rpc(self):
        try:
            self.rpc = Presence(DISCORD_CLIENT_ID)
            self.rpc.connect()
            self.rpc.update(state="Выбирает моды", details=f"Mod Installer v{CURRENT_VERSION}", large_image="logo", start=time.time())
        except: pass

    def update_rpc(self, state_text):
        if self.rpc:
            try: self.rpc.update(state=state_text, details=f"Mod Installer v{CURRENT_VERSION}", large_image="logo")
            except: pass

    # --- НОВОСТИ ---
    def load_tg_news(self):
        try:
            url = f"https://t.me/s/{TG_CHANNEL}"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            posts = soup.find_all('div', class_='tgme_widget_message_text')
            last_posts = posts[-5:]

            for widget in self.news_scroll.winfo_children(): widget.destroy()

            if not last_posts:
                lbl = customtkinter.CTkLabel(self.news_scroll, text="Нет новостей...", text_color=COLOR_TEXT_SEC)
                lbl.pack(pady=10)
                return

            for post in reversed(last_posts):
                text = post.get_text(separator="\n")
                if len(text) > 150: text = text[:150] + "..."

                card = customtkinter.CTkFrame(self.news_scroll, fg_color="#2b2b38", corner_radius=6)
                card.pack(fill="x", pady=5, padx=5)

                header = customtkinter.CTkLabel(card, text="Новости Telegram", font=customtkinter.CTkFont(size=10, weight="bold"), text_color=COLOR_ACCENT, anchor="w")
                header.pack(fill="x", padx=10, pady=(5,0))

                content = customtkinter.CTkLabel(card, text=text, font=customtkinter.CTkFont(size=11), text_color=COLOR_TEXT, anchor="w", justify="left", wraplength=280)
                content.pack(fill="x", padx=10, pady=5)

                btn = customtkinter.CTkButton(card, text="Читать далее", height=20, fg_color="transparent", text_color=COLOR_ACCENT, hover_color="#333344", command=lambda: webbrowser.open(f"https://t.me/{TG_CHANNEL}"))
                btn.pack(fill="x", pady=(0,5))
        except Exception:
            lbl = customtkinter.CTkLabel(self.news_scroll, text="Ошибка загрузки новостей", text_color=COLOR_ERROR)
            lbl.pack(pady=10)

    # --- ЗАПУСК ИГРЫ ---
    def launch_game(self):
        # Приоритет поиска: 1. Выбранные пути 2. Стандартные пути
        paths_to_check = []

        # Если была установка в копию
        if self.install_type == "copy" and self.destination_path:
            paths_to_check.append(os.path.join(self.destination_path, "Among Us (Modded)", "Among Us.exe"))

        # Если прямая или просто путь
        if self.source_path:
            paths_to_check.append(os.path.join(self.source_path, "Among Us.exe"))

        # Стандартные
        possible_roots = [
            r"C:\Program Files (x86)\Steam\steamapps\common\Among Us",
            r"D:\SteamLibrary\steamapps\common\Among Us",
            r"C:\Program Files\Epic Games\AmongUs"
        ]
        for p in possible_roots: paths_to_check.append(os.path.join(p, "Among Us.exe"))

        game_exe = None
        for p in paths_to_check:
            if p and os.path.exists(p):
                game_exe = p
                break

        if game_exe:
            try:
                self.update_rpc("Играет в Among Us")
                os.startfile(game_exe)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось запустить: {e}")
        else:
            messagebox.showwarning("Игра не найдена", "Сначала выберите папку с игрой в меню установки!")

    # --- UI ---
    def setup_main_menu(self):
        frame = customtkinter.CTkFrame(self.container, corner_radius=15, fg_color=COLOR_FRAME)
        self.frames["MainMenu"] = frame

        top_panel = customtkinter.CTkFrame(frame, fg_color="transparent")
        top_panel.pack(fill="x", padx=30, pady=(25, 10))

        title_col = customtkinter.CTkFrame(top_panel, fg_color="transparent")
        title_col.pack(side="left")

        title = customtkinter.CTkLabel(title_col, text="MOD INSTALLER", font=customtkinter.CTkFont(family="Arial", size=28, weight="bold"), text_color=COLOR_ACCENT)
        title.pack(anchor="w")
        subtitle = customtkinter.CTkLabel(title_col, text=f"Version {CURRENT_VERSION}", font=customtkinter.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_SEC)
        subtitle.pack(anchor="w")

        play_btn = AnimatedButton(top_panel, text="▶ ИГРАТЬ", width=120, height=40, fg_color=COLOR_SUCCESS, hover_color="#00cc7a", text_color="black", command=self.launch_game)
        play_btn.pack(side="right")

        self.update_label = customtkinter.CTkLabel(frame, text="", text_color=COLOR_ACCENT, cursor="hand2")
        self.update_label.bind("<Button-1>", lambda e: self.open_update_url())

        content_row = customtkinter.CTkFrame(frame, fg_color="transparent")
        content_row.pack(fill="both", expand=True, padx=20, pady=10)

        mods_col = customtkinter.CTkFrame(content_row, fg_color="transparent")
        mods_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.scroll_frame = customtkinter.CTkScrollableFrame(mods_col, fg_color="transparent", label_text="КАТАЛОГ МОДОВ")
        self.scroll_frame.pack(fill="both", expand=True)

        lbl_cheats = customtkinter.CTkLabel(self.scroll_frame, text="🔥 ЧИТЫ", font=customtkinter.CTkFont(size=14, weight="bold"), text_color=COLOR_ERROR, anchor="w")
        lbl_cheats.pack(fill="x", pady=(5, 5))
        cheats_list = ["SickoMenu", "Mod Menu Crew", "MalumMenu"]
        for mod in cheats_list: self.add_mod_btn(mod)

        lbl_mods = customtkinter.CTkLabel(self.scroll_frame, text="🎭 РОЛИ", font=customtkinter.CTkFont(size=14, weight="bold"), text_color=COLOR_SUCCESS, anchor="w")
        lbl_mods.pack(fill="x", pady=(15, 5))
        mods_list = ["The Endless Host Roles", "AllTheRoles", "LotusContinued"]
        for mod in mods_list: self.add_mod_btn(mod)

        news_col = customtkinter.CTkFrame(content_row, fg_color="#21212e", corner_radius=10, width=300)
        news_col.pack(side="right", fill="y", padx=(10, 0))

        lbl_news = customtkinter.CTkLabel(news_col, text="НОВОСТИ", font=customtkinter.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_news.pack(pady=10)

        self.news_scroll = customtkinter.CTkScrollableFrame(news_col, fg_color="transparent", width=280)
        self.news_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        loading_lbl = customtkinter.CTkLabel(self.news_scroll, text="Загрузка из Telegram...", text_color=COLOR_TEXT_SEC)
        loading_lbl.pack(pady=20)

        footer = customtkinter.CTkLabel(frame, text=f"Разработано dimakovboi", text_color=COLOR_TEXT_SEC, font=customtkinter.CTkFont(size=10))
        footer.pack(side="bottom", pady=10)

    def add_mod_btn(self, mod_name):
        btn = AnimatedButton(self.scroll_frame, text=mod_name, height=45, width=380, command=lambda m=mod_name: self.select_mod(m))
        btn.pack(pady=5)
        self.mod_buttons[mod_name] = btn

    # ОСТАЛЬНЫЕ ЭКРАНЫ
    def setup_version_select(self):
        frame = customtkinter.CTkFrame(self.container, corner_radius=15, fg_color=COLOR_FRAME)
        self.frames["VersionSelect"] = frame
        self.ver_title = customtkinter.CTkLabel(frame, text="ВЫБОР ВЕРСИИ", font=customtkinter.CTkFont(size=24, weight="bold"), text_color=COLOR_TEXT)
        self.ver_title.pack(pady=(40, 10))
        self.ver_subtitle = customtkinter.CTkLabel(frame, text="Какая у вас версия игры?", font=customtkinter.CTkFont(size=14), text_color=COLOR_TEXT_SEC)
        self.ver_subtitle.pack(pady=(0, 40))
        btn_steam = AnimatedButton(frame, text="Steam / itch.io / Пиратка", height=50, width=350, command=lambda: self.select_version_type("steam"))
        btn_steam.pack(pady=10)
        btn_epic = AnimatedButton(frame, text="Epic Games / Microsoft Store", height=50, width=350, command=lambda: self.select_version_type("epic"))
        btn_epic.pack(pady=10)
        btn_back = customtkinter.CTkButton(frame, text="Назад", fg_color="transparent", border_width=1, border_color=COLOR_TEXT_SEC, text_color=COLOR_TEXT_SEC, hover_color="#333333", width=100, command=lambda: self.show_frame("MainMenu"))
        btn_back.pack(side="bottom", pady=30)

    def setup_install_type(self):
        frame = customtkinter.CTkFrame(self.container, corner_radius=15, fg_color=COLOR_FRAME)
        self.frames["InstallType"] = frame
        title = customtkinter.CTkLabel(frame, text="СПОСОБ УСТАНОВКИ", font=customtkinter.CTkFont(size=24, weight="bold"), text_color=COLOR_TEXT)
        title.pack(pady=(40, 40))
        btn_direct = AnimatedButton(frame, text="Установить в папку с игрой", height=50, width=350, command=lambda: self.setup_install_screen("direct"))
        btn_direct.pack(pady=10)
        lbl_direct = customtkinter.CTkLabel(frame, text="Заменяет файлы в папке с игрой.", text_color=COLOR_TEXT_SEC, font=customtkinter.CTkFont(size=11))
        lbl_direct.pack(pady=(0, 20))
        btn_copy = AnimatedButton(frame, text="Создать отдельную копию", height=50, width=350, command=lambda: self.setup_install_screen("copy"))
        btn_copy.pack(pady=10)
        lbl_copy = customtkinter.CTkLabel(frame, text="Сохраняет оригинальную игру.", text_color=COLOR_TEXT_SEC, font=customtkinter.CTkFont(size=11))
        lbl_copy.pack(pady=(0, 20))
        btn_back = customtkinter.CTkButton(frame, text="Назад", fg_color="transparent", border_width=1, border_color=COLOR_TEXT_SEC, text_color=COLOR_TEXT_SEC, hover_color="#333333", width=100, command=lambda: self.show_frame("VersionSelect"))
        btn_back.pack(side="bottom", pady=30)

    def setup_install_process(self):
        frame = customtkinter.CTkFrame(self.container, corner_radius=15, fg_color=COLOR_FRAME)
        self.frames["InstallProcess"] = frame
        self.proc_title = customtkinter.CTkLabel(frame, text="УСТАНОВКА", font=customtkinter.CTkFont(size=24, weight="bold"), text_color=COLOR_TEXT)
        self.proc_title.pack(pady=(30, 20))
        self.path_frame = customtkinter.CTkFrame(frame, fg_color="transparent")
        self.path_frame.pack(fill="x", padx=40)
        self.lbl_source = customtkinter.CTkLabel(self.path_frame, text="Папка с оригинальной игрой:", text_color=COLOR_ACCENT, anchor="w")
        self.lbl_source.pack(fill="x")
        self.entry_source = customtkinter.CTkEntry(self.path_frame, placeholder_text="Выберите папку...", state="disabled", fg_color="#2b2b38", border_color="#2b2b38")
        self.entry_source.pack(fill="x", pady=(5, 10))
        self.btn_sel_source = customtkinter.CTkButton(self.path_frame, text="Обзор...", width=100, fg_color="#333344", hover_color="#444455", command=self.select_source_folder)
        self.btn_sel_source.pack(anchor="e")
        self.dest_container = customtkinter.CTkFrame(self.path_frame, fg_color="transparent")
        self.lbl_dest = customtkinter.CTkLabel(self.dest_container, text="Папка для копии:", text_color=COLOR_ACCENT, anchor="w")
        self.lbl_dest.pack(fill="x")
        self.entry_dest = customtkinter.CTkEntry(self.dest_container, placeholder_text="Выберите папку...", state="disabled", fg_color="#2b2b38", border_color="#2b2b38")
        self.entry_dest.pack(fill="x", pady=(5, 10))
        self.btn_sel_dest = customtkinter.CTkButton(self.dest_container, text="Обзор...", width=100, fg_color="#333344", hover_color="#444455", command=self.select_destination_folder)
        self.btn_sel_dest.pack(anchor="e")
        self.chk_subfolder = customtkinter.CTkCheckBox(self.dest_container, text="Создать подпапку 'Among Us (Modded)'", variable=self.create_subfolder_var, text_color=COLOR_TEXT, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER)
        self.chk_subfolder.pack(pady=10, anchor="w")
        self.progress_frame = customtkinter.CTkFrame(frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=40, pady=20)
        self.status_label = customtkinter.CTkLabel(self.progress_frame, text="Готов к установке", text_color=COLOR_TEXT_SEC)
        self.status_label.pack(anchor="w")
        self.progress_bar = customtkinter.CTkProgressBar(self.progress_frame, height=15, corner_radius=5)
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color=COLOR_ACCENT)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_info = customtkinter.CTkLabel(self.progress_frame, text="0% | 0.0 MB/s | Ост: --:--", text_color=COLOR_TEXT_SEC, font=customtkinter.CTkFont(size=11))
        self.progress_info.pack(anchor="e")
        self.action_buttons = customtkinter.CTkFrame(frame, fg_color="transparent")
        self.action_buttons.pack(side="bottom", fill="x", padx=40, pady=30)
        self.btn_install_start = AnimatedButton(self.action_buttons, text="НАЧАТЬ УСТАНОВКУ", fg_color=COLOR_SUCCESS, hover_color="#00cc7a", text_color="black", height=50, command=self.start_installation, state="disabled")
        self.btn_install_start.pack(fill="x", pady=(0, 10))
        self.btn_proc_back = customtkinter.CTkButton(self.action_buttons, text="Назад", fg_color="transparent", border_width=1, border_color=COLOR_TEXT_SEC, text_color=COLOR_TEXT_SEC, hover_color="#333333", command=lambda: self.show_frame("InstallType"))
        self.btn_proc_back.pack(fill="x")

    def show_frame(self, name):
        for frame in self.frames.values(): frame.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    def select_mod(self, mod_name):
        self.selected_mod_name = mod_name
        if mod_name not in self.mod_urls: return
        self.show_frame("VersionSelect")

    def select_version_type(self, v_type):
        self.selected_version_type = v_type
        self.show_frame("InstallType")

    def setup_install_screen(self, i_type):
        self.install_type = i_type
        # Если пути уже сохранены - подгружаем их
        if not self.source_path: self.entry_source.delete(0, "end")
        else:
            self.entry_source.configure(state="normal")
            self.entry_source.delete(0, "end")
            self.entry_source.insert(0, self.source_path)
            self.entry_source.configure(state="disabled")

        if not self.destination_path: self.entry_dest.delete(0, "end")
        else:
            self.entry_dest.configure(state="normal")
            self.entry_dest.delete(0, "end")
            self.entry_dest.insert(0, self.destination_path)
            self.entry_dest.configure(state="disabled")

        self.progress_bar.set(0)
        self.progress_info.configure(text="0% | 0.0 MB/s | Ост: --:--")
        self.status_label.configure(text="Готов к установке", text_color=COLOR_TEXT_SEC)

        # Сбрасываем кнопку обратно на "Установить" (вдруг она была "Играть")
        self.btn_install_start.configure(
            text="НАЧАТЬ УСТАНОВКУ",
            fg_color=COLOR_SUCCESS,
            hover_color="#00cc7a",
            command=self.start_installation
        )
        self._update_install_button_state()

        if i_type == "copy": self.dest_container.pack(fill="x", pady=(10, 0))
        else: self.dest_container.pack_forget()
        self.show_frame("InstallProcess")

    def select_source_folder(self):
        path = filedialog.askdirectory(title="Выберите папку Among Us")
        if path:
            self.source_path = os.path.normpath(path)
            self.save_settings() # Сохраняем
            self.entry_source.configure(state="normal")
            self.entry_source.delete(0, "end")
            self.entry_source.insert(0, self.source_path)
            self.entry_source.configure(state="disabled")
            self._update_install_button_state()

    def select_destination_folder(self):
        path = filedialog.askdirectory(title="Выберите папку назначения")
        if path:
            self.destination_path = os.path.normpath(path)
            self.save_settings() # Сохраняем
            self.entry_dest.configure(state="normal")
            self.entry_dest.delete(0, "end")
            self.entry_dest.insert(0, self.destination_path)
            self.entry_dest.configure(state="disabled")
            self._update_install_button_state()

    def _update_install_button_state(self):
        valid = False
        if self.install_type == "direct" and self.source_path: valid = True
        elif self.install_type == "copy" and self.source_path and self.destination_path: valid = True

        if valid: self.btn_install_start.configure(state="normal")
        else: self.btn_install_start.configure(state="disabled")

    def compare_versions(self, ver1, ver2):
        try:
            v1_parts = [int(x) for x in ver1.split(".")]
            v2_parts = [int(x) for x in ver2.split(".")]
            return v1_parts > v2_parts
        except: return ver1 > ver2

    def show_mod_info(self, title, reason):
        messagebox.showinfo(title, reason)

    def load_remote_config(self):
        try:
            response = requests.get(CONFIG_URL, timeout=10)
            response.raise_for_status()
            config = response.json()
            latest_version = config.get("version")
            self.latest_version_url = config.get("url")
            if latest_version and self.latest_version_url:
                if self.compare_versions(latest_version, CURRENT_VERSION):
                    self.update_label.configure(text=f"ДОСТУПНО ОБНОВЛЕНИЕ: {latest_version} (Нажмите чтобы скачать)")
                    self.update_label.pack(side="top", pady=(0, 10))
            mods_config = config.get("mods", {})
            for mod_name, button in self.mod_buttons.items():
                mod_data = mods_config.get(mod_name)
                if mod_data:
                    if mod_data.get("enabled", False):
                        self.mod_urls[mod_name] = mod_data.get("urls", {})
                        button.configure(state="normal", text=mod_name, fg_color=COLOR_ACCENT)
                    else:
                        reason = mod_data.get("reason", "Временно недоступен")
                        button.configure(state="normal", text=f"{mod_name} [Смотри Инфо]", fg_color=COLOR_DISABLED, hover_color=COLOR_DISABLED, text_color=COLOR_TEXT_SEC, command=lambda r=reason, n=mod_name: self.show_mod_info(f"Информация о {n}", r))
                else: button.configure(state="disabled", text=f"{mod_name} [Ошибка]")
        except Exception: pass

    def open_update_url(self):
        if self.latest_version_url: webbrowser.open_new(self.latest_version_url)

    def start_installation(self):
        self.btn_install_start.configure(state="disabled")
        self.btn_proc_back.configure(state="disabled")
        self.btn_sel_source.configure(state="disabled")
        self.btn_sel_dest.configure(state="disabled")
        self.update_rpc(f"Устанавливает {self.selected_mod_name}")
        threading.Thread(target=self._execute_installation, daemon=True).start()

    def _execute_installation(self):
        try:
            target_path = ""
            if self.install_type == "direct": target_path = self.source_path
            elif self.install_type == "copy":
                if self.create_subfolder_var.get(): target_path = os.path.join(self.destination_path, "Among Us (Modded)")
                else: target_path = self.destination_path

            if not os.path.exists(os.path.join(self.source_path, "Among Us.exe")): raise ValueError("Among Us.exe не найден!")
            if self.install_type == "copy" and not self.create_subfolder_var.get() and self.source_path == target_path: raise ValueError("Пути совпадают!")

            if self.install_type == "copy":
                self.update_status("Копирование игры...", COLOR_ACCENT)
                if os.path.exists(target_path): shutil.rmtree(target_path)
                shutil.copytree(self.source_path, target_path)

            self.update_status("Очистка...", COLOR_ACCENT)
            items = ["winhttp.dll", "doorstop_config.ini", "changelog.txt", ".doorstop_version", "BepInEx", "dotnet"]
            for i in items:
                p = os.path.join(target_path, i)
                if os.path.isdir(p): shutil.rmtree(p)
                elif os.path.isfile(p): os.remove(p)

            self.update_status("Скачивание...", COLOR_ACCENT)
            mod_url = self.mod_urls.get(self.selected_mod_name, {}).get(self.selected_version_type)
            if not mod_url: raise ValueError("Ссылка не найдена!")

            resp = requests.get(mod_url, stream=True)
            resp.raise_for_status()
            total = int(resp.headers.get('content-length', 0))
            down = 0
            start = time.time()

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                for chunk in resp.iter_content(8192):
                    tmp.write(chunk)
                    down += len(chunk)
                    if total:
                        pct = down / total
                        el = time.time() - start
                        spd = down / (el if el > 0 else 1)
                        eta = (total - down) / spd if spd > 0 else 0
                        self.update_progress(pct, spd, eta)
                zip_path = tmp.name

            self.update_status("Распаковка...", COLOR_ACCENT)
            with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(target_path)
            os.remove(zip_path)

            self.update_status("УСТАНОВКА ЗАВЕРШЕНА!", COLOR_SUCCESS)
            self.progress_bar.set(1)
            self.update_rpc("Мод установлен!")

            # --- СМЕНА КНОПКИ НА "ИГРАТЬ" ---
            self.btn_install_start.configure(
                text="ИГРАТЬ В AMONG US",
                fg_color="#00a86b",
                hover_color="#008f5b",
                state="normal",
                command=self.launch_game # Теперь кнопка запускает игру
            )

        except Exception as e:
            self.update_status(f"Ошибка: {e}", COLOR_ERROR)
        finally:
            self.btn_proc_back.configure(state="normal")
            self.btn_sel_source.configure(state="normal")
            self.btn_sel_dest.configure(state="normal")
            # Если произошла ошибка, кнопка останется неактивной.
            # Если успех - она уже изменена выше.
            if "Ошибка" in self.status_label.cget("text"):
                self._update_install_button_state()

    def update_status(self, text, color):
        self.status_label.configure(text=text, text_color=color)

    def update_progress(self, percent, speed, eta):
        self.progress_bar.set(percent)
        self.progress_info.configure(text=f"{int(percent*100)}% | {speed/1048576:.1f} MB/s | Ост: {int(eta)}с")

if __name__ == "__main__":
    app = App()
    app.mainloop()