import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import threading
from tkinter import filedialog, messagebox, scrolledtext, END, BOTH, RIGHT, X, WORD
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from payslip.cache_manager import PDFCacheManager
from payslip.payslip_processor import PayslipProcessor
from login.auth_manager import AuthManager
import hashlib
import tkinter.simpledialog
from update_manager import check_for_update

APP_VERSION = "1.0.0"  # Change this version as you release updates

# Check for updates before running the app
check_for_update(APP_VERSION)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

class PDFPayslipOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Payslip Organizer")
        self.auth_manager = AuthManager(self.root)
        if not self.auth_manager.authenticate_user():
            self.root.destroy()
            return
        self.cache_manager = PDFCacheManager(CACHE_DIR)
        self.processor = PayslipProcessor(self.cache_manager, self.log_message, self.update_progress)
        self.is_processing = False
        self.processing_thread = None
        self.setup_ui()
        self.update_memory_usage()

    def setup_ui(self):
        style = ttk.Style(theme="cosmo")
        main_frame = ttk.Frame(self.root, padding=(30, 20))
        main_frame.pack(fill=BOTH, expand=True)

        # Header with icon
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(pady=(0, 10))
        # Pixel-style icon (emoji for now)
        icon = ttk.Label(header_frame, text="🗂️", font=("Segoe UI", 28))
        icon.pack(side=LEFT, padx=(0, 10))
        header = ttk.Label(header_frame, text="Payslip Manager by Kreetan", font=("Segoe UI", 20, "bold"), bootstyle=PRIMARY)
        header.pack(side=LEFT)
        subtitle = ttk.Label(main_frame, text="Organize, deduplicate, and merge your payslips easily", font=("Segoe UI", 12), bootstyle=INFO)
        subtitle.pack(pady=(0, 10))

        # Tabs with icons
        self.notebook = ttk.Notebook(main_frame, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=True, pady=(10, 0))
        self.notebook.add(ttk.Frame(self.notebook), text="🗂️ Organize")
        self.notebook.add(ttk.Frame(self.notebook), text="📄 Log")
        self.notebook.add(ttk.Frame(self.notebook), text="⚙️ Settings")
        self.notebook.add(ttk.Frame(self.notebook), text="👤 Users")
        organize_tab = self.notebook.winfo_children()[0]
        log_tab = self.notebook.winfo_children()[1]
        settings_tab = self.notebook.winfo_children()[2]
        users_tab = self.notebook.winfo_children()[3]
        self._setup_organize_tab(organize_tab)
        self._setup_log_tab(log_tab)
        self._setup_settings_tab(settings_tab)
        self._setup_users_tab(users_tab)

        # Footer
        footer = ttk.Frame(main_frame)
        footer.pack(fill=X, pady=(0, 5))
        self.memory_label = ttk.Label(footer, text="Memory: 0 MB", font=("Segoe UI", 9), bootstyle=SECONDARY)
        self.memory_label.pack(side=RIGHT, padx=5)
        ttk.Label(footer, text="© 2025 Kritan Rimal", font=("Segoe UI", 9), bootstyle=SECONDARY).pack(side=LEFT, padx=5)

    def _setup_organize_tab(self, tab):
        # Payslips folder selector
        input_frame = ttk.Frame(tab)
        input_frame.pack(fill=X, pady=(10, 0), padx=30)
        ttk.Label(input_frame, text="Payslips Folder:", font=("Segoe UI", 11)).pack(side=LEFT, padx=(0, 8))
        self.input_entry = ttk.Entry(input_frame, font=('Segoe UI', 11))
        self.input_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(input_frame, text="Browse", command=self.select_input_dir, bootstyle=OUTLINE).pack(side=LEFT, padx=5)
        # Recent folders dropdown
        self.recent_folders = []
        self.recent_var = ttk.StringVar()
        self.recent_combo = ttk.Combobox(input_frame, textvariable=self.recent_var, values=self.recent_folders, width=18, bootstyle=INFO)
        self.recent_combo.pack(side=LEFT, padx=5)
        self.recent_combo.bind('<<ComboboxSelected>>', self._on_recent_selected)

        # Progress bar
        progress_frame = ttk.Frame(tab)
        progress_frame.pack(fill=X, pady=(10, 0), padx=30)
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate', bootstyle=SUCCESS)
        self.progress_bar.pack(fill=X, padx=0, pady=0, side=LEFT, expand=True)

        # Logs section
        log_frame = ttk.Frame(tab)
        log_frame.pack(fill=BOTH, expand=True, pady=(10, 0), padx=30)
        ttk.Label(log_frame, text="Log:", font=("Segoe UI", 10, "bold"), bootstyle=SECONDARY).pack(anchor='w', pady=(0, 2))
        current_theme = ttk.Style().theme_use()
        if current_theme == 'cosmo':
            organize_log_bg = self.root.cget('background')
            organize_log_fg = '#212529'
        else:
            organize_log_bg = '#23272e'
            organize_log_fg = '#e1e1e1'
        self.organize_log_area = scrolledtext.ScrolledText(log_frame, wrap=WORD, state='disabled', font=('Consolas', 10), height=8, bg=organize_log_bg, fg=organize_log_fg)
        self.organize_log_area.pack(fill=BOTH, expand=True)

        # Status label for organize tab
        self.status_label = ttk.Label(tab, text="Ready", font=("Segoe UI", 10, "italic"), bootstyle=INFO)
        self.status_label.pack(fill=X, padx=30, pady=(0, 2))

        # Start and Cancel buttons at the bottom
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill=X, pady=(10, 20), padx=30, anchor='s')
        self.start_btn = ttk.Button(button_frame, text="🚀 Start Processing", command=self.start_processing, bootstyle=SUCCESS, width=18)
        self.start_btn.pack(side=LEFT, padx=5)
        self.cancel_btn = ttk.Button(button_frame, text="⏹ Cancel", command=self.cancel_processing, state='disabled', bootstyle=DANGER, width=12)
        self.cancel_btn.pack(side=LEFT, padx=5)

    def _on_recent_selected(self, event):
        folder = self.recent_var.get()
        if folder:
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, folder)

    def _on_drop_folder(self, event):
        # Only handle first folder
        if event.data:
            folder = event.data.split()[0]
            if os.path.isdir(folder):
                self.input_entry.delete(0, END)
                self.input_entry.insert(0, folder)

    def _setup_log_tab(self, tab):
        log_label = ttk.Label(tab, text="Log:", font=("Segoe UI", 11, "bold"), bootstyle=SECONDARY)
        log_label.pack(anchor='w', padx=10, pady=(10, 0))
        # Log filter
        filter_frame = ttk.Frame(tab)
        filter_frame.pack(fill=X, padx=10, pady=(0, 5))
        ttk.Label(filter_frame, text="Filter:", font=("Segoe UI", 10)).pack(side=LEFT)
        self.log_filter_var = ttk.StringVar(value="All")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.log_filter_var, values=["All", "Info", "Warning", "Error"], width=10, bootstyle=INFO)
        filter_combo.pack(side=LEFT, padx=5)
        filter_combo.bind('<<ComboboxSelected>>', self._apply_log_filter)
        # Log area with theme-adaptive colors
        current_theme = ttk.Style().theme_use()
        if current_theme == 'cosmo':
            log_bg = self.root.cget('background')
            log_fg = '#212529'
        else:
            log_bg = '#23272e'
            log_fg = '#e1e1e1'
        self.log_area = scrolledtext.ScrolledText(tab, wrap=WORD, state='disabled', font=('Consolas', 10), height=18, bg=log_bg, fg=log_fg)
        self.log_area.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        # Snackbar notification (placeholder)
        self.snackbar = ttk.Label(tab, text="", font=("Segoe UI", 10), bootstyle=SUCCESS)
        self.snackbar.pack(anchor='s', pady=2)

    def log_message(self, message, level="Info"):
        # Log to both the main log tab and the organize tab log area, with level and color
        log_entry = f"[{level}] {message}"
        color_map = {
            "Info": "#4dc3ff",      # info blue
            "Success": "#5cb85c",  # success green
            "Warning": "#f0ad4e",  # warning yellow
            "Error": "#d9534f",    # danger red
        }
        tag = level.lower()
        # Insert in main log area
        self.log_area.config(state='normal')
        self.log_area.insert(END, f"{log_entry}\n", tag)
        self.log_area.tag_config(tag, foreground=color_map.get(level, "#4dc3ff"))
        self.log_area.config(state='disabled')
        self.log_area.see(END)
        # Insert in organize log area
        self.organize_log_area.config(state='normal')
        self.organize_log_area.insert(END, f"{log_entry}\n", tag)
        self.organize_log_area.tag_config(tag, foreground=color_map.get(level, "#4dc3ff"))
        self.organize_log_area.config(state='disabled')
        self.organize_log_area.see(END)
        self.root.update_idletasks()
        # Store logs for filtering
        if not hasattr(self, 'all_logs'):
            self.all_logs = []
        self.all_logs.append((level, message))
        self._apply_log_filter()

    def _apply_log_filter(self, *_):
        # Filter logs in the log tab based on the selected filter
        if not hasattr(self, 'all_logs'):
            return
        selected = self.log_filter_var.get()
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, END)
        color_map = {
            "Info": "#4dc3ff",
            "Success": "#5cb85c",
            "Warning": "#f0ad4e",
            "Error": "#d9534f",
        }
        for level, msg in self.all_logs:
            if selected == "All" or level == selected:
                tag = level.lower()
                self.log_area.insert(END, f"[{level}] {msg}\n", tag)
                self.log_area.tag_config(tag, foreground=color_map.get(level, "#4dc3ff"))
        self.log_area.config(state='disabled')
        self.log_area.see(END)

    def _setup_settings_tab(self, tab):
        settings_label = ttk.Label(tab, text="Settings", font=("Segoe UI", 13, "bold"), bootstyle=PRIMARY)
        settings_label.pack(anchor='w', padx=10, pady=(10, 5))
        # Theme switcher (cosmo and superhero)
        ttk.Label(tab, text="Theme:", font=("Segoe UI", 10)).pack(anchor='w', padx=10, pady=(5, 0))
        self.theme_var = ttk.StringVar(value="cosmo")
        theme_combo = ttk.Combobox(tab, textvariable=self.theme_var, values=["cosmo", "superhero"], width=15, bootstyle=INFO, state='readonly')
        theme_combo.pack(anchor='w', padx=10, pady=(0, 10))
        theme_combo.bind('<<ComboboxSelected>>', self._on_theme_change)
        # Keyboard shortcuts info
        ttk.Label(tab, text="Shortcuts:", font=("Segoe UI", 10, "bold")).pack(anchor='w', padx=10, pady=(10, 0))
        ttk.Label(tab, text="Start: Ctrl+Enter   Cancel: Esc   Switch Tab: Ctrl+Tab", font=("Segoe UI", 9), bootstyle=SECONDARY).pack(anchor='w', padx=10, pady=(0, 10))
        # Help/About
        ttk.Button(tab, text="Help / About", command=self._show_help, bootstyle=OUTLINE).pack(anchor='w', padx=10, pady=10)

    def _on_theme_change(self, event):
        selected = self.theme_var.get()
        style = ttk.Style()
        style.theme_use(selected)
        self.log_message(f"Theme changed to {selected}")

    def _show_help(self):
        messagebox.showinfo("About", "Payslip Manager by Kreetan\nVersion 1.0\n© 2025 Kreetan Rimal\n\n- Drag & drop a folder to Organize tab\n- Use keyboard shortcuts for speed\n- Filter log messages in Log tab\n- More features coming soon!")

    def select_input_dir(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, dir_path)

    def start_processing(self):
        if not self.is_processing:
            input_dir = self.input_entry.get().strip()
            if not input_dir or not os.path.isdir(input_dir):
                messagebox.showerror("Error", "Please select a valid input directory")
                return
            self.is_processing = True
            self.start_btn.config(state='disabled')
            self.cancel_btn.config(state='normal')
            self.log_area.config(state='normal')
            self.log_area.delete(1.0, END)
            self.log_area.config(state='disabled')
            self.status_label.config(text="Processing...")
            output_file = os.path.join(input_dir, "output", "arranged_payslips.pdf")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            self.processing_thread = threading.Thread(target=self._process_thread, args=(input_dir, output_file))
            self.processing_thread.daemon = True
            self.processing_thread.start()

    def _process_thread(self, input_dir, output_file):
        self.processor.is_processing = True
        self.processor.process_payslips(input_dir, output_file)
        self.is_processing = False
        self.start_btn.config(state='normal')
        self.cancel_btn.config(state='disabled')
        self.status_label.config(text="Done" if self.processor.is_processing == False else "Cancelled")

    def cancel_processing(self):
        self.processor.is_processing = False
        self.status_label.config(text="⏹ Processing cancelled")
        self.log_message("🛑 Processing cancelled by user")
        self.start_btn.config(state='normal')
        self.cancel_btn.config(state='disabled')
        self.update_progress(0)

    def update_progress(self, value):
        self.progress_bar['value'] = value
        self.root.update_idletasks()

    def update_memory_usage(self):
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            self.memory_label.config(text=f"Memory: {memory_mb:.1f} MB")
        except ImportError:
            self.memory_label.config(text="Memory: N/A")
        self.root.after(5000, self.update_memory_usage)

    def _setup_users_tab(self, tab):
        from login.user_manager import UserManager
        user_manager = UserManager(tab)
        user_manager.pack(fill="both", expand=True, padx=10, pady=10)

if __name__ == "__main__":
    root = ttk.Window("Payslip Organizer", "cosmo", resizable=(True, True))
    root.withdraw()  # Hide main window until login
    app = PDFPayslipOrganizerApp(root)
    if hasattr(app, 'auth_manager') and not app.auth_manager.login_success:
        root.destroy()
    else:
        root.deiconify()  # Show main window after successful login
        root.mainloop()
