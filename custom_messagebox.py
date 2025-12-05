# ui/custom_messagebox.py
import tkinter as tk
from tkinter import messagebox as tk_messagebox

import customtkinter as ctk


class CTkMessageBox(ctk.CTkToplevel):
    """
    Fenêtre popup custom pour remplacer les messagebox classiques.
    level: 'info' | 'warning' | 'error' | 'question'
    buttons: liste de libellés de boutons ("OK", "Oui", "Non", ...)
    """
    def __init__(self, parent, title, message, level="info", buttons=("OK",)):
        if parent is None:
            parent = tk._default_root

        super().__init__(parent)
        self.result = None

        self.title(title)
        self.geometry("480x260")
        self.resizable(False, False)
        self.transient(parent)

        # couleurs selon le type
        palette = {
            "info": {
                "header": "#1565C0",
                "bg": "#E3F2FD",
                "accent": "#1976D2",
                "icon": "ℹ"
            },
            "warning": {
                "header": "#EF6C00",
                "bg": "#FFF3E0",
                "accent": "#FB8C00",
                "icon": "⚠"
            },
            "error": {
                "header": "#C62828",
                "bg": "#FFEBEE",
                "accent": "#E53935",
                "icon": "⛔"
            },
            "question": {
                "header": "#00695C",
                "bg": "#E0F2F1",
                "accent": "#00897B",
                "icon": "❓"
            },
        }
        colors = palette.get(level, palette["info"])

        try:
            self.configure(fg_color=colors["bg"])
        except Exception:
            pass

        main = ctk.CTkFrame(self, fg_color=colors["bg"], corner_radius=12)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.grid_columnconfigure(1, weight=1)

        # Bande de titre
        header = ctk.CTkFrame(main, fg_color=colors["header"], corner_radius=10)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=2, pady=(2, 8))
        header.grid_columnconfigure(1, weight=1)

        icon_label = ctk.CTkLabel(
            header,
            text=colors["icon"],
            text_color="white",
            font=ctk.CTkFont(size=24, weight="bold"),
            width=40,
        )
        icon_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")

        title_label = ctk.CTkLabel(
            header,
            text=title,
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(row=0, column=1, padx=5, pady=8, sticky="w")

        # Message
        msg_frame = ctk.CTkFrame(main, fg_color=colors["bg"])
        msg_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=4, pady=(0, 8))
        msg_frame.grid_columnconfigure(0, weight=1)

        msg_label = ctk.CTkLabel(
            msg_frame,
            text=message,
            text_color="#000000",
            wraplength=420,
            justify="left",
            font=ctk.CTkFont(size=13),
        )
        msg_label.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        # Boutons
        btn_frame = ctk.CTkFrame(main, fg_color=colors["bg"])
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(4, 2))
        for i, btxt in enumerate(buttons):
            if btxt.lower() in ("ok", "oui", "yes"):
                fg = colors["accent"]
                hov = colors["header"]
            else:
                fg = "#9E9E9E"
                hov = "#757575"

            btn = ctk.CTkButton(
                btn_frame,
                text=btxt,
                fg_color=fg,
                hover_color=hov,
                text_color="white",
                width=110,
                command=lambda v=btxt: self._on_button(v)
            )
            btn.grid(row=0, column=i, padx=6, pady=4)

        # centrer sur le parent
        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + parent.winfo_width() // 2 - self.winfo_width() // 2
            y = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self.grab_set()
        self.focus_force()
        self.bind("<Escape>", lambda e: self._on_button("CANCEL"))
        self.bind("<Return>", lambda e: self._on_button(buttons[0] if buttons else "OK"))

    def _on_button(self, value):
        txt = value.lower()
        if txt in ("ok", "oui", "yes"):
            self.result = True
        elif txt in ("non", "no", "cancel", "annuler"):
            self.result = False
        else:
            self.result = value
        self.destroy()


# ----------------------------------------------------------------------
# Fonctions de remplacement pour tkinter.messagebox
# ----------------------------------------------------------------------

def _get_parent(options):
    parent = options.get("parent")
    if parent is None:
        parent = tk._default_root
    return parent


def _show_info(title, message, **options):
    parent = _get_parent(options)
    box = CTkMessageBox(parent, title, message, level="info", buttons=("OK",))
    parent.wait_window(box)
    return "ok"


def _show_warning(title, message, **options):
    parent = _get_parent(options)
    box = CTkMessageBox(parent, title, message, level="warning", buttons=("OK",))
    parent.wait_window(box)
    return "ok"


def _show_error(title, message, **options):
    parent = _get_parent(options)
    box = CTkMessageBox(parent, title, message, level="error", buttons=("OK",))
    parent.wait_window(box)
    return "ok"


def _ask_yesno(title, message, **options):
    parent = _get_parent(options)
    box = CTkMessageBox(parent, title, message, level="question", buttons=("Oui", "Non"))
    parent.wait_window(box)
    return bool(box.result)


# Patch global de tkinter.messagebox
tk_messagebox.showinfo = _show_info
tk_messagebox.showwarning = _show_warning
tk_messagebox.showerror = _show_error
tk_messagebox.askyesno = _ask_yesno
