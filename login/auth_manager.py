import hashlib
import tkinter as tk
import tkinter.simpledialog
from tkinter import messagebox

class AuthManager:
    """Handles user authentication with a proper login form."""
    def __init__(self, root):
        self.root = root
        # In a real app, load users from a secure database or config
        self.USERNAME = "admin"
        self.PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()
        self.login_success = False

    def authenticate_user(self):
        self.login_success = False
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Login")
        self.login_window.minsize(340, 340)
        self.login_window.geometry("480x480")
        self.login_window.resizable(True, True)
        self.login_window.grab_set()
        self.login_window.protocol("WM_DELETE_WINDOW", self._on_close)
        # Remove gradient background, just use a plain window
        # Centered dark card (responsive)
        self.card = tk.Frame(self.login_window, bg="#18191c")
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        # Title
        tk.Label(self.card, text="LOGIN", font=("Segoe UI", 22, "bold"), fg="white", bg="#18191c").pack(pady=(18, 2))
        tk.Label(self.card, text="Please enter your login and password!", font=("Segoe UI", 11), fg="#b0b0b0", bg="#18191c").pack(pady=(0, 12))
        # Username
        self.username_entry = tk.Entry(self.card, font=("Segoe UI", 12), fg="#4dc3ff", bg="#23272e", insertbackground="#4dc3ff", relief="flat", highlightthickness=2, highlightbackground="#4dc3ff", highlightcolor="#4dc3ff")
        self.username_entry.pack(pady=6, ipady=6, ipadx=8, fill="x", padx=32)
        self.username_entry.insert(0, "Username")
        self.username_entry.bind('<FocusIn>', lambda e: self._clear_placeholder(self.username_entry, "Username"))
        self.username_entry.bind('<FocusOut>', lambda e: self._restore_placeholder(self.username_entry, "Username"))
        # Password
        self.password_entry = tk.Entry(self.card, font=("Segoe UI", 12), fg="#4dc3ff", bg="#23272e", insertbackground="#4dc3ff", relief="flat", highlightthickness=2, highlightbackground="#4dc3ff", highlightcolor="#4dc3ff")
        self.password_entry.pack(pady=6, ipady=6, ipadx=8, fill="x", padx=32)
        self.password_entry.insert(0, "Password")
        self.password_entry.bind('<FocusIn>', lambda e: self._clear_placeholder(self.password_entry, "Password", is_password=True))
        self.password_entry.bind('<FocusOut>', lambda e: self._restore_placeholder(self.password_entry, "Password", is_password=True))
        # Forgot password
        forgot = tk.Label(self.card, text="Forgot password?", font=("Segoe UI", 10, "underline"), fg="#4dc3ff", bg="#18191c", cursor="hand2")
        forgot.pack(pady=(4, 8))
        forgot.bind('<Button-1>', lambda e: self._forgot_password())
        # Error label
        self.error_label = tk.Label(self.card, text="", fg="#d9534f", bg="#18191c", font=("Segoe UI", 9))
        self.error_label.pack(pady=(0, 4))
        # Login button
        login_btn = tk.Button(self.card, text="Login", font=("Segoe UI", 12, "bold"), fg="#fff", bg="#18191c", activebackground="#23272e", activeforeground="#4dc3ff", relief="flat", highlightthickness=2, highlightbackground="#5cb85c", highlightcolor="#5cb85c", command=self._try_login)
        login_btn.pack(pady=(4, 12), ipadx=18, ipady=4)
        # Social icons (placeholders)
        icon_frame = tk.Frame(self.card, bg="#18191c")
        icon_frame.pack(pady=(8, 0))
        for icon in ["\u2605", "\u263A", "\u25CF", "\u25CB"]:
            tk.Label(icon_frame, text=icon, font=("Segoe UI", 16), fg="#4dc3ff", bg="#18191c").pack(side="left", padx=10)
        self.username_entry.focus_set()
        self.login_window.bind('<Return>', lambda e: self._try_login())
        self.login_window.wait_window()
        return self.login_success

    def _clear_placeholder(self, entry, placeholder, is_password=False):
        if entry.get() == placeholder:
            entry.delete(0, 'end')
            if is_password:
                entry.config(show='*')

    def _restore_placeholder(self, entry, placeholder, is_password=False):
        if not entry.get():
            entry.insert(0, placeholder)
            if is_password:
                entry.config(show='')

    def _forgot_password(self):
        messagebox.showinfo("Forgot Password", "Please contact support to reset your password.")

    def _try_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if username == self.USERNAME and hashlib.sha256(password.encode()).hexdigest() == self.PASSWORD_HASH:
            self.login_success = True
            if self.login_window.winfo_exists():
                self.login_window.destroy()
        else:
            self.error_label.config(text="Invalid username or password.")
            self.password_entry.delete(0, 'end')

    def _on_close(self):
        self.login_success = False
        if self.login_window.winfo_exists():
            self.login_window.destroy()
