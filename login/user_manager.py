import tkinter as tk
from tkinter import messagebox
import requests

class UserManager(tk.Frame):
    """A user management UI component for showing user info, licenses, and logout."""
    def __init__(self, parent, user_data=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.user_data = user_data or {}
        tk.Label(self, text="User Profile", font=("Segoe UI", 14, "bold")).pack(pady=(10, 5))
        # Profile info
        profile = self.user_data.get("profile", {})
        user = self.user_data.get("user", {})
        session = self.user_data.get("session", {})
        licenses = self.user_data.get("licenses", [])
        # Name
        tk.Label(self, text=f"Name: {profile.get('full_name', '-')}", font=("Segoe UI", 11)).pack(anchor='w', padx=20, pady=(5, 0))
        # Email
        tk.Label(self, text=f"Email: {user.get('email', '-')}", font=("Segoe UI", 11)).pack(anchor='w', padx=20, pady=(5, 0))
        # Role
        tk.Label(self, text=f"Role: {profile.get('role', '-')}", font=("Segoe UI", 11)).pack(anchor='w', padx=20, pady=(5, 0))
        # Licenses
        tk.Label(self, text="Licenses:", font=("Segoe UI", 11, "bold")).pack(anchor='w', padx=20, pady=(10, 0))
        if licenses:
            for lic in licenses:
                tk.Label(self, text=str(lic), font=("Segoe UI", 10)).pack(anchor='w', padx=40)
        else:
            tk.Label(self, text="No licenses found.", font=("Segoe UI", 10, "italic")).pack(anchor='w', padx=40)
        # Logout button
        tk.Button(self, text="Logout", command=self.logout, bg="#d9534f", fg="white", relief="flat", font=("Segoe UI", 11, "bold")).pack(pady=(20, 10))
        self.session = session

    def logout(self):
        access_token = self.session.get("access_token")
        if not access_token:
            tk.messagebox.showerror("Logout Failed", "No access token found.")
            return
        try:
            response = requests.post(
                "https://kritanpayslipmanager.vercel.app/api/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            if response.status_code == 200:
                tk.messagebox.showinfo("Logged Out", "You have been logged out.")
                self.master.master.auth_manager.login_success = False
                root = self.master.master.root
                try:
                    if root.winfo_exists():
                        root.destroy()
                except Exception:
                    pass
            else:
                tk.messagebox.showerror("Logout Failed", response.json().get("message", "Unknown error."))
        except Exception as e:
            tk.messagebox.showerror("Logout Failed", str(e))
