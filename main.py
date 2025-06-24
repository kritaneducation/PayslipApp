import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Add socket for internet connectivity check
import socket

# Import update manager components
try:
    from update import check_for_update, AUTO_UPDATE_CHECK_ON_START
    UPDATE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Update package not available - {e}")
    AUTO_UPDATE_CHECK_ON_START = False
    UPDATE_AVAILABLE = False

import threading
from tkinter import filedialog, messagebox, scrolledtext, END, BOTH, RIGHT, X, WORD, LEFT, TclError
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from payslip.cache_manager import PDFCacheManager
from payslip.payslip_processor import PayslipProcessor
from login.auth_manager import AuthManager
import hashlib
import tkinter.simpledialog
import subprocess
import tkinterdnd2  # We'll need to add this to requirements.txt

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

class PDFPayslipOrganizerApp:
    def __init__(self, root, user_data=None):
        # Make root window accept drag and drop
        if not isinstance(root, tkinterdnd2.Tk):
            root = tkinterdnd2.Tk()
            root.title("Payslip Organizer")
            style = ttk.Style(theme="cosmo")
            
        self.root = root
        self.root.title("Payslip Organizer")
        self.user_data = user_data
        self.login_success = user_data is not None
        self.cache_manager = PDFCacheManager(CACHE_DIR)
        self.processor = PayslipProcessor(self.cache_manager, self.log_message, self.update_progress)
        self.is_processing = False
        self.processing_thread = None
        self.setup_ui()
        self.update_memory_usage()
        
        # Register window destroy event to clean up threads
        self.root.protocol("WM_DELETE_WINDOW", self.safe_destroy)

    def check_internet_connection(self):
        """Check if the device has an internet connection."""
        try:
            # Try to connect to a reliable server (Google's DNS)
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

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
        
        # Configure drag and drop for the entry
        self.input_entry.drop_target_register('DND_Files')
        self.input_entry.dnd_bind('<<Drop>>', self._on_drop)
        
        # Add drag and drop hint
        hint_label = ttk.Label(tab, text="💡 Drag and drop PDF files or folders here", 
                             font=("Segoe UI", 10, "italic"), bootstyle=SECONDARY)
        hint_label.pack(pady=(5,0))
        
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
        """Thread-safe logging method."""
        if threading.current_thread() is threading.main_thread():
            self._do_log(message, level)
        else:
            # If called from a background thread, schedule the update on the main thread
            try:
                self.root.after(0, self._do_log, message, level)
            except TclError:
                # Window might be destroyed, just print to console
                print(f"[{level}] {message}")

    def _do_log(self, message, level="Info"):
        """Actual logging implementation, must be called from main thread."""
        # Log to both the main log tab and the organize tab log area, with level and color
        log_entry = f"[{level}] {message}"
        color_map = {
            "Info": "#4dc3ff",      # info blue
            "Success": "#5cb85c",  # success green
            "Warning": "#f0ad4e",  # warning yellow
            "Error": "#d9534f",    # danger red
        }
        tag = level.lower()
        
        try:
            # Check if the window still exists
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                print(f"[{level}] {message}")
                return
                
            # Insert in main log area
            if hasattr(self, 'log_area') and self.log_area.winfo_exists():
                self.log_area.config(state='normal')
                self.log_area.insert(END, f"{log_entry}\n", tag)
                self.log_area.tag_config(tag, foreground=color_map.get(level, "#4dc3ff"))
                self.log_area.config(state='disabled')
                self.log_area.see(END)
            
            # Insert in organize log area
            if hasattr(self, 'organize_log_area') and self.organize_log_area.winfo_exists():
                self.organize_log_area.config(state='normal')
                self.organize_log_area.insert(END, f"{log_entry}\n", tag)
                self.organize_log_area.tag_config(tag, foreground=color_map.get(level, "#4dc3ff"))
                self.organize_log_area.config(state='disabled')
                self.organize_log_area.see(END)
            
            # Store logs for filtering
            if not hasattr(self, 'all_logs'):
                self.all_logs = []
            self.all_logs.append((level, message))
            
            # Only apply filter if the window exists
            try:
                self._apply_log_filter()
                self.root.update_idletasks()
            except TclError:
                pass
                
        except TclError:
            # Window likely destroyed
            print(f"[{level}] {message}")  # Fallback logging to console
        except Exception as e:
            print(f"Logging error: {e} - {message}")  # Fallback logging to console

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
        
        # Version information
        version_frame = ttk.LabelFrame(tab, text="Version", bootstyle=INFO)
        version_frame.pack(fill=X, padx=10, pady=5, ipady=5)
          # Current version
        current_version = getattr(self, 'version', "1.0.0")
        ttk.Label(version_frame, text=f"Current Version: {current_version}", 
                  font=("Segoe UI", 10)).pack(anchor='w', padx=10, pady=(5, 0))
        
        # Update controls
        update_buttons_frame = ttk.Frame(version_frame)
        update_buttons_frame.pack(fill=X, padx=10, pady=5)
        
        def check_for_updates():
            try:
                # Check internet connection first
                if not self.check_internet_connection():
                    self.log_message("Cannot check for updates: No internet connection", "Error")
                    
                    # Keep showing dialog until internet is available or user cancels
                    while not self.check_internet_connection():
                        response = messagebox.askretrycancel("Internet Connection Required", 
                                                          "This application requires an internet connection to check for updates.\n\n"
                                                          "• Please connect to the internet and click 'Retry'\n"
                                                          "• Click 'Cancel' to skip the update check",
                                                          icon="warning")
                        if not response:  # User clicked Cancel
                            return
                    
                    self.log_message("Internet connection detected", "Info")
                
                self.log_message("Checking for updates...", "Info")
                messagebox.showinfo("Update", "Update system not available")
            except ImportError:
                messagebox.showinfo("Update", "Update system not available")
            except Exception as e:
                self.log_message(f"Update error: {str(e)}", "Error")
        
        check_updates_btn = ttk.Button(update_buttons_frame, text="Check for Updates", 
                                     command=check_for_updates, bootstyle=INFO)
        check_updates_btn.pack(side=LEFT, padx=(0, 5))
        
        # Theme switcher (cosmo and superhero)
        theme_frame = ttk.LabelFrame(tab, text="Appearance", bootstyle=INFO) 
        theme_frame.pack(fill=X, padx=10, pady=5, ipady=5)
        
        ttk.Label(theme_frame, text="Theme:", font=("Segoe UI", 10)).pack(anchor='w', padx=10, pady=(5, 0))
        self.theme_var = ttk.StringVar(value="cosmo")
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, values=["cosmo", "superhero"], 
                                   width=15, bootstyle=INFO, state='readonly')
        theme_combo.pack(anchor='w', padx=10, pady=(0, 10))
        
        # Store combobox reference for cleanup during application close
        self.theme_combo = theme_combo
        theme_combo.bind('<<ComboboxSelected>>', self._on_theme_change)
        
        # Keyboard shortcuts info
        shortcuts_frame = ttk.LabelFrame(tab, text="Help", bootstyle=INFO)
        shortcuts_frame.pack(fill=X, padx=10, pady=5, ipady=5)
        
        ttk.Label(shortcuts_frame, text="Shortcuts:", font=("Segoe UI", 10, "bold")).pack(anchor='w', padx=10, pady=(5, 0))
        ttk.Label(shortcuts_frame, text="Start: Ctrl+Enter   Cancel: Esc   Switch Tab: Ctrl+Tab", 
                 font=("Segoe UI", 9), bootstyle=SECONDARY).pack(anchor='w', padx=10, pady=(0, 10))
        
        # Help/About
        ttk.Button(shortcuts_frame, text="Help / About", command=self._show_help, bootstyle=OUTLINE).pack(anchor='w', padx=10, pady=(0, 10))

        # Tesseract OCR status
        tesseract_status, tesseract_ok = self._check_tesseract_status()
        self.tesseract_label = ttk.Label(tab, text=tesseract_status, font=("Segoe UI", 10))
        self.tesseract_label.pack(anchor='w', padx=10, pady=(5, 0))
        
        def install_ocr():
            ocr_path = os.path.join(os.path.dirname(__file__), 'OCR.exe')
            if os.path.exists(ocr_path):
                try:
                    os.startfile(ocr_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to launch OCR installer: {e}")
            else:
                messagebox.showwarning("Missing File", "OCR.exe not found in the application directory.")
        
        ttk.Button(tab, text="Install OCR.exe", command=install_ocr, bootstyle=PRIMARY).pack(anchor='w', padx=10, pady=(0, 5))
        
        def recheck_tesseract():
            status, _ = self._check_tesseract_status()
            self.tesseract_label.config(text=status)
        ttk.Button(tab, text="Re-check Tesseract", command=recheck_tesseract, bootstyle=INFO).pack(anchor='w', padx=10, pady=(0, 10))

    def _on_theme_change(self, event):
        # Check if the application is still running
        try:
            # Check if the root window exists and is not being destroyed
            if hasattr(self, 'root') and self.root.winfo_exists():
                selected = self.theme_var.get()
                style = ttk.Style()
                style.theme_use(selected)
                self.log_message(f"Theme changed to {selected}")
        except TclError:
            # Tcl error is raised when the window is being destroyed
            pass

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
        
        # Schedule UI updates on the main thread
        def update_ui():
            self.start_btn.config(state='normal')
            self.cancel_btn.config(state='disabled')
            self.status_label.config(text="Done" if self.processor.is_processing == False else "Cancelled")
        
        self.root.after(0, update_ui)

    def cancel_processing(self):
        self.processor.is_processing = False
        self.status_label.config(text="⏹ Processing cancelled")
        self.log_message("🛑 Processing cancelled by user")
        self.start_btn.config(state='normal')
        self.cancel_btn.config(state='disabled')
        self.update_progress(0)
        
    def update_progress(self, value):
        """Thread-safe progress update method."""
        if threading.current_thread() is threading.main_thread():
            self._do_update_progress(value)
        else:
            try:
                self.root.after(0, self._do_update_progress, value)
            except TclError:
                # Window might be destroyed
                pass

    def _do_update_progress(self, value):
        """Actual progress update implementation, must be called from main thread."""
        try:
            # Check if the window still exists
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                return
                
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                self.progress_bar['value'] = value
                self.root.update_idletasks()
        except TclError:
            # Window likely destroyed
            pass
        except Exception as e:
            print(f"Progress update error: {e}")
            
    def update_memory_usage(self):
        try:
            # Check if window still exists
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                return
                
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            if hasattr(self, 'memory_label') and self.memory_label.winfo_exists():
                self.memory_label.config(text=f"Memory: {memory_mb:.1f} MB")
                
            # Schedule next update
            try:
                self.root.after(5000, self.update_memory_usage)
            except TclError:
                # Window might be in the process of being destroyed
                pass
        except ImportError:
            if hasattr(self, 'memory_label') and self.memory_label.winfo_exists():
                self.memory_label.config(text="Memory: N/A")
            try:
                self.root.after(5000, self.update_memory_usage)
            except TclError:
                pass
        except TclError:
            # Window likely destroyed
            pass

    def _setup_users_tab(self, tab):
        from login.user_manager import UserManager
        user_manager = UserManager(tab, user_data=self.user_data)
        user_manager.pack(fill="both", expand=True, padx=10, pady=10)

    def _check_tesseract_status(self):
        """Check if Tesseract is installed and return version or prompt for OCR.exe."""
        # First, try system path
        try:
            result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.splitlines()[0]
                return f"Tesseract Installed: {version_line}", True
        except Exception:
            pass
        # Next, try C:\Program Files\Tesseract-OCR\tesseract.exe
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tesseract_path):
            try:
                result = subprocess.run([tesseract_path, "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    version_line = result.stdout.splitlines()[0]
                    return f"Tesseract Installed (Custom Path): {version_line}", True
            except Exception:
                pass
        return "Tesseract not found. Please install OCR.exe.", False

    def _on_drop(self, event):
        """Handle drag and drop of files and folders."""
        try:
            # Get the dropped data
            data = event.data
            
            # Handle Windows paths
            if os.name == 'nt':
                data = data.replace('{', '').replace('}', '')
                paths = [p.strip() for p in data.split('} {')]
            else:
                paths = data.split()
            
            # Use the first valid path
            for path in paths:
                if os.path.exists(path):
                    if os.path.isfile(path) and path.lower().endswith('.pdf'):
                        # If it's a PDF file, use its directory
                        path = os.path.dirname(path)
                    if os.path.isdir(path):
                        self.input_entry.delete(0, END)
                        self.input_entry.insert(0, path)
                        self.log_message(f"Added folder: {path}", "Info")
                        return
            
            self.log_message("Please drop a PDF file or folder", "Warning")
            
        except Exception as e:
            self.log_message(f"Error handling dropped files: {str(e)}", "Error")
            
    def safe_destroy(self):
        """Safely destroy the window by stopping threads and cleaning up bindings"""
        # First, stop any ongoing processing
        if self.is_processing and self.processing_thread:
            self.is_processing = False
            try:
                if self.processing_thread.is_alive():
                    self.processing_thread.join(0.1)  # Give thread a little time to exit
            except:
                pass
                
        # Unbind theme change event which is causing issues
        try:
            if hasattr(self, 'theme_combo') and self.theme_combo.winfo_exists():
                self.theme_combo.unbind('<<ComboboxSelected>>')
        except TclError:
            pass
                
        # Unbind any other event bindings that might cause issues
        try:
            # Find and unbind all combobox bindings to prevent theme change events
            for widget in self.root.winfo_children():
                if isinstance(widget, ttk.Notebook):
                    for tab in widget.winfo_children():
                        for child in tab.winfo_children():
                            if isinstance(child, ttk.Combobox):
                                try:
                                    child.unbind('<<ComboboxSelected>>')
                                except TclError:
                                    pass
        except:
            # If any unbinding fails, just continue with destruction
            pass
            
        # Now destroy the window
        try:
            self.root.destroy()
        except TclError:
            # Window might already be in the process of being destroyed
            pass

if __name__ == "__main__":
    # Define the app version - this should match the version in your remote repository
    CURRENT_VERSION = "1.0.0"
    
    # Create a minimal login window first (will not be visible)
    login_root = ttk.Window("Login", themename="cosmo")
    login_root.withdraw()  # Keep it hidden initially
    
    # Create an authentication manager and check login
    auth_manager = AuthManager(login_root)
    login_result = auth_manager.authenticate_user()
    
    if isinstance(login_result, tuple):
        login_success, user_data = login_result
    else:
        login_success = login_result
        user_data = None
        
    # Close the login window after authentication
    login_root.destroy()
    
    # If login failed, exit application
    if not login_success:
        sys.exit(0)
        
    # Only create the main application window after successful login
    root = ttk.Window("Payslip Organizer", "cosmo", resizable=(True, True))
    app = PDFPayslipOrganizerApp(root, user_data=user_data)  # Pass user data to constructor
    
    # Store current version in app
    app.version = CURRENT_VERSION
    
    # Check internet connection first
    internet_connected = app.check_internet_connection()
      # Force update check after successful login if internet is available
    if UPDATE_AVAILABLE and internet_connected:
        try:
            app.log_message("Checking for updates...", "Info")
            update_available = check_for_update(CURRENT_VERSION, force_check=True)
            if update_available:
                messagebox.showinfo("Update Required", 
                                   "A new version is available and required to continue.\n\n"
                                   "The application will now close. Please install the update before running again.")
                app.safe_destroy()
                sys.exit(0)
            else:
                app.log_message("No updates available. Running latest version.", "Success")
        except Exception as e:
            app.log_message(f"Update check failed: {str(e)}", "Warning")
            response = messagebox.askquestion("Update Check Failed", 
                                            "Unable to verify if you have the latest version.\n\n"
                                            "Do you want to continue anyway?")
            if response != 'yes':
                app.safe_destroy()
                sys.exit(0)
    elif UPDATE_AVAILABLE and not internet_connected:
        # Force internet connection - application cannot run offline
        app.log_message("No internet connection detected. Internet is required to run this application.", "Error")
        
        # Loop until internet is available or user quits
        while not app.check_internet_connection():
            response = messagebox.askretrycancel("Internet Connection Required", 
                                              "This application requires an internet connection to check for updates.\n\n"
                                              "• Please connect to the internet and click 'Retry'\n"
                                              "• Click 'Cancel' to exit the application",
                                              icon="warning")
            if not response:  # User clicked Cancel
                app.safe_destroy()
                sys.exit(0)
                
        # User has connected to internet, now check for updates
        try:
            app.log_message("Internet connection detected. Checking for updates...", "Info")
            update_available = check_for_update(CURRENT_VERSION, force_check=True)
            if update_available:
                messagebox.showinfo("Update Required", 
                                   "A new version is available and required to continue.\n\n"
                                   "The application will now close. Please install the update before running again.")
                app.safe_destroy()
                sys.exit(0)
            else:
                app.log_message("No updates available. Running latest version.", "Success")
        except Exception as e:
            app.log_message(f"Update check failed: {str(e)}", "Warning")
            response = messagebox.askquestion("Update Check Failed", 
                                            "Unable to verify if you have the latest version.\n\n"
                                            "Do you want to continue anyway?")
            if response != 'yes':
                app.safe_destroy()
                sys.exit(0)
    
    # Start the main application
    root.mainloop()

# Note: Update check is already handled in the main block above
# if AUTO_UPDATE_CHECK_ON_START:
#     check_for_update(CURRENT_VERSION)
