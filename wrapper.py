import customtkinter as ctk
import subprocess
import threading
import os
import tkinter
from tkinter import filedialog, messagebox

class BotLavalinkWrapper(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Bot & Lavalink Wrapper")
        self.geometry("900x600")
        self.bot_proc = None
        self.lavalink_proc = None
        self.bot_path = "main.py"
        self.lavalink_path = "Lavalink.jar"  # Default, can be changed in settings
        self.venv_python_path = ""  # Path to venv python, set in settings
        self.load_settings()
        self.create_widgets()
        # Ensure child processes are killed on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.start_auto_refresh_log()

    def on_close(self):
        # Terminate bot and lavalink if running
        import signal
        if self.bot_proc and self.bot_proc.poll() is None:
            try:
                self.bot_proc.terminate()
            except Exception:
                pass
        if self.lavalink_proc and self.lavalink_proc.poll() is None:
            try:
                self.lavalink_proc.terminate()
            except Exception:
                pass
        # Give processes a moment to terminate
        self.stop_auto_refresh_log()
        self.after(300, self.destroy)

    def create_widgets(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True)
        
        # Tabs
        self.tab_console = self.tabview.add("Consoles")
        self.tab_settings = self.tabview.add("Settings")
        self.tab_env = self.tabview.add(".env & Config Editor")

        self.setup_console_tab()
        self.setup_settings_tab()
        self.setup_env_tab()

    def setup_console_tab(self):
        # Use a PanedWindow for resizable log windows
        paned = tkinter.PanedWindow(self.tab_console, orient=tkinter.VERTICAL, sashrelief=tkinter.RAISED)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        # Bot console
        bot_console_frame = ctk.CTkFrame(paned)
        # Add a horizontal frame for bot log controls (Refresh button)
        bot_log_controls = ctk.CTkFrame(bot_console_frame)
        bot_log_controls.pack(fill="x", anchor="n", pady=(0,2))
        self.refresh_btn = ctk.CTkButton(bot_log_controls, text="Refresh Log", width=100, command=self.refresh_bot_log)
        self.refresh_btn.pack(side="right", padx=2)
        self.bot_console = ctk.CTkTextbox(bot_console_frame, height=10)
        self.bot_console.pack(fill="both", expand=True)
        self.bot_console.insert("end", "[Bot console output here]\n")
        paned.add(bot_console_frame, minsize=80)

        # Lavalink console
        lavalink_console_frame = ctk.CTkFrame(paned)
        self.lavalink_console = ctk.CTkTextbox(lavalink_console_frame, height=10)
        self.lavalink_console.pack(fill="both", expand=True)
        self.lavalink_console.insert("end", "[Lavalink console output here]\n")
        paned.add(lavalink_console_frame, minsize=80)

        # Controls
        btn_frame = ctk.CTkFrame(self.tab_console)
        btn_frame.pack(pady=5)
        ctk.CTkButton(btn_frame, text="Start Bot", command=self.start_bot).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Stop Bot", command=self.stop_bot).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Restart Bot", command=self.restart_bot).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Start Lavalink", command=self.start_lavalink).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Stop Lavalink", command=self.stop_lavalink).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Restart Lavalink", command=self.restart_lavalink).pack(side="left", padx=5)

    def refresh_bot_log(self):
        """Reload the entire bot.log into the bot console."""
        import os
        log_path = os.path.join("cache", "logs", "bot.log")
        self.bot_console.delete("1.0", "end")
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()
                if log_content.strip():
                    self.bot_console.insert("end", log_content + ("\n" if not log_content.endswith("\n") else ""))
            except Exception as e:
                self.bot_console.insert("end", f"[Failed to read bot.log: {e}]\n")
        else:
            self.bot_console.insert("end", "[bot.log not found]\n")
        self.bot_console.see("end")

    def start_auto_refresh_log(self):
        self._auto_refresh_log = True
        self._auto_refresh_log_loop()

    def stop_auto_refresh_log(self):
        self._auto_refresh_log = False

    def _auto_refresh_log_loop(self):
        if getattr(self, '_auto_refresh_log', False):
            self.refresh_bot_log()
            self.after(1000, self._auto_refresh_log_loop)

    def setup_settings_tab(self):
        # Path selectors
        ctk.CTkLabel(self.tab_settings, text="Bot Path:").pack(anchor="w", padx=10, pady=2)
        self.bot_path_entry = ctk.CTkEntry(self.tab_settings, width=400)
        self.bot_path_entry.insert(0, self.bot_path)
        self.bot_path_entry.pack(anchor="w", padx=10, pady=2)
        ctk.CTkButton(self.tab_settings, text="Browse", command=self.browse_bot_path).pack(anchor="w", padx=10, pady=2)
        ctk.CTkLabel(self.tab_settings, text="Lavalink Path:").pack(anchor="w", padx=10, pady=2)
        self.lavalink_path_entry = ctk.CTkEntry(self.tab_settings, width=400)
        self.lavalink_path_entry.insert(0, self.lavalink_path)
        self.lavalink_path_entry.pack(anchor="w", padx=10, pady=2)
        ctk.CTkButton(self.tab_settings, text="Browse", command=self.browse_lavalink_path).pack(anchor="w", padx=10, pady=2)
        # venv Python path
        ctk.CTkLabel(self.tab_settings, text="Python Executable (venv):").pack(anchor="w", padx=10, pady=2)
        self.venv_python_entry = ctk.CTkEntry(self.tab_settings, width=400)
        self.venv_python_entry.insert(0, getattr(self, 'venv_python_path', ""))
        self.venv_python_entry.pack(anchor="w", padx=10, pady=2)
        ctk.CTkButton(self.tab_settings, text="Browse", command=self.browse_venv_python_path).pack(anchor="w", padx=10, pady=2)
        ctk.CTkButton(self.tab_settings, text="Save Settings", command=self.save_settings).pack(anchor="w", padx=10, pady=10)
    def browse_venv_python_path(self):
        path = filedialog.askopenfilename(filetypes=[("Python Executable", "python*.exe")])
        if path:
            self.venv_python_entry.delete(0, "end")
            self.venv_python_entry.insert(0, path)
            self.venv_python_path = path

    def save_settings(self):
        # Save settings to a file (wrapper_settings.json)
        import json
        settings = {
            "bot_path": self.bot_path_entry.get(),
            "lavalink_path": self.lavalink_path_entry.get(),
            "venv_python_path": self.venv_python_entry.get(),
        }
        with open("wrapper_settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        self.bot_path = settings["bot_path"]
        self.lavalink_path = settings["lavalink_path"]
        self.venv_python_path = settings["venv_python_path"]
        messagebox.showinfo("Settings", "Settings saved!")

    def load_settings(self):
        import json
        if os.path.exists("wrapper_settings.json"):
            try:
                with open("wrapper_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.bot_path = settings.get("bot_path", self.bot_path)
                self.lavalink_path = settings.get("lavalink_path", self.lavalink_path)
                self.venv_python_path = settings.get("venv_python_path", "")
            except Exception:
                pass

    def setup_env_tab(self):
        # Make the whole env/config editor scrollable
        # Use a Frame inside a Canvas for proper scrolling and no whitespace
        container = ctk.CTkFrame(self.tab_env)
        container.pack(fill="both", expand=True)
        canvas = tkinter.Canvas(container, borderwidth=0, highlightthickness=0)
        scrollbar = tkinter.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ctk.CTkFrame(canvas)
        scrollable_frame_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        def _on_canvas_configure(event):
            canvas.itemconfig(scrollable_frame_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scroll support (cross-platform)
        def _on_mousewheel(event):
            if os.name == 'nt':
                canvas.yview_scroll(-1 * int(event.delta / 120), "units")
            elif os.name == 'posix':
                canvas.yview_scroll(-1 * int(event.delta), "units")
            else:
                canvas.yview_scroll(-1 * int(event.delta), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))

        # .env editor
        env_frame = ctk.CTkFrame(scrollable_frame)
        env_frame.pack(fill="x", padx=10, pady=10, anchor="n")
        ctk.CTkLabel(env_frame, text=".env Editor", font=("Arial", 14, "bold")).pack(anchor="w")
        self.env_entries = {}
        self.env_show_buttons = {}
        env_path = os.path.join(os.getcwd(), ".env")
        env_vars = {}
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.strip().startswith("#") and "=" in line:
                        k, v = line.strip().split("=", 1)
                        env_vars[k] = v
        # Heuristic: treat keys with 'TOKEN', 'KEY', 'SECRET', 'PASSWORD' as sensitive
        sensitive_keys = [k for k in env_vars if any(x in k.upper() for x in ["TOKEN", "KEY", "SECRET", "PASSWORD"])]
        for k, v in env_vars.items():
            row_frame = ctk.CTkFrame(env_frame)
            row_frame.pack(fill="x", pady=2)
            ctk.CTkLabel(row_frame, text=k+":").pack(side="left")
            show_var = tkinter.BooleanVar(value=False)
            if k in sensitive_keys:
                entry = ctk.CTkEntry(row_frame, width=400, show="*")
                btn = ctk.CTkButton(row_frame, text="👁", width=30, command=lambda e=None, ent=None, var=None: self.toggle_show(ent, var), fg_color="#444")
                # Use lambda default args to bind current entry and var
                btn.configure(command=lambda ent=entry, var=show_var: self.toggle_show(ent, var))
                btn.pack(side="right", padx=2)
                self.env_show_buttons[k] = (entry, show_var)
            else:
                entry = ctk.CTkEntry(row_frame, width=400)
            entry.insert(0, v)
            entry.pack(side="left", padx=2, fill="x", expand=True)
            self.env_entries[k] = entry
        ctk.CTkButton(env_frame, text="Save .env", command=self.save_env).pack(anchor="w", pady=5)

        # config.py editor (simple key=value pairs only)
        config_frame = ctk.CTkFrame(scrollable_frame)
        config_frame.pack(fill="x", padx=10, pady=10, anchor="n")
        ctk.CTkLabel(config_frame, text="core/config.py Editor", font=("Arial", 14, "bold")).pack(anchor="w")
        self.config_entries = {}
        self.config_show_buttons = {}
        config_path = os.path.join("core", "config.py")
        # --- Robust multi-line config parser ---
        config_vars = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.strip().startswith('#') or '=' not in line:
                    i += 1
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.lstrip()
                # Triple-quoted string
                if v.startswith('"""') or v.startswith("'''"):
                    quote = v[:3]
                    val_lines = []
                    # If ends on same line
                    if v.count(quote) == 2:
                        val = v.split(quote)[1]
                        config_vars[k] = val
                        i += 1
                        continue
                    # Multiline string
                    v = v[3:]
                    if v:
                        val_lines.append(v)
                    i += 1
                    while i < len(lines):
                        l = lines[i]
                        if l.strip().endswith(quote):
                            val_lines.append(l.rstrip()[:-3])
                            break
                        else:
                            val_lines.append(l.rstrip('\n'))
                        i += 1
                    config_vars[k] = '\n'.join(val_lines)
                    i += 1
                    continue
                # Multi-line dict/list
                elif v.startswith('{') or v.startswith('['):
                    open_bracket = v[0]
                    close_bracket = '}' if open_bracket == '{' else ']'
                    val_lines = [v.rstrip('\n')]
                    depth = v.count(open_bracket) - v.count(close_bracket)
                    i += 1
                    while i < len(lines) and depth > 0:
                        l = lines[i]
                        val_lines.append(l.rstrip('\n'))
                        depth += l.count(open_bracket) - l.count(close_bracket)
                        i += 1
                    config_vars[k] = '\n'.join(val_lines)
                    continue
                else:
                    # Single line value
                    config_vars[k] = v.strip().strip('"').strip("'")
                    i += 1
        sensitive_keys_cfg = [k for k in config_vars if any(x in k.upper() for x in ["TOKEN", "KEY", "SECRET", "PASSWORD"])]
        import ast, json
        for k, v in config_vars.items():
            row_frame = ctk.CTkFrame(config_frame)
            row_frame.pack(fill="x", pady=2)
            ctk.CTkLabel(row_frame, text=k+":").pack(side="left")
            show_var = tkinter.BooleanVar(value=False)
            # Try to parse value as Python literal (list, dict, etc.)
            parsed = None
            try:
                if v.strip().startswith('{') or v.strip().startswith('['):
                    parsed = ast.literal_eval(v)
            except Exception:
                parsed = None
            # If it's a dict/list, use a textbox with pretty JSON
            if isinstance(parsed, (list, dict)):
                text = ctk.CTkTextbox(row_frame, width=400, height=80)
                text.insert("1.0", json.dumps(parsed, indent=2, ensure_ascii=False))
                text.pack(side="left", padx=2, fill="x", expand=True)
                self.config_entries[k] = text
            # If it's a multiline string (personality, prompts, etc.)
            elif '\n' in v:
                text = ctk.CTkTextbox(row_frame, width=400, height=80)
                text.insert("1.0", v)
                text.pack(side="left", padx=2, fill="x", expand=True)
                self.config_entries[k] = text
            elif k in sensitive_keys_cfg:
                entry = ctk.CTkEntry(row_frame, width=400, show="*")
                btn = ctk.CTkButton(row_frame, text="👁", width=30, command=lambda e=None, ent=None, var=None: self.toggle_show(ent, var), fg_color="#444")
                btn.configure(command=lambda ent=entry, var=show_var: self.toggle_show(ent, var))
                btn.pack(side="right", padx=2)
                entry.insert(0, v)
                entry.pack(side="left", padx=2, fill="x", expand=True)
                self.config_show_buttons[k] = (entry, show_var)
                self.config_entries[k] = entry
            else:
                entry = ctk.CTkEntry(row_frame, width=400)
                entry.insert(0, v)
                entry.pack(side="left", padx=2, fill="x", expand=True)
                self.config_entries[k] = entry
        ctk.CTkButton(config_frame, text="Save config.py", command=self.save_config).pack(anchor="w", pady=5)

        # Discord Guild IDs configuration (special section for server IDs)
        guild_frame = ctk.CTkFrame(scrollable_frame)
        guild_frame.pack(fill="x", padx=10, pady=10, anchor="n")
        ctk.CTkLabel(guild_frame, text="⚙️ Discord Server IDs for Slash Commands", font=("Arial", 14, "bold")).pack(anchor="w")
        ctk.CTkLabel(guild_frame, text="Add server IDs to sync slash commands only to specific servers (faster updates). Leave empty to sync globally.", wraplength=400, justify="left").pack(anchor="w", pady=(0, 10))
        
        # Guild IDs list with add/remove
        list_frame = ctk.CTkFrame(guild_frame)
        list_frame.pack(fill="both", expand=True, pady=5)
        
        # Textbox for guild IDs (one per line)
        ctk.CTkLabel(list_frame, text="Server IDs (one per line):").pack(anchor="w")
        self.guild_ids_textbox = ctk.CTkTextbox(list_frame, height=100)
        self.guild_ids_textbox.pack(fill="both", expand=True, pady=5)
        
        # Load existing guild IDs from config.py
        guild_ids_list = []
        try:
            import re
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    match = re.search(r'DISCORD_GUILD_IDS\s*=\s*\[(.*?)\]', content, re.DOTALL)
                    if match:
                        ids_str = match.group(1).strip()
                        if ids_str:
                            guild_ids_list = [id.strip() for id in ids_str.split(',') if id.strip()]
        except Exception:
            pass
        
        # Display guild IDs in textbox
        self.guild_ids_textbox.insert("1.0", "\n".join(guild_ids_list))
        
        # Button frame for guild operations
        guild_btn_frame = ctk.CTkFrame(guild_frame)
        guild_btn_frame.pack(fill="x", pady=5)
        ctk.CTkButton(guild_btn_frame, text="Save Guild IDs", command=self.save_guild_ids).pack(side="left", padx=5)
        ctk.CTkButton(guild_btn_frame, text="Clear All", command=lambda: self.guild_ids_textbox.delete("1.0", "end")).pack(side="left", padx=5)

    def toggle_show(self, entry, var):
        # Toggle between password and normal entry
        if var.get():
            entry.configure(show="*")
            var.set(False)
        else:
            entry.configure(show="")
            var.set(True)

    def save_env(self):
        env_path = os.path.join(os.getcwd(), ".env")
        lines = []
        for k, entry in self.env_entries.items():
            v = entry.get()
            lines.append(f"{k}={v}")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        messagebox.showinfo(".env", ".env saved!")

    def save_config(self):
        import ast, json
        config_path = os.path.join("core", "config.py")
        # Read original lines to preserve comments and structure
        if not os.path.exists(config_path):
            return
        with open(config_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        i = 0
        skip_keys = set()
        # Build a map of key: (start, end) for all config keys in the file
        key_ranges = {}
        while i < len(lines):
            line = lines[i]
            if line.strip() and not line.strip().startswith("#") and "=" in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.lstrip()
                start = i
                # Triple-quoted string
                if v.startswith('"""') or v.startswith("'''"):
                    quote = v[:3]
                    if v.count(quote) == 2:
                        end = i
                    else:
                        i += 1
                        while i < len(lines) and not lines[i].strip().endswith(quote):
                            i += 1
                        end = i
                # Multi-line dict/list
                elif v.startswith('{') or v.startswith('['):
                    open_bracket = v[0]
                    close_bracket = '}' if open_bracket == '{' else ']'
                    depth = v.count(open_bracket) - v.count(close_bracket)
                    i += 1
                    while i < len(lines) and depth > 0:
                        l = lines[i]
                        depth += l.count(open_bracket) - l.count(close_bracket)
                        i += 1
                    end = i - 1
                else:
                    end = i
                key_ranges[k] = (start, end)
            i += 1
        # Now, build new_lines, replacing only the keys that are edited, preserving all others
        i = 0
        used_keys = set()
        while i < len(lines):
            line = lines[i]
            if line.strip() and not line.strip().startswith("#") and "=" in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.lstrip()
                if k in self.config_entries and k not in used_keys:
                    widget = self.config_entries[k]
                    # Multiline string or dict/list
                    if isinstance(widget, ctk.CTkTextbox):
                        val = widget.get("1.0", "end").rstrip('\n')
                        # If original was dict/list, try to parse and pretty-print as Python
                        if v.startswith('{') or v.startswith('['):
                            try:
                                parsed = json.loads(val)
                                pretty = json.dumps(parsed, ensure_ascii=False, indent=4)
                                pretty = pretty.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                                new_lines.append(f'{k} = {pretty}\n')
                            except Exception:
                                new_lines.append(f'{k} = {val}\n')
                        elif v.startswith('"""') or v.startswith("'''") or '\n' in val:
                            safe_val = val.replace('"""', '\"\"\"')
                            new_lines.append(f'{k} = """{safe_val}"""\n')
                        else:
                            new_lines.append(f'{k} = "{val}"\n')
                    else:
                        val = widget.get()
                        if v.startswith('"'):
                            new_lines.append(f'{k} = "{val}"\n')
                        elif v.startswith("'"):
                            new_lines.append(f"{k} = '{val}'\n")
                        else:
                            new_lines.append(f"{k} = {val}\n")
                    # Skip all lines for this key (multi-line safe)
                    start, end = key_ranges.get(k, (i, i))
                    i = end + 1
                    used_keys.add(k)
                    continue
            new_lines.append(line)
            i += 1
        # Deduplicate: add any new keys not present in file
        for k, widget in self.config_entries.items():
            if k in used_keys:
                continue
            if isinstance(widget, ctk.CTkTextbox):
                val = widget.get("1.0", "end").rstrip('\n')
                try:
                    parsed = json.loads(val)
                    pretty = json.dumps(parsed, ensure_ascii=False, indent=4)
                    pretty = pretty.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                    new_lines.append(f'{k} = {pretty}\n')
                except Exception:
                    new_lines.append(f'{k} = """{val}"""\n')
            else:
                val = widget.get()
                new_lines.append(f'{k} = "{val}"\n')
        with open(config_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        messagebox.showinfo("config.py", "config.py saved!")

    def save_guild_ids(self):
        """Save Discord Guild IDs to config.py"""
        import re
        config_path = os.path.join("core", "config.py")
        
        # Get guild IDs from textbox
        guild_ids_text = self.guild_ids_textbox.get("1.0", "end").strip()
        guild_ids = [id.strip() for id in guild_ids_text.split('\n') if id.strip()]
        
        # Validate that each ID is numeric
        try:
            guild_ids = [int(id) for id in guild_ids]
        except ValueError:
            messagebox.showerror("Invalid Guild ID", "All Guild IDs must be numeric values.")
            return
        
        # Read current config
        if not os.path.exists(config_path):
            messagebox.showerror("Error", "config.py not found.")
            return
        
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Replace DISCORD_GUILD_IDS line
        guild_ids_str = "[" + ", ".join(str(id) for id in guild_ids) + "]"
        if "DISCORD_GUILD_IDS" in content:
            content = re.sub(r'DISCORD_GUILD_IDS\s*=\s*\[.*?\]', f'DISCORD_GUILD_IDS = {guild_ids_str}', content, flags=re.DOTALL)
        else:
            # Add it after LAVALINK_PASSWORD if not found
            content = re.sub(
                r'(LAVALINK_PASSWORD.*?\n)',
                f'\\1\n# Server IDs for slash command synchronization\nDISCORD_GUILD_IDS = {guild_ids_str}\n',
                content
            )
        
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        messagebox.showinfo("Guild IDs", f"Guild IDs saved! ({len(guild_ids)} server(s))")

    def browse_bot_path(self):
        path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if path:
            self.bot_path_entry.delete(0, "end")
            self.bot_path_entry.insert(0, path)
            self.bot_path = path

    def browse_lavalink_path(self):
        path = filedialog.askopenfilename(filetypes=[("JAR Files", "*.jar")])
        if path:
            self.lavalink_path_entry.delete(0, "end")
            self.lavalink_path_entry.insert(0, path)
            self.lavalink_path = path

    def start_bot(self):
        if self.bot_proc and self.bot_proc.poll() is None:
            messagebox.showinfo("Info", "Bot is already running.")
            return
        python_exec = self.venv_python_entry.get() if hasattr(self, 'venv_python_entry') and self.venv_python_entry.get() else self.venv_python_path or "python"
        def run():
            # Replace bot console with the latest bot.log content
            self.bot_console.delete("1.0", "end")
            import os
            log_path = os.path.join("cache", "logs", "bot.log")
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        log_content = f.read()
                    if log_content.strip():
                        self.bot_console.insert("end", log_content + ("\n" if not log_content.endswith("\n") else ""))
                except Exception as e:
                    self.bot_console.insert("end", f"[Failed to read bot.log: {e}]\n")
            self.bot_console.see("end")
            try:
                self.bot_proc = subprocess.Popen([
                    python_exec, self.bot_path
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                for line in self.bot_proc.stdout:
                    self.bot_console.insert("end", line)
                    self.bot_console.see("end")
                self.bot_proc.stdout.close()
                ret = self.bot_proc.wait()
                if ret != 0:
                    self.bot_console.insert("end", f"[Bot exited with code {ret}]\n")
                    self.bot_console.see("end")
            except Exception as e:
                self.bot_console.insert("end", f"[Bot failed to start: {e}]\n")
                self.bot_console.see("end")
        threading.Thread(target=run, daemon=True).start()

    def stop_bot(self):
        if self.bot_proc and self.bot_proc.poll() is None:
            self.bot_proc.terminate()
            self.bot_console.insert("end", "[Bot stopped]\n")
            self.bot_console.see("end")

    def restart_bot(self):
        self.stop_bot()
        self.start_bot()

    def start_lavalink(self):
        if self.lavalink_proc and self.lavalink_proc.poll() is None:
            messagebox.showinfo("Info", "Lavalink is already running.")
            return
        def run():
            import os
            lavalink_dir = os.path.dirname(self.lavalink_path) or os.getcwd()
            # Check if application.yml exists in the same directory as Lavalink.jar
            app_yml = os.path.join(lavalink_dir, "application.yml")
            cmd = [
                "java", "-jar", self.lavalink_path
            ]
            if os.path.exists(app_yml):
                # Explicitly set config location if file exists
                cmd += [f"--spring.config.location={app_yml}"]
            self.lavalink_console.insert("end", "[Lavalink starting...]\n")
            self.lavalink_console.see("end")
            try:
                self.lavalink_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=lavalink_dir,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                for line in self.lavalink_proc.stdout:
                    self.lavalink_console.insert("end", line)
                    self.lavalink_console.see("end")
                self.lavalink_proc.stdout.close()
                ret = self.lavalink_proc.wait()
                if ret != 0:
                    self.lavalink_console.insert("end", f"[Lavalink exited with code {ret}]\n")
                    self.lavalink_console.see("end")
            except Exception as e:
                self.lavalink_console.insert("end", f"[Lavalink failed to start: {e}]\n")
                self.lavalink_console.see("end")
        threading.Thread(target=run, daemon=True).start()

    def stop_lavalink(self):
        if self.lavalink_proc and self.lavalink_proc.poll() is None:
            self.lavalink_proc.terminate()
            self.lavalink_console.insert("end", "[Lavalink stopped]\n")
            self.lavalink_console.see("end")

    def restart_lavalink(self):
        self.stop_lavalink()
        self.start_lavalink()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = BotLavalinkWrapper()
    app.mainloop()
