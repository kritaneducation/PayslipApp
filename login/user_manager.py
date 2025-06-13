import tkinter as tk
from tkinter import messagebox

class UserManager(tk.Frame):
    """A user management UI component for changing username, password, and email."""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(bg="#18191c")
        tk.Label(self, text="User Settings", font=("Segoe UI", 14, "bold"), fg="white", bg="#18191c").pack(pady=(10, 5))
        # Username
        user_frame = tk.Frame(self, bg="#18191c")
        user_frame.pack(fill="x", padx=20, pady=(10, 5))
        tk.Label(user_frame, text="Username:", font=("Segoe UI", 11), fg="#b0b0b0", bg="#18191c").pack(side="left")
        self.username_var = tk.StringVar(value="admin")
        self.username_entry = tk.Entry(user_frame, textvariable=self.username_var, font=("Segoe UI", 11), bg="#23272e", fg="#4dc3ff", insertbackground="#4dc3ff")
        self.username_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        # Email
        email_frame = tk.Frame(self, bg="#18191c")
        email_frame.pack(fill="x", padx=20, pady=(5, 5))
        tk.Label(email_frame, text="Email:", font=("Segoe UI", 11), fg="#b0b0b0", bg="#18191c").pack(side="left")
        self.email_var = tk.StringVar(value="admin@example.com")
        self.email_entry = tk.Entry(email_frame, textvariable=self.email_var, font=("Segoe UI", 11), bg="#23272e", fg="#4dc3ff", insertbackground="#4dc3ff")
        self.email_entry.pack(side="left", fill="x", expand=True, padx=(32, 0))
        # Password
        pass_frame = tk.Frame(self, bg="#18191c")
        pass_frame.pack(fill="x", padx=20, pady=(5, 10))
        tk.Label(pass_frame, text="New Password:", font=("Segoe UI", 11), fg="#b0b0b0", bg="#18191c").pack(side="left")
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(pass_frame, textvariable=self.password_var, font=("Segoe UI", 11), bg="#23272e", fg="#4dc3ff", insertbackground="#4dc3ff", show="*")
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        # Eye icon button to show/hide password
        self.show_password = False
        self.eye_button = tk.Button(pass_frame, text="\U0001F441", font=("Segoe UI", 11), bg="#23272e", fg="#4dc3ff", relief="flat", bd=0, command=self.toggle_password)
        self.eye_button.pack(side="left", padx=(4, 0))
        # Save button
        tk.Button(self, text="Save Changes", command=self.save_changes, bg="#5cb85c", fg="white", relief="flat", font=("Segoe UI", 11, "bold")).pack(pady=(10, 10))

    def save_changes(self):
        username = self.username_var.get().strip()
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()
        if not username or not email:
            messagebox.showerror("Error", "Username and email cannot be empty.")
            return
        # Password is optional (only change if provided)
        # Here you would update the user in your real database/config
        messagebox.showinfo("Saved", "User settings updated successfully! (Not persistent in demo)")
        self.password_var.set("")

    def toggle_password(self):
        self.show_password = not self.show_password
        if self.show_password:
            self.password_entry.config(show="")
            self.eye_button.config(text="\U0001F441\U0001F5E8")  # eye with speech bubble
        else:
            self.password_entry.config(show="*")
            self.eye_button.config(text="\U0001F441")  # eye only
