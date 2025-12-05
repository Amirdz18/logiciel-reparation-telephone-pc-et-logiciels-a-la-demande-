import os
import sys
import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
from datetime import datetime

import customtkinter as ctk

from database import Database
from .dialogs import CreditClientDialog, ManualProductDialog, AchatDialog, VenteDialog
from .pages.depot import DepotPage
from .pages.historique import HistoriquePage
from .pages.caisses_historique import CaisseHistoriquePage
from .pages.occasion import OccasionPage
from . import custom_messagebox  # si tu l'utilises pour tes popups perso


class Application:
    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.db = Database()

        # ---------- FICHIER DE PARAMÈTRES ----------
        self.base_dir = Path(__file__).resolve().parents[1]

        if getattr(sys, "frozen", False):
            # Application packagée (.exe)
            if os.name == "nt":
                base_data = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
            else:
                base_data = Path.home()
            self.data_dir = base_data / "pyramide" / "data"
        else:
            # Mode développement
            self.data_dir = self.base_dir / "data"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.data_dir / "settings.json"
        # -------------------------------------------

        # Valeurs par défaut
        self.store_name = "Red"
        self.store_tel = ""
        self.store_logo_path = None  # chemin complet vers un logo optionnel
        self.admin_password = ""     # mot de passe admin (texte simple)
        self.admin_authenticated = False  # True après login réussi, pour la session

        # Charger les paramètres sauvés (si le fichier existe)
        self._load_settings()

        self.root = ctk.CTk()
        self.root.title("Red - Gestion du magasin de téléphonie")
        self.root.geometry("1100x700")
        try:
            self.root.state("zoomed")
        except Exception:
            pass

        self.logo_image = None
        self.caisse_selectionnee_id = None

        self.vente_panier = []
        self.vente_selected_index = None
        self.vente_total = 0.0

        self.reception_ticket_id = None

        self._build_header()
        self._build_pages()
        self.show_accueil()

    # PARAMÈTRES (fichier JSON) -------------------------------

    def _load_settings(self):
        """Charge store_name, store_tel, store_logo_path, admin_password depuis settings.json."""
        if not self.settings_file.exists():
            return
        try:
            with self.settings_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.store_name = data.get("store_name", self.store_name)
        self.store_tel = data.get("store_tel", self.store_tel)
        self.store_logo_path = data.get("store_logo_path") or None
        self.admin_password = data.get("admin_password", self.admin_password)
        # à chaque démarrage, l'admin doit se reconnecter
        self.admin_authenticated = False

    def _save_settings(self):
        """Sauvegarde store_name, store_tel, store_logo_path, admin_password dans settings.json."""
        data = {
            "store_name": self.store_name,
            "store_tel": self.store_tel,
            "store_logo_path": self.store_logo_path,
            "admin_password": self.admin_password,
        }
        try:
            with self.settings_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror(
                "Paramètres",
                f"Erreur lors de la sauvegarde des paramètres : {e}",
                parent=self.root
            )

    # HEADER ---------------------------------------------------

    def _build_header(self):
        header = ctk.CTkFrame(self.root, fg_color="#243b67", height=80)
        header.pack(fill="x")
        header.grid_columnconfigure(0, weight=0)
        header.grid_columnconfigure(1, weight=1)

        # logo (label conservé en attribut pour mise à jour)
        self.header_logo_label = ctk.CTkLabel(
            header,
            text="LOGO",
            text_color="white",
            fg_color="#243b67",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=80,
        )
        self.header_logo_label.grid(row=0, column=0, padx=15, pady=10)

        self.header_title_label = ctk.CTkLabel(
            header,
            text=self.store_name,
            text_color="white",
            fg_color="#243b67",
            font=ctk.CTkFont(size=26, weight="bold"),
        )
        self.header_title_label.grid(row=0, column=1, sticky="w", pady=(10, 0))

        self.header_subtitle_label = ctk.CTkLabel(
            header,
            text="Dépôt téléphones, réception téléphones, vente au comptoir, créances, caisses, produits",
            text_color="#d0d8ff",
            fg_color="#243b67",
            font=ctk.CTkFont(size=11),
        )
        self.header_subtitle_label.grid(row=0, column=1, sticky="sw", pady=(0, 10), padx=(0, 10))

        self._update_header()

    def _update_header(self):
        """Met à jour nom, téléphone et logo dans le header à partir des attributs."""
        nom = self.store_name or "Red"
        tel = (self.store_tel or "").strip()

        base_subtitle = "Dépôt téléphones, réception téléphones, vente au comptoir, créances, caisses, produits"

        self.header_title_label.configure(text=nom)

        if tel:
            self.header_subtitle_label.configure(text=f"{base_subtitle}  |  Tél : {tel}")
        else:
            self.header_subtitle_label.configure(text=base_subtitle)

        # logo
        default_logo = self.base_dir / "logo.png"
        logo_path = None
        if self.store_logo_path and os.path.exists(self.store_logo_path):
            logo_path = self.store_logo_path
        elif default_logo.exists():
            logo_path = str(default_logo)

        if logo_path:
            try:
                self.logo_image = tk.PhotoImage(file=logo_path)
                self.header_logo_label.configure(image=self.logo_image, text="")
            except Exception:
                self.header_logo_label.configure(image=None, text="LOGO")
        else:
            self.header_logo_label.configure(image=None, text="LOGO")

    # GESTION ADMIN --------------------------------------------

    def demander_admin(self) -> bool:
        """
        Demande le mot de passe admin si nécessaire.
        Retourne True si l'utilisateur est autorisé, False sinon.
        """
        if not (self.admin_password or "").strip():
            messagebox.showwarning(
                "Administrateur",
                "Aucun mot de passe administrateur n'est défini.\n"
                "Définissez-le dans le menu PARAMÈTRES.",
                parent=self.root
            )
            return False

        if self.admin_authenticated:
            return True

        pwd = simpledialog.askstring(
            "Administrateur",
            "Mot de passe administrateur :",
            parent=self.root,
            show="*"
        )
        if pwd is None:
            return False
        if pwd != self.admin_password:
            messagebox.showerror("Administrateur", "Mot de passe incorrect.", parent=self.root)
            return False

        self.admin_authenticated = True
        return True

    # PAGES ----------------------------------------------------

    def _build_pages(self):
        self.container = ctk.CTkFrame(self.root, fg_color="#e6ecff")
        self.container.pack(fill="both", expand=True)

        # Accueil
        self.page_accueil = ctk.CTkFrame(self.container, fg_color="#e6ecff")

        # Dépôt : page séparée
        self.page_depot = DepotPage(self.container, self)

        # Historique téléphones / clients : page séparée
        self.page_historique = HistoriquePage(self.container, self)

        # CAISSES : page avec en-tête + page CaisseHistorique à l'intérieur
        self.page_caisses = ctk.CTkFrame(self.container, fg_color="white")
        self.page_caisse_histo = None  # créé dans _build_page_caisses

        # Paramètres : page gérée ici
        self.page_parametres = ctk.CTkFrame(self.container, fg_color="white")

        # Autres pages gérées directement dans Application
        self.page_reception = ctk.CTkFrame(self.container, fg_color="white")
        self.page_creances = ctk.CTkFrame(self.container, fg_color="white")
        self.page_produits = ctk.CTkFrame(self.container, fg_color="white")
        self.page_vente = ctk.CTkFrame(self.container, fg_color="white")

        # NOUVELLE PAGE : achats de téléphones d'occasion
        self.page_occasion = OccasionPage(self.container, self)

        self._build_page_accueil()
        self._build_page_parametres()
        self._build_page_reception()
        self._build_page_creances()
        self._build_page_caisses()
        self._build_page_produits()
        self._build_page_vente()

    def _forget_all_pages(self):
        for p in [
            self.page_accueil,
            self.page_depot,
            self.page_historique,
            self.page_caisses,
            self.page_parametres,
            self.page_reception,
            self.page_creances,
            self.page_produits,
            self.page_vente,
            self.page_occasion,
        ]:
            p.pack_forget()

    def show_accueil(self):
        self._forget_all_pages()
        self.page_accueil.pack(fill="both", expand=True)

    def show_depot(self):
        self._forget_all_pages()
        self.page_depot.pack(fill="both", expand=True)
        self.page_depot.depot_charger_tickets()

    def show_historique(self):
        self._forget_all_pages()
        self.page_historique.pack(fill="both", expand=True)
        self.page_historique.charger_historique()

    def show_caisse_historique(self):
        self.show_caisses()

    def show_parametres(self):
        self._forget_all_pages()
        self.page_parametres.pack(fill="both", expand=True)
        self._param_charger_ui()

    def show_reception(self):
        self._forget_all_pages()
        self.page_reception.pack(fill="both", expand=True)
        self.reception_reset_form()
        self.reception_charger_caisses()
        self.reception_charger_tickets()

    def show_creances(self):
        self._forget_all_pages()
        self.page_creances.pack(fill="both", expand=True)
        self.charger_creances()

    def show_caisses(self):
        self._forget_all_pages()
        self.page_caisses.pack(fill="both", expand=True)
        if self.page_caisse_histo is not None:
            if hasattr(self.page_caisse_histo, "charger_caisses"):
                self.page_caisse_histo.charger_caisses()
            if hasattr(self.page_caisse_histo, "charger_historique"):
                self.page_caisse_histo.charger_historique()

    def show_produits(self):
        self._forget_all_pages()
        self.page_produits.pack(fill="both", expand=True)
        self.charger_produits()

    def show_vente(self):
        self._forget_all_pages()
        self.page_vente.pack(fill="both", expand=True)
        self.vente_actualiser_produits()
        self.vente_actualiser_caisses()
        self.vente_mettre_a_jour_affichage()

    def show_occasion(self):
        self._forget_all_pages()
        self.page_occasion.pack(fill="both", expand=True)
        self.page_occasion.charger_achats()

    # ACCUEIL --------------------------------------------------

    def _build_page_accueil(self):
        self.page_accueil.grid_rowconfigure(0, weight=1)
        self.page_accueil.grid_columnconfigure(0, weight=1)

        center = ctk.CTkFrame(self.page_accueil, fg_color="#e6ecff")
        center.grid(row=0, column=0, sticky="nsew")
        center.grid_rowconfigure(3, weight=1)
        center.grid_columnconfigure(0, weight=1)

        auteur = ctk.CTkLabel(
            center,
            text="Logiciel conçu par Mati Redouane",
            fg_color="#e6ecff",
            text_color="#555555",
            font=ctk.CTkFont(size=12, slant="italic"),
        )
        auteur.grid(row=0, column=0, pady=(10, 5), sticky="ne", padx=10)

        title = ctk.CTkLabel(
            center,
            text="Soyez les bienvenus",
            fg_color="#e6ecff",
            text_color="#243b67",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.grid(row=1, column=0, pady=(30, 5))

        info = ctk.CTkLabel(
            center,
            text="Choisissez une opération :",
            fg_color="#e6ecff",
            text_color="#333333",
            font=ctk.CTkFont(size=13),
        )
        info.grid(row=2, column=0, pady=(0, 10))

        tiles = ctk.CTkFrame(center, fg_color="#e6ecff")
        tiles.grid(row=3, column=0, pady=(10, 40))

        for r in range(3):
            tiles.grid_rowconfigure(r, weight=1)
        for c in range(3):
            tiles.grid_columnconfigure(c, weight=1)

        def create_tile(text, cmd, color, row, col):
            btn = ctk.CTkButton(
                tiles,
                text=text,
                command=cmd,
                fg_color=color,
                hover_color=color,
                text_color="white",
                font=ctk.CTkFont(size=15, weight="bold"),
                width=220,
                height=100,
                corner_radius=20,
            )
            btn.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")

        create_tile("DÉPÔT\nTÉLÉPHONE / CLIENT", self.show_depot, "#2e7d32", 0, 0)
        create_tile("RÉCEPTION\nTÉLÉPHONE", self.show_reception, "#c62828", 0, 1)
        create_tile("VENTE\nAU COMPTOIR", self.show_vente, "#FF5722", 0, 2)

        create_tile("CRÉANCES\n/ DETTES", self.show_creances, "#ff9800", 1, 0)
        create_tile("CAISSES", self.show_caisses, "#3f51b5", 1, 1)
        create_tile("PRODUITS\n/ STOCK", self.show_produits, "#009688", 1, 2)

        create_tile("HISTORIQUE\nTÉLÉPHONES REMIS", self.show_historique, "#9C27B0", 2, 0)
        create_tile("PARAMÈTRES\nMAGASIN", self.show_parametres, "#607D8B", 2, 1)
        create_tile("OCCASION\nACHAT TÉLÉPHONE", self.show_occasion, "#8E24AA", 2, 2)

    # PARAMÈTRES ----------------------------------------------

    def _build_page_parametres(self):
        top = ctk.CTkFrame(self.page_parametres, fg_color="white")
        top.pack(fill="x", padx=20, pady=(10, 5))

        ctk.CTkButton(
            top, text="← Accueil", command=self.show_accueil,
            fg_color="#cccccc", hover_color="#b0b0b0",
            text_color="#000000", width=100
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text="Paramètres du magasin",
            fg_color="white",
            text_color="#006064",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=20)

        main = ctk.CTkFrame(self.page_parametres, fg_color="#E0F7FA")
        main.pack(fill="both", expand=True, padx=20, pady=5)

        # Infos magasin
        box_info = ctk.CTkFrame(main, fg_color="#FFFFFF", corner_radius=10)
        box_info.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            box_info,
            text="Informations du magasin",
            text_color="#006064",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=3, padx=10, pady=(8, 4), sticky="w")

        ctk.CTkLabel(box_info, text="Nom du magasin :", text_color="#000000").grid(
            row=1, column=0, padx=10, pady=4, sticky="e"
        )
        self.param_nom_entry = ctk.CTkEntry(box_info, width=260)
        self.param_nom_entry.grid(row=1, column=1, padx=5, pady=4, sticky="w")

        ctk.CTkLabel(box_info, text="Téléphone :", text_color="#000000").grid(
            row=2, column=0, padx=10, pady=4, sticky="e"
        )
        self.param_tel_entry = ctk.CTkEntry(box_info, width=260)
        self.param_tel_entry.grid(row=2, column=1, padx=5, pady=4, sticky="w")

        ctk.CTkLabel(box_info, text="Logo magasin :", text_color="#000000").grid(
            row=3, column=0, padx=10, pady=4, sticky="e"
        )
        self.param_logo_label = ctk.CTkLabel(
            box_info,
            text="(logo par défaut : logo.png)",
            text_color="#004d40",
        )
        self.param_logo_label.grid(row=3, column=1, padx=5, pady=4, sticky="w")

        ctk.CTkButton(
            box_info,
            text="Choisir un logo...",
            fg_color="#00838F",
            hover_color="#006064",
            text_color="white",
            command=self._param_choisir_logo,
            width=150
        ).grid(row=3, column=2, padx=5, pady=4, sticky="w")

        ctk.CTkButton(
            box_info,
            text="Enregistrer les informations",
            fg_color="#00796B",
            hover_color="#004D40",
            text_color="white",
            command=self._param_enregistrer_infos
        ).grid(row=4, column=0, columnspan=3, padx=10, pady=(8, 10))

        # Sécurité admin
        box_sec = ctk.CTkFrame(main, fg_color="#FFFFFF", corner_radius=10)
        box_sec.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            box_sec,
            text="Sécurité - Administrateur",
            text_color="#BF360C",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(8, 4), sticky="w")

        self.param_admin_status_label = ctk.CTkLabel(
            box_sec,
            text="",
            text_color="#000000",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.param_admin_status_label.grid(row=1, column=0, columnspan=2, padx=10, pady=4, sticky="w")

        ctk.CTkButton(
            box_sec,
            text="Définir / changer le mot de passe admin",
            fg_color="#D84315",
            hover_color="#BF360C",
            text_color="white",
            command=self._param_changer_mdp_admin
        ).grid(row=2, column=0, columnspan=2, padx=10, pady=(6, 10))

        ctk.CTkLabel(
            box_sec,
            text="Seul l'administrateur peut :\n"
                 " - Saisir des sommes manuellement en caisse\n"
                 " - Modifier/ajouter des produits au stock\n"
                 " - Enregistrer des factures d'achat (entrée de stock)",
            text_color="#5D4037",
            font=ctk.CTkFont(size=11),
            justify="left"
        ).grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")

    def _param_charger_ui(self):
        self.param_nom_entry.delete(0, "end")
        self.param_nom_entry.insert(0, self.store_name or "Red")

        self.param_tel_entry.delete(0, "end")
        self.param_tel_entry.insert(0, self.store_tel or "")

        if self.store_logo_path:
            self.param_logo_label.configure(text=self.store_logo_path)
        else:
            self.param_logo_label.configure(text="(logo par défaut : logo.png)")

        self._param_update_admin_status()

    def _param_update_admin_status(self):
        if self.admin_password:
            txt = "Mot de passe administrateur : DÉFINI"
            col = "#1B5E20"
        else:
            txt = "Mot de passe administrateur : NON défini"
            col = "#B71C1C"
        self.param_admin_status_label.configure(text=txt, text_color=col)

    def _param_choisir_logo(self):
        path = filedialog.askopenfilename(
            title="Choisir un logo",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif"), ("Tous les fichiers", "*.*")]
        )
        if not path:
            return
        self.store_logo_path = path
        self.param_logo_label.configure(text=path)
        self._update_header()
        self._save_settings()

    def _param_enregistrer_infos(self):
        nom = (self.param_nom_entry.get() or "").strip()
        tel = (self.param_tel_entry.get() or "").strip()
        if not nom:
            nom = "Red"
        self.store_name = nom
        self.store_tel = tel
        self._update_header()
        self._save_settings()
        messagebox.showinfo("Paramètres", "Informations du magasin mises à jour.", parent=self.root)

    def _param_changer_mdp_admin(self):
        if self.admin_password:
            old = simpledialog.askstring(
                "Administrateur",
                "Ancien mot de passe :",
                parent=self.root,
                show="*"
            )
            if old is None:
                return
            if old != self.admin_password:
                messagebox.showerror("Administrateur", "Ancien mot de passe incorrect.", parent=self.root)
                return

        new1 = simpledialog.askstring(
            "Administrateur",
            "Nouveau mot de passe :",
            parent=self.root,
            show="*"
        )
        if not new1:
            messagebox.showwarning("Administrateur", "Le mot de passe ne peut pas être vide.", parent=self.root)
            return
        new2 = simpledialog.askstring(
            "Administrateur",
            "Confirmer le mot de passe :",
            parent=self.root,
            show="*"
        )
        if new2 != new1:
            messagebox.showwarning("Administrateur", "La confirmation ne correspond pas.", parent=self.root)
            return

        self.admin_password = new1
        self.admin_authenticated = False
        self._param_update_admin_status()
        self._save_settings()
        messagebox.showinfo("Administrateur", "Mot de passe administrateur mis à jour.", parent=self.root)

    # ==========================================================
    #  RÉCEPTION TÉLÉPHONE
    # ==========================================================

    def _build_page_reception(self):
        top = ctk.CTkFrame(self.page_reception, fg_color="white")
        top.pack(fill="x", padx=20, pady=(10, 5))

        ctk.CTkButton(
            top, text="← Accueil", command=self.show_accueil,
            fg_color="#cccccc", hover_color="#b0b0b0",
            text_color="#000000", width=100
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text="Réception téléphone",
            fg_color="white",
            text_color="#b71c1c",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=20)

        main = ctk.CTkFrame(self.page_reception, fg_color="#fafafa")
        main.pack(fill="both", expand=True, padx=20, pady=5)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # -------- COLONNE GAUCHE : LISTE DES TICKETS EN COURS --------
        left = ctk.CTkFrame(main, fg_color="#fafafa")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            left,
            text="Tickets en cours",
            text_color="#000000",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=5, pady=(5, 2), sticky="w")

        cols = ("id", "client", "tel", "tel_col", "date", "statut")
        self.reception_tickets_tree = ttk.Treeview(left, columns=cols, show="headings", height=12)
        self.reception_tickets_tree.heading("id", text="ID")
        self.reception_tickets_tree.heading("client", text="Client")
        self.reception_tickets_tree.heading("tel", text="Téléphone client")
        self.reception_tickets_tree.heading("tel_col", text="Téléphone (marque/modèle)")
        self.reception_tickets_tree.heading("date", text="Date dépôt")
        self.reception_tickets_tree.heading("statut", text="Statut")

        self.reception_tickets_tree.column("id", width=40, anchor="center")
        self.reception_tickets_tree.column("client", width=120, anchor="w")
        self.reception_tickets_tree.column("tel", width=90, anchor="w")
        self.reception_tickets_tree.column("tel_col", width=160, anchor="w")
        self.reception_tickets_tree.column("date", width=90, anchor="center")
        self.reception_tickets_tree.column("statut", width=80, anchor="center")

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.reception_tickets_tree.yview)
        self.reception_tickets_tree.configure(yscrollcommand=vsb.set)

        self.reception_tickets_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 2), pady=(0, 5))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 5))

        self.reception_tickets_tree.bind("<<TreeviewSelect>>", lambda e: self.reception_on_ticket_select())

        # -------- COLONNE DROITE : DÉTAILS + FORMULAIRE --------
        right = ctk.CTkFrame(main, fg_color="white")
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right.grid_columnconfigure(1, weight=1)

        rowi = 0
        ctk.CTkLabel(right, text="Détails du ticket", text_color="#000000",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=rowi, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 2)
        )

        rowi += 1
        ctk.CTkLabel(right, text="Client :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.rec_client_entry = ctk.CTkEntry(right, width=250)
        self.rec_client_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Téléphone client :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.rec_tel_entry = ctk.CTkEntry(right, width=250)
        self.rec_tel_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Téléphone (marque / modèle) :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.rec_pc_entry = ctk.CTkEntry(right, width=250)
        self.rec_pc_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Date dépôt :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.rec_date_depot_entry = ctk.CTkEntry(right, width=120)
        self.rec_date_depot_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Diagnostic initial :", text_color="#000000").grid(
            row=rowi, column=0, sticky="ne", padx=5, pady=2
        )
        self.rec_diag_text = tk.Text(right, height=3, width=40)
        self.rec_diag_text.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Travaux effectués :", text_color="#000000").grid(
            row=rowi, column=0, sticky="ne", padx=5, pady=2
        )
        self.rec_travaux_text = tk.Text(right, height=3, width=40)
        self.rec_travaux_text.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Montant total (DA) :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.rec_montant_total_entry = ctk.CTkEntry(right, width=120)
        self.rec_montant_total_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Montant payé (DA) :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.rec_montant_paye_entry = ctk.CTkEntry(right, width=120)
        self.rec_montant_paye_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        # mise à jour dynamique du reste à payer
        self.rec_montant_total_entry.bind("<KeyRelease>", lambda e: self.reception_maj_restant())
        self.rec_montant_paye_entry.bind("<KeyRelease>", lambda e: self.reception_maj_restant())

        rowi += 1
        ctk.CTkLabel(right, text="Reste à payer :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.rec_montant_restant_label = ctk.CTkLabel(
            right, text="0.00 DA", text_color="#b71c1c",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.rec_montant_restant_label.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        # Choix de la caisse
        rowi += 1
        ctk.CTkLabel(right, text="Caisse :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.reception_caisse_var = tk.StringVar()
        self.reception_caisses_map = {}
        self.reception_caisse_option = ctk.CTkOptionMenu(
            right,
            variable=self.reception_caisse_var,
            values=[],
            command=self.reception_on_caisse_change,
            width=220
        )
        self.reception_caisse_option.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        btns = ctk.CTkFrame(right, fg_color="white")
        btns.grid(row=rowi, column=0, columnspan=2, pady=(6, 8))

        ctk.CTkButton(
            btns,
            text="Valider la réception",
            fg_color="#c62828",
            hover_color="#8e0000",
            text_color="white",
            command=self.reception_valider,
            width=160
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btns,
            text="Supprimer le ticket",
            fg_color="#9e9e9e",
            hover_color="#616161",
            text_color="white",
            command=self.reception_supprimer_ticket,
            width=160
        ).pack(side="left", padx=4)

    def reception_reset_form(self):
        self.reception_ticket_id = None
        for e in [
            self.rec_client_entry,
            self.rec_tel_entry,
            self.rec_pc_entry,
            self.rec_date_depot_entry,
            self.rec_montant_total_entry,
            self.rec_montant_paye_entry,
        ]:
            e.delete(0, "end")

        self.rec_diag_text.delete("1.0", "end")
        self.rec_travaux_text.delete("1.0", "end")
        self.rec_montant_restant_label.configure(text="0.00 DA")

    def reception_charger_tickets(self):
        """Charge la liste des tickets 'En cours'."""
        try:
            rows = self.db.get_tickets(statut="En cours")
        except Exception as e:
            messagebox.showerror("Réception", f"Erreur lecture tickets : {e}", parent=self.root)
            return

        self.reception_tickets_tree.delete(*self.reception_tickets_tree.get_children())
        self.reception_tickets_map = {}

        for row in rows:
            tid = row["id"]
            client = row["client_nom"] or ""
            tel = row["client_tel"] or ""
            pc = (row["pc_marque"] or "") + ((" " + (row["pc_modele"] or "")) if row["pc_modele"] else "")
            date_depot = row["date_depot"] or ""
            statut = row["statut"] or ""
            self.reception_tickets_map[tid] = row
            self.reception_tickets_tree.insert(
                "",
                "end",
                values=(tid, client, tel, pc, date_depot, statut)
            )

    def reception_charger_caisses(self):
        """Charge la liste des caisses dans le menu déroulant de la page Réception."""
        try:
            caisses = self.db.get_caisses()
        except Exception as e:
            messagebox.showerror("Réception", f"Erreur lecture caisses : {e}", parent=self.root)
            return

        self.reception_caisses_map = {}
        values = []
        for row in caisses:
            cid, nom, desc = row
            label = f"{cid} - {nom}"
            values.append(label)
            self.reception_caisses_map[label] = cid

        self.reception_caisse_option.configure(values=values)

        if self.caisse_selectionnee_id is not None:
            for lbl, cid in self.reception_caisses_map.items():
                if cid == self.caisse_selectionnee_id:
                    self.reception_caisse_option.set(lbl)
                    break
            else:
                if values:
                    self.reception_caisse_option.set(values[0])
                    self.caisse_selectionnee_id = self.reception_caisses_map[values[0]]
        else:
            if values:
                self.reception_caisse_option.set(values[0])
                self.caisse_selectionnee_id = self.reception_caisses_map[values[0]]

    def reception_on_caisse_change(self, choice: str):
        if not choice:
            return
        cid = self.reception_caisses_map.get(choice)
        if cid:
            self.caisse_selectionnee_id = cid

    def reception_on_ticket_select(self):
        sel = self.reception_tickets_tree.selection()
        if not sel:
            return
        vals = self.reception_tickets_tree.item(sel[0]).get("values") or []
        if not vals:
            return
        tid = vals[0]
        try:
            tid = int(tid)
        except Exception:
            return

        row = self.reception_tickets_map.get(tid)
        if not row:
            return

        self.reception_ticket_id = tid

        self.rec_client_entry.delete(0, "end")
        self.rec_client_entry.insert(0, row["client_nom"] or "")

        self.rec_tel_entry.delete(0, "end")
        self.rec_tel_entry.insert(0, row["client_tel"] or "")

        pc_txt = (row["pc_marque"] or "") + ((" " + (row["pc_modele"] or "")) if row["pc_modele"] else "")
        self.rec_pc_entry.delete(0, "end")
        self.rec_pc_entry.insert(0, pc_txt)

        self.rec_date_depot_entry.delete(0, "end")
        self.rec_date_depot_entry.insert(0, row["date_depot"] or "")

        self.rec_diag_text.delete("1.0", "end")
        self.rec_diag_text.insert("1.0", row["diagnostic_initial"] or "")

        self.rec_travaux_text.delete("1.0", "end")
        self.rec_travaux_text.insert("1.0", row["travaux_effectues"] or "")

        mt_total = row["montant_total"] if row["montant_total"] is not None else 0.0
        mt_paye = row["montant_paye"] if row["montant_paye"] is not None else 0.0
        restant = row["montant_restant"]
        if restant is None:
            restant = float(mt_total) - float(mt_paye)
        if restant < 0:
            restant = 0.0

        self.rec_montant_total_entry.delete(0, "end")
        self.rec_montant_total_entry.insert(0, f"{float(mt_total):.2f}")

        self.rec_montant_paye_entry.delete(0, "end")
        self.rec_montant_paye_entry.insert(0, f"{float(mt_paye):.2f}")

        self.rec_montant_restant_label.configure(text=f"{float(restant):.2f} DA")

    def reception_maj_restant(self):
        """Met à jour le label 'Reste à payer' en fonction du total et du montant payé."""
        try:
            total = float((self.rec_montant_total_entry.get() or "0").replace(",", "."))
        except ValueError:
            total = 0.0
        try:
            paye = float((self.rec_montant_paye_entry.get() or "0").replace(",", "."))
        except ValueError:
            paye = 0.0

        reste = total - paye
        if reste < 0:
            reste = 0.0
        self.rec_montant_restant_label.configure(text=f"{reste:.2f} DA")

    def reception_valider(self):
        if not self.reception_ticket_id:
            messagebox.showwarning("Réception", "Sélectionnez un ticket dans la liste.", parent=self.root)
            return

        travaux_effectues = (self.rec_travaux_text.get("1.0", "end") or "").strip()
        if not travaux_effectues:
            if not messagebox.askyesno(
                "Réception",
                "Aucun texte saisi dans 'travaux effectués'.\nContinuer quand même ?",
                parent=self.root
            ):
                return

        try:
            mt_total = float((self.rec_montant_total_entry.get() or "0").replace(",", "."))
        except ValueError:
            messagebox.showwarning("Réception", "Montant total invalide.", parent=self.root)
            return

        try:
            mt_paye = float((self.rec_montant_paye_entry.get() or "0").replace(",", "."))
        except ValueError:
            messagebox.showwarning("Réception", "Montant payé invalide.", parent=self.root)
            return

        # Si un montant est payé, une caisse doit être sélectionnée
        if mt_paye > 0 and not self.caisse_selectionnee_id:
            messagebox.showwarning(
                "Réception",
                "Aucune caisse sélectionnée pour encaisser le paiement.",
                parent=self.root
            )
            return

        try:
            reste = self.db.enregistrer_reception_pc(
                ticket_id=self.reception_ticket_id,
                travaux_effectues=travaux_effectues,
                montant_total=mt_total,
                montant_paye=mt_paye
            )
        except Exception as e:
            messagebox.showerror("Réception", f"Erreur enregistrement : {e}", parent=self.root)
            return

        msg = ""
        if reste > 0.01:
            try:
                row = self.db.get_ticket_by_id(self.reception_ticket_id)
                client_nom = row["client_nom"] or "Client inconnu"
                pc_marque = row["pc_marque"] or ""
                description = f"Réparation téléphone (ticket N°{self.reception_ticket_id})"
                date_retrait = row["date_retrait"] or datetime.now().strftime("%d/%m/%Y")
                self.db.ajouter_creance(
                    client_nom=client_nom,
                    pc_marque=pc_marque,
                    description=description,
                    montant_total=mt_total,
                    montant_paye=mt_paye,
                    montant_restant=reste,
                    date_retrait=date_retrait,
                    ticket_id=self.reception_ticket_id
                )
                msg = f"Réception enregistrée.\nCréance ajoutée : {reste:.2f} DA restant."
            except Exception as e:
                msg = f"Réception enregistrée.\nATTENTION : erreur enregistrement créance : {e}"
        else:
            msg = "Réception enregistrée (aucun reste à payer)."

        # Mouvement de caisse (entrée) pour le montant payé
        if mt_paye > 0:
            desc = f"Réparation téléphone N°{self.reception_ticket_id}"
            try:
                self.db.ajouter_mouvement_caisse(
                    caisse_id=self.caisse_selectionnee_id,
                    type_mvt="ENTREE",
                    montant=mt_paye,
                    description=desc
                )
            except Exception as e:
                messagebox.showerror(
                    "Réception",
                    f"Réception OK mais erreur mouvement caisse : {e}",
                    parent=self.root
                )

        messagebox.showinfo("Réception", msg, parent=self.root)

        self.reception_charger_tickets()
        self.reception_reset_form()
        self.charger_creances()

    def reception_supprimer_ticket(self):
        """Marque le ticket sélectionné comme 'Annulé' (disparaît de Réception, reste en historique)."""
        if not self.reception_ticket_id:
            messagebox.showwarning(
                "Réception",
                "Sélectionnez un ticket dans la liste avant de le supprimer.",
                parent=self.root
            )
            return

        if not messagebox.askyesno(
            "Réception",
            "Marquer ce ticket comme ANNULÉ ?\n"
            "Il ne s'affichera plus dans la liste de Réception,\n"
            "mais restera dans la base (historique).",
            parent=self.root
        ):
            return

        try:
            self.db.cursor.execute(
                "UPDATE tickets_reparation SET statut = ? WHERE id = ?",
                ("Annulé", self.reception_ticket_id)
            )
            self.db.conn.commit()
        except Exception as e:
            messagebox.showerror(
                "Réception",
                f"Erreur lors de la suppression (annulation) du ticket : {e}",
                parent=self.root
            )
            return

        messagebox.showinfo("Réception", "Ticket marqué comme ANNULÉ.", parent=self.root)
        self.reception_charger_tickets()
        self.reception_reset_form()

    # ==========================================================
    #  CRÉANCES / DETTES
    # ==========================================================

    def _build_page_creances(self):
        top = ctk.CTkFrame(self.page_creances, fg_color="white")
        top.pack(fill="x", padx=20, pady=(10, 5))

        ctk.CTkButton(
            top, text="← Accueil", command=self.show_accueil,
            fg_color="#cccccc", hover_color="#b0b0b0",
            text_color="#000000", width=100
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text="Créances / Dettes",
            fg_color="white",
            text_color="#e65100",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=20)

        main = ctk.CTkFrame(self.page_creances, fg_color="#fff8e1")
        main.pack(fill="both", expand=True, padx=20, pady=5)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # -------- COLONNE GAUCHE : LISTE DES CRÉANCES --------
        left = ctk.CTkFrame(main, fg_color="#fff8e1")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            left,
            text="Liste des créances / dettes",
            text_color="#000000",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=5, pady=(5, 2), sticky="w")

        cols = ("id", "client", "tel", "total", "paye", "reste", "date")
        self.creances_tree = ttk.Treeview(left, columns=cols, show="headings", height=12)
        self.creances_tree.heading("id", text="ID")
        self.creances_tree.heading("client", text="Client")
        self.creances_tree.heading("tel", text="Téléphone / Appareil")
        self.creances_tree.heading("total", text="Total")
        self.creances_tree.heading("paye", text="Payé")
        self.creances_tree.heading("reste", text="Reste")
        self.creances_tree.heading("date", text="Date")

        self.creances_tree.column("id", width=50, anchor="center")
        self.creances_tree.column("client", width=130, anchor="w")
        self.creances_tree.column("tel", width=130, anchor="w")
        self.creances_tree.column("total", width=80, anchor="e")
        self.creances_tree.column("paye", width=80, anchor="e")
        self.creances_tree.column("reste", width=80, anchor="e")
        self.creances_tree.column("date", width=90, anchor="center")

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.creances_tree.yview)
        self.creances_tree.configure(yscrollcommand=vsb.set)

        self.creances_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 2), pady=(0, 5))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 5))

        self.creances_tree.bind("<<TreeviewSelect>>", lambda e: self.creances_on_select())

        # -------- COLONNE DROITE : DÉTAILS + PAIEMENT --------
        right = ctk.CTkFrame(main, fg_color="white")
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right.grid_columnconfigure(1, weight=1)

        rowi = 0
        ctk.CTkLabel(
            right,
            text="Détail de la créance",
            text_color="#000000",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=rowi, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 2))

        rowi += 1
        ctk.CTkLabel(right, text="Client :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.cre_client_label = ctk.CTkLabel(right, text="", text_color="#000000")
        self.cre_client_label.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Téléphone / Appareil :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.cre_pc_label = ctk.CTkLabel(right, text="", text_color="#000000")
        self.cre_pc_label.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Description :", text_color="#000000").grid(
            row=rowi, column=0, sticky="ne", padx=5, pady=2
        )
        self.cre_desc_text = tk.Text(right, height=3, width=40)
        self.cre_desc_text.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Montant total :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.cre_total_label = ctk.CTkLabel(right, text="0.00 DA", text_color="#000000")
        self.cre_total_label.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Déjà payé :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.cre_paye_label = ctk.CTkLabel(right, text="0.00 DA", text_color="#000000")
        self.cre_paye_label.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Reste à payer :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.cre_reste_label = ctk.CTkLabel(
            right, text="0.00 DA", text_color="#b71c1c",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.cre_reste_label.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Nouveau paiement (DA) :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=4
        )
        self.cre_paiement_entry = ctk.CTkEntry(right, width=120)
        self.cre_paiement_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=4)

        # BOUTON ENREGISTRER PAIEMENT
        rowi += 1
        ctk.CTkButton(
            right,
            text="Enregistrer le paiement",
            fg_color="#e65100",
            hover_color="#bf360c",
            text_color="white",
            command=self.creances_enregistrer_paiement
        ).grid(row=rowi, column=0, columnspan=2, pady=(6, 4))

        # BOUTON SUPPRIMER CRÉANCE SI RESTE = 0
        rowi += 1
        ctk.CTkButton(
            right,
            text="Supprimer la créance (reste = 0)",
            fg_color="#9e9e9e",
            hover_color="#757575",
            text_color="white",
            command=self.creances_supprimer
        ).grid(row=rowi, column=0, columnspan=2, pady=(0, 8))

        self.creances_selected_id = None        # id de la créance sélectionnée
        self.creances_rows = {}                 # id -> row

    def charger_creances(self):
        """Charge toutes les créances / dettes."""
        try:
            rows = self.db.get_creances()
        except Exception as e:
            messagebox.showerror("Créances", f"Erreur lecture créances : {e}", parent=self.root)
            return

        self.creances_tree.delete(*self.creances_tree.get_children())
        self.creances_rows = {}

        for row in rows:
            cid = row["id"]
            client = row["client_nom"] or ""
            pc = row["pc_marque"] or ""
            total = float(row["montant_total"] or 0)
            paye = float(row["montant_paye"] or 0)
            reste = float(row["montant_restant"] or 0)
            date = row["date_retrait"] or ""
            self.creances_rows[cid] = row
            self.creances_tree.insert(
                "",
                "end",
                values=(cid, client, pc, f"{total:.2f}", f"{paye:.2f}", f"{reste:.2f}", date)
            )

        self.creances_selected_id = None
        self.cre_client_label.configure(text="")
        self.cre_pc_label.configure(text="")
        self.cre_desc_text.delete("1.0", "end")
        self.cre_total_label.configure(text="0.00 DA")
        self.cre_paye_label.configure(text="0.00 DA")
        self.cre_reste_label.configure(text="0.00 DA")
        self.cre_paiement_entry.delete(0, "end")

    def creances_on_select(self):
        sel = self.creances_tree.selection()
        if not sel:
            return
        vals = self.creances_tree.item(sel[0]).get("values") or []
        if not vals:
            return
        cid = vals[0]
        try:
            cid = int(cid)
        except Exception:
            return
        row = self.creances_rows.get(cid)
        if not row:
            return

        self.creances_selected_id = cid

        client = row["client_nom"] or ""
        pc = row["pc_marque"] or ""
        desc = row["description"] or ""
        total = float(row["montant_total"] or 0)
        paye = float(row["montant_paye"] or 0)
        reste = float(row["montant_restant"] or 0)

        self.cre_client_label.configure(text=client)
        self.cre_pc_label.configure(text=pc)

        self.cre_desc_text.delete("1.0", "end")
        self.cre_desc_text.insert("1.0", desc)

        self.cre_total_label.configure(text=f"{total:.2f} DA")
        self.cre_paye_label.configure(text=f"{paye:.2f} DA")
        self.cre_reste_label.configure(text=f"{reste:.2f} DA")

        self.cre_paiement_entry.delete(0, "end")

    def creances_enregistrer_paiement(self):
        if not self.creances_selected_id:
            messagebox.showwarning("Créances", "Sélectionnez une créance dans la liste.", parent=self.root)
            return

        row = self.creances_rows.get(self.creances_selected_id)
        if not row:
            messagebox.showerror("Créances", "Impossible de retrouver la créance sélectionnée.", parent=self.root)
            return

        try:
            paiement = float((self.cre_paiement_entry.get() or "0").replace(",", "."))
        except ValueError:
            messagebox.showwarning("Créances", "Montant de paiement invalide.", parent=self.root)
            return

        if paiement <= 0:
            messagebox.showwarning("Créances", "Le paiement doit être strictement positif.", parent=self.root)
            return

        total = float(row["montant_total"] or 0)
        deja_paye = float(row["montant_paye"] or 0)
        reste = float(row["montant_restant"] or 0)

        if paiement > reste + 0.01:
            if not messagebox.askyesno(
                "Créances",
                "Le paiement dépasse le reste à payer.\nEnregistrer quand même (le reste sera mis à 0) ?",
                parent=self.root
            ):
                return

        nouveau_paye = deja_paye + paiement
        nouveau_reste = total - nouveau_paye
        if nouveau_reste < 0:
            nouveau_reste = 0.0

        try:
            self.db.mettre_a_jour_creance(
                creance_id=self.creances_selected_id,
                montant_paye=nouveau_paye,
                montant_restant=nouveau_reste
            )
        except Exception as e:
            messagebox.showerror("Créances", f"Erreur mise à jour créance : {e}", parent=self.root)
            return

        messagebox.showinfo("Créances", "Paiement enregistré.", parent=self.root)
        self.charger_creances()

    def creances_supprimer(self):
        """
        Supprime la créance sélectionnée si le montant restant est 0.
        """
        if not self.creances_selected_id:
            messagebox.showwarning(
                "Créances",
                "Sélectionnez une créance dans la liste.",
                parent=self.root
            )
            return

        row = self.creances_rows.get(self.creances_selected_id)
        if not row:
            messagebox.showerror(
                "Créances",
                "Impossible de retrouver la créance sélectionnée.",
                parent=self.root
            )
            return

        # Montant restant
        reste = float(row["montant_restant"] or 0)

        # On n'autorise la suppression que si reste ≈ 0
        if reste > 0.01:
            messagebox.showwarning(
                "Créances",
                "Vous ne pouvez supprimer qu'une créance dont le reste à payer est 0.00 DA.",
                parent=self.root
            )
            return

        client = row["client_nom"] or ""
        if not messagebox.askyesno(
            "Créances",
            f"Supprimer cette créance pour le client « {client} » ?\n"
            "Cette opération est définitive.",
            parent=self.root
        ):
            return

        try:
            self.db.supprimer_creance(self.creances_selected_id)
        except Exception as e:
            messagebox.showerror(
                "Créances",
                f"Erreur lors de la suppression de la créance : {e}",
                parent=self.root
            )
            return

        messagebox.showinfo("Créances", "Créance supprimée.", parent=self.root)
        self.charger_creances()

    # ==========================================================
    #  CAISSES (en-tête + CaisseHistoriquePage)
    # ==========================================================

    def _build_page_caisses(self):
        top = ctk.CTkFrame(self.page_caisses, fg_color="white")
        top.pack(fill="x", padx=20, pady=(10, 5))

        ctk.CTkButton(
            top, text="← Accueil", command=self.show_accueil,
            fg_color="#cccccc", hover_color="#b0b0b0",
            text_color="#000000", width=100
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text="Historique des caisses",
            fg_color="white",
            text_color="#1e88e5",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=20)

        content = ctk.CTkFrame(self.page_caisses, fg_color="#e3f2fd")
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.page_caisse_histo = CaisseHistoriquePage(content, self)
        self.page_caisse_histo.pack(fill="both", expand=True)

    def charger_caisses(self):
        pass

    # ==========================================================
    #  PRODUITS / STOCK + BON D'ACHAT / FACTURE DE VENTE
    # ==========================================================

    def _build_page_produits(self):
        top = ctk.CTkFrame(self.page_produits, fg_color="white")
        top.pack(fill="x", padx=20, pady=(10, 5))

        ctk.CTkButton(
            top, text="← Accueil", command=self.show_accueil,
            fg_color="#cccccc", hover_color="#b0b0b0",
            text_color="#000000", width=100
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text="Produits / Stock",
            fg_color="white",
            text_color="#00796b",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=20)

        main = ctk.CTkFrame(self.page_produits, fg_color="#e0f2f1")
        main.pack(fill="both", expand=True, padx=20, pady=5)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # ---------- BARRE DE RECHERCHE ----------
        search_frame = ctk.CTkFrame(main, fg_color="#e0f2f1")
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="Recherche :", text_color="#000000").grid(
            row=0, column=0, padx=5, pady=3, sticky="w"
        )
        self.prod_search_var = tk.StringVar()
        self.prod_search_entry = ctk.CTkEntry(search_frame, textvariable=self.prod_search_var, width=220)
        self.prod_search_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        self.prod_search_entry.bind("<Return>", lambda e: self.charger_produits())

        ctk.CTkLabel(search_frame, text="Filtre :", text_color="#000000").grid(
            row=0, column=2, padx=5, pady=3, sticky="e"
        )
        self.prod_filter_var = tk.StringVar(value="Actifs")
        self.prod_filter_menu = ctk.CTkOptionMenu(
            search_frame,
            variable=self.prod_filter_var,
            values=["Actifs", "Tous"],
            width=100
        )
        self.prod_filter_menu.grid(row=0, column=3, padx=5, pady=3, sticky="w")

        ctk.CTkButton(
            search_frame,
            text="Rechercher",
            fg_color="#00796b",
            hover_color="#004d40",
            text_color="white",
            command=self.charger_produits,
            width=100
        ).grid(row=0, column=4, padx=5, pady=3)

        # ---------- COLONNE GAUCHE : LISTE DES PRODUITS ----------
        left = ctk.CTkFrame(main, fg_color="#e0f2f1")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            left,
            text="Produits en stock",
            text_color="#000000",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=5, pady=(5, 2), sticky="w")

        cols = ("id", "nom", "ref", "cat", "pv", "qte", "actif")
        self.produits_tree = ttk.Treeview(left, columns=cols, show="headings", height=12)
        self.produits_tree.heading("id", text="ID")
        self.produits_tree.heading("nom", text="Nom")
        self.produits_tree.heading("ref", text="Référence")
        self.produits_tree.heading("cat", text="Catégorie")
        self.produits_tree.heading("pv", text="P. Vente")
        self.produits_tree.heading("qte", text="Stock")
        self.produits_tree.heading("actif", text="Actif")

        self.produits_tree.column("id", width=40, anchor="center")
        self.produits_tree.column("nom", width=150, anchor="w")
        self.produits_tree.column("ref", width=100, anchor="w")
        self.produits_tree.column("cat", width=100, anchor="w")
        self.produits_tree.column("pv", width=70, anchor="e")
        self.produits_tree.column("qte", width=60, anchor="e")
        self.produits_tree.column("actif", width=50, anchor="center")

        vsb_prod = ttk.Scrollbar(left, orient="vertical", command=self.produits_tree.yview)
        self.produits_tree.configure(yscrollcommand=vsb_prod.set)

        self.produits_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 2), pady=(0, 5))
        vsb_prod.grid(row=1, column=1, sticky="ns", pady=(0, 5))

        self.produits_tree.bind("<<TreeviewSelect>>", lambda e: self.produits_on_select())

        # ---------- COLONNE DROITE : FORMULAIRE DÉTAIL ----------
        right = ctk.CTkFrame(main, fg_color="white")
        right.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        right.grid_columnconfigure(1, weight=1)

        rowi = 0
        ctk.CTkLabel(
            right,
            text="Détail du produit",
            text_color="#000000",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=rowi, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 2))

        rowi += 1
        ctk.CTkLabel(right, text="Code-barres :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.prod_cb_entry = ctk.CTkEntry(right, width=180)
        self.prod_cb_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Référence :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.prod_ref_entry = ctk.CTkEntry(right, width=180)
        self.prod_ref_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Nom produit :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.prod_nom_entry = ctk.CTkEntry(right, width=220)
        self.prod_nom_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Catégorie :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.prod_cat_entry = ctk.CTkEntry(right, width=180)
        self.prod_cat_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Prix achat (DA) :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.prod_pa_entry = ctk.CTkEntry(right, width=100)
        self.prod_pa_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Prix vente (DA) :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.prod_pv_entry = ctk.CTkEntry(right, width=100)
        self.prod_pv_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Quantité stock :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.prod_qte_entry = ctk.CTkEntry(right, width=100)
        self.prod_qte_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        ctk.CTkLabel(right, text="Seuil alerte :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=2
        )
        self.prod_seuil_entry = ctk.CTkEntry(right, width=100)
        self.prod_seuil_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=2)

        rowi += 1
        self.prod_actif_var = tk.BooleanVar(value=True)
        self.prod_actif_check = ctk.CTkCheckBox(
            right, text="Produit actif", variable=self.prod_actif_var, onvalue=True, offvalue=False
        )
        self.prod_actif_check.grid(row=rowi, column=1, sticky="w", padx=5, pady=4)

        rowi += 1
        btn_frame = ctk.CTkFrame(right, fg_color="white")
        btn_frame.grid(row=rowi, column=0, columnspan=2, sticky="ew", pady=(6, 4))

        ctk.CTkButton(
            btn_frame,
            text="Nouveau",
            fg_color="#9e9e9e",
            hover_color="#757575",
            text_color="white",
            command=self.produits_nouveau,
            width=80
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame,
            text="Enregistrer / Modifier",
            fg_color="#00796b",
            hover_color="#004d40",
            text_color="white",
            command=self.produits_enregistrer,
            width=150
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame,
            text="Supprimer",
            fg_color="#b71c1c",
            hover_color="#7f0000",
            text_color="white",
            command=self.produits_supprimer,
            width=100
        ).pack(side="left", padx=4)

        rowi += 1
        btn_stock = ctk.CTkFrame(right, fg_color="white")
        btn_stock.grid(row=rowi, column=0, columnspan=2, sticky="ew", pady=(2, 8))

        ctk.CTkButton(
            btn_stock,
            text="Ajouter au stock (+)",
            fg_color="#388e3c",
            hover_color="#1b5e20",
            text_color="white",
            command=lambda: self.produits_adjust_stock(1),
            width=140
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_stock,
            text="Retirer du stock (-)",
            fg_color="#f57c00",
            hover_color="#e65100",
            text_color="white",
            command=lambda: self.produits_adjust_stock(-1),
            width=150
        ).pack(side="left", padx=4)

        # NOUVEAUX BOUTONS : BON D'ACHAT & FACTURE DE VENTE
        ctk.CTkButton(
            btn_stock,
            text="Bon d'achat",
            fg_color="#3949AB",
            hover_color="#283593",
            text_color="white",
            command=self.produits_bon_achat,
            width=120
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_stock,
            text="Facture de vente",
            fg_color="#D84315",
            hover_color="#BF360C",
            text_color="white",
            command=self.produits_bon_vente,
            width=140
        ).pack(side="left", padx=4)

        self.prod_selected_id = None
        self.produits_rows = {}

    def charger_produits(self):
        """Charge la liste des produits selon le filtre et la recherche."""
        terme = (self.prod_search_var.get() or "").strip() if hasattr(self, "prod_search_var") else ""
        filt = self.prod_filter_var.get() if hasattr(self, "prod_filter_var") else "Actifs"
        uniquement_actifs = (filt == "Actifs")

        try:
            if terme:
                rows = self.db.rechercher_produits(terme, uniquement_actifs=uniquement_actifs)
            else:
                rows = self.db.get_produits(uniquement_actifs=uniquement_actifs)
        except Exception as e:
            messagebox.showerror("Produits", f"Erreur lecture produits : {e}", parent=self.root)
            return

        self.produits_tree.delete(*self.produits_tree.get_children())
        self.produits_rows = {}

        for row in rows:
            pid = row["id"]
            nom = row["nom"] or ""
            ref = row["reference"] or ""
            cat = row["categorie"] or ""
            pv = float(row["prix_vente"] or 0)
            qte = int(row["quantite"] or 0)
            actif = "Oui" if int(row["actif"] or 0) == 1 else "Non"
            self.produits_rows[pid] = row
            self.produits_tree.insert(
                "",
                "end",
                values=(pid, nom, ref, cat, f"{pv:.2f}", qte, actif)
            )

        self.prod_selected_id = None

    def produits_on_select(self):
        sel = self.produits_tree.selection()
        if not sel:
            return
        vals = self.produits_tree.item(sel[0]).get("values") or []
        if not vals:
            return
        pid = vals[0]
        try:
            pid = int(pid)
        except Exception:
            return

        row = self.produits_rows.get(pid)
        if not row:
            return

        self.prod_selected_id = pid

        self.prod_cb_entry.delete(0, "end")
        self.prod_cb_entry.insert(0, row["code_barres"] or "")

        self.prod_ref_entry.delete(0, "end")
        self.prod_ref_entry.insert(0, row["reference"] or "")

        self.prod_nom_entry.delete(0, "end")
        self.prod_nom_entry.insert(0, row["nom"] or "")

        self.prod_cat_entry.delete(0, "end")
        self.prod_cat_entry.insert(0, row["categorie"] or "")

        self.prod_pa_entry.delete(0, "end")
        self.prod_pa_entry.insert(0, f"{float(row['prix_achat'] or 0):.2f}")

        self.prod_pv_entry.delete(0, "end")
        self.prod_pv_entry.insert(0, f"{float(row['prix_vente'] or 0):.2f}")

        self.prod_qte_entry.delete(0, "end")
        self.prod_qte_entry.insert(0, str(int(row["quantite"] or 0)))

        self.prod_seuil_entry.delete(0, "end")
        self.prod_seuil_entry.insert(0, str(int(row["seuil_alerte"] or 0)))

        self.prod_actif_var.set(bool(row["actif"]))

    def produits_nouveau(self):
        self.prod_selected_id = None
        for e in [
            self.prod_cb_entry,
            self.prod_ref_entry,
            self.prod_nom_entry,
            self.prod_cat_entry,
            self.prod_pa_entry,
            self.prod_pv_entry,
            self.prod_qte_entry,
            self.prod_seuil_entry,
        ]:
            e.delete(0, "end")
        self.prod_actif_var.set(True)

    def produits_enregistrer(self):
        if not self.demander_admin():
            return

        nom = (self.prod_nom_entry.get() or "").strip()
        if not nom:
            messagebox.showwarning("Produits", "Le nom du produit est obligatoire.", parent=self.root)
            return

        code_barres = (self.prod_cb_entry.get() or "").strip()
        ref = (self.prod_ref_entry.get() or "").strip()
        cat = (self.prod_cat_entry.get() or "").strip()

        try:
            pa = float((self.prod_pa_entry.get() or "0").replace(",", "."))
        except ValueError:
            pa = 0.0
        try:
            pv = float((self.prod_pv_entry.get() or "0").replace(",", "."))
        except ValueError:
            pv = 0.0
        try:
            qte = int(self.prod_qte_entry.get() or "0")
        except ValueError:
            qte = 0
        try:
            seuil = int(self.prod_seuil_entry.get() or "0")
        except ValueError:
            seuil = 0

        actif = self.prod_actif_var.get()

        try:
            if self.prod_selected_id is None:
                self.db.ajouter_produit(
                    nom=nom,
                    code_barres=code_barres,
                    reference=ref,
                    categorie=cat,
                    description="",
                    prix_achat=pa,
                    prix_vente=pv,
                    quantite=qte,
                    seuil_alerte=seuil
                )
                messagebox.showinfo("Produits", "Produit ajouté.", parent=self.root)
            else:
                self.db.modifier_produit(
                    produit_id=self.prod_selected_id,
                    nom=nom,
                    code_barres=code_barres,
                    reference=ref,
                    categorie=cat,
                    prix_achat=pa,
                    prix_vente=pv,
                    quantite=qte,
                    seuil_alerte=seuil,
                    actif=actif
                )
                messagebox.showinfo("Produits", "Produit modifié.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Produits", f"Erreur enregistrement produit : {e}", parent=self.root)
            return

        self.charger_produits()

    def produits_supprimer(self):
        if self.prod_selected_id is None:
            messagebox.showwarning("Produits", "Sélectionnez un produit à supprimer.", parent=self.root)
            return

        if not self.demander_admin():
            return

        if not messagebox.askyesno(
            "Produits",
            "Supprimer ce produit du stock ?\n"
            "Il sera désactivé et restera dans l'historique des ventes/achats.",
            parent=self.root
        ):
            return

        try:
            # Désactiver le produit pour éviter les erreurs de clés étrangères
            self.db.modifier_produit(
                produit_id=self.prod_selected_id,
                actif=False
            )
        except Exception as e:
            messagebox.showerror("Produits", f"Erreur lors de la suppression du produit : {e}", parent=self.root)
            return

        messagebox.showinfo("Produits", "Produit supprimé du stock (désactivé).", parent=self.root)
        self.produits_nouveau()
        self.charger_produits()

    def produits_adjust_stock(self, sens: int):
        if self.prod_selected_id is None:
            messagebox.showwarning("Produits", "Sélectionnez un produit.", parent=self.root)
            return

        if not self.demander_admin():
            return

        txt = "ajouter au" if sens > 0 else "retirer du"
        try:
            delta = simpledialog.askinteger(
                "Stock",
                f"Quantité à {txt} stock :",
                parent=self.root,
                minvalue=1
            )
        except Exception:
            delta = None

        if not delta:
            return

        if sens < 0:
            delta = -delta

        try:
            self.db.modifier_stock(self.prod_selected_id, delta)
        except Exception as e:
            messagebox.showerror("Stock", f"Erreur ajustement stock : {e}", parent=self.root)
            return

        self.charger_produits()
        messagebox.showinfo("Stock", "Stock mis à jour.", parent=self.root)

    # ========= BON D'ACHAT & FACTURE DE VENTE (PRODUITS) =========

    def produits_bon_achat(self):
        """
        Ouvre la fenêtre complète de bon / facture d'achat (AchatDialog).
        """
        if not self.demander_admin():
            return

        dlg = AchatDialog(self.root, self.db, store_name=self.store_name, store_tel=self.store_tel)
        if dlg.result:
            # Le stock ayant été mis à jour, on recharge la liste des produits.
            self.charger_produits()

    def produits_bon_vente(self):
        """
        Ouvre la fenêtre de facture / bon de vente détaillé (VenteDialog)
        à partir des produits en stock.
        """
        dlg = VenteDialog(
            self.root,
            self.db,
            store_name=self.store_name,
            store_tel=self.store_tel
        )
        if dlg.result:
            # Le stock peut avoir été modifié, on recharge.
            self.charger_produits()

    # ==========================================================
    #  VENTE AU COMPTOIR (page simple, ticket rapide)
    # ==========================================================

    def _build_page_vente(self):
        top = ctk.CTkFrame(self.page_vente, fg_color="white")
        top.pack(fill="x", padx=20, pady=(10, 5))

        ctk.CTkButton(
            top, text="← Accueil", command=self.show_accueil,
            fg_color="#cccccc", hover_color="#b0b0b0",
            text_color="#000000", width=100
        ).pack(side="left")

        ctk.CTkLabel(
            top, text="Vente au comptoir",
            fg_color="white", text_color="#d84315",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=20)

        main = ctk.CTkFrame(self.page_vente, fg_color="white")
        main.pack(fill="both", expand=True, padx=20, pady=5)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # ---------------- COLONNE GAUCHE : PRODUITS ----------------
        left = ctk.CTkFrame(main, fg_color="white")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left.grid_rowconfigure(2, weight=1)

        code_frame = ctk.CTkFrame(left, fg_color="white")
        code_frame.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        code_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(code_frame, text="Code-barres :", text_color="#000000").grid(
            row=0, column=0, padx=5, pady=3, sticky="w"
        )
        self.vente_code_entry = ctk.CTkEntry(code_frame, width=180)
        self.vente_code_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        self.vente_code_entry.bind("<Return>", lambda e: self.vente_ajouter_par_code())

        ctk.CTkButton(
            code_frame,
            text="OK",
            width=60,
            fg_color="#d84315",
            hover_color="#bf360c",
            text_color="white",
            command=self.vente_ajouter_par_code
        ).grid(row=0, column=2, padx=5, pady=3)

        search_frame = ctk.CTkFrame(left, fg_color="white")
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 3))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="Recherche produit :", text_color="#000000").grid(
            row=0, column=0, padx=5, pady=3, sticky="w"
        )
        self.vente_recherche_var = tk.StringVar()
        self.vente_recherche_entry = ctk.CTkEntry(search_frame, textvariable=self.vente_recherche_var, width=200)
        self.vente_recherche_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        self.vente_recherche_entry.bind("<Return>", lambda e: self.vente_actualiser_produits())

        ctk.CTkButton(
            search_frame,
            text="Chercher",
            width=80,
            fg_color="#d84315",
            hover_color="#bf360c",
            text_color="white",
            command=self.vente_actualiser_produits
        ).grid(row=0, column=2, padx=5, pady=3)

        produits_frame = ctk.CTkFrame(left, fg_color="white")
        produits_frame.grid(row=2, column=0, sticky="nsew")
        cols = ("id", "nom", "prix", "stock")
        self.vente_produits_tree = ttk.Treeview(produits_frame, columns=cols, show="headings", height=10)
        self.vente_produits_tree.heading("id", text="ID")
        self.vente_produits_tree.heading("nom", text="Produit")
        self.vente_produits_tree.heading("prix", text="Prix")
        self.vente_produits_tree.heading("stock", text="Stock")

        self.vente_produits_tree.column("id", width=40, anchor="center")
        self.vente_produits_tree.column("nom", width=180, anchor="w")
        self.vente_produits_tree.column("prix", width=70, anchor="e")
        self.vente_produits_tree.column("stock", width=60, anchor="e")

        vsb = ttk.Scrollbar(produits_frame, orient="vertical", command=self.vente_produits_tree.yview)
        self.vente_produits_tree.configure(yscrollcommand=vsb.set)

        self.vente_produits_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.vente_produits_tree.bind("<Double-1>", lambda e: self.vente_ajouter_produit_selection())

        qte_frame = ctk.CTkFrame(left, fg_color="white")
        qte_frame.grid(row=3, column=0, sticky="ew", pady=(3, 0))
        ctk.CTkLabel(qte_frame, text="Quantité :", text_color="#000000").pack(side="left", padx=5)
        self.vente_qte_entry = ctk.CTkEntry(qte_frame, width=80)
        self.vente_qte_entry.pack(side="left", padx=5)
        self.vente_qte_entry.insert(0, "1")

        ctk.CTkButton(
            qte_frame,
            text="Ajouter au ticket",
            fg_color="#d84315",
            hover_color="#bf360c",
            text_color="white",
            command=self.vente_ajouter_produit_selection
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            qte_frame,
            text="Produit manuel",
            fg_color="#6d4c41",
            hover_color="#4e342e",
            text_color="white",
            command=self.vente_ajouter_produit_manuel
        ).pack(side="left", padx=5)

        # ---------------- COLONNE DROITE : TICKET + PAIEMENT ----------------
        right = ctk.CTkFrame(main, fg_color="white")
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right.grid_rowconfigure(2, weight=1)

        style = ttk.Style(self.page_vente)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "VenteTicket.Treeview",
            background="#FFF3E0",
            fieldbackground="#FFF3E0",
            foreground="#000000",
            rowheight=28,
            font=("Segoe UI", 12, "bold"),
            borderwidth=0,
        )
        style.configure(
            "VenteTicket.Treeview.Heading",
            background="#FFB74D",
            foreground="#4E342E",
            font=("Segoe UI", 11, "bold"),
        )
        style.map(
            "VenteTicket.Treeview",
            background=[("selected", "#FFE082")],
            foreground=[("selected", "#000000")],
        )

        total_bar = ctk.CTkFrame(right, fg_color="#000000")
        total_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 3))

        ctk.CTkLabel(
            total_bar,
            text="TOTAL TICKET :",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=10, pady=4)

        self.vente_total_label = ctk.CTkLabel(
            total_bar,
            text="0.00 DA",
            text_color="#00E676",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.vente_total_label.pack(side="left", padx=10, pady=4)

        ticket_frame = ctk.CTkFrame(right, fg_color="white")
        ticket_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        ctk.CTkLabel(
            ticket_frame,
            text="Ticket de vente",
            text_color="#d84315",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=5, pady=(0, 3))

        self.vente_ticket_tree = ttk.Treeview(
            right,
            columns=("libelle", "qte", "pu", "st"),
            show="headings",
            height=18,
            style="VenteTicket.Treeview"
        )
        self.vente_ticket_tree.heading("libelle", text="Article")
        self.vente_ticket_tree.heading("qte", text="Qté")
        self.vente_ticket_tree.heading("pu", text="PU")
        self.vente_ticket_tree.heading("st", text="Sous-total")

        self.vente_ticket_tree.column("libelle", width=230, anchor="w")
        self.vente_ticket_tree.column("qte", width=70, anchor="e")
        self.vente_ticket_tree.column("pu", width=90, anchor="e")
        self.vente_ticket_tree.column("st", width=110, anchor="e")

        vsb2 = ttk.Scrollbar(right, orient="vertical", command=self.vente_ticket_tree.yview)
        self.vente_ticket_tree.configure(yscrollcommand=vsb2.set)

        self.vente_ticket_tree.grid(row=2, column=0, sticky="nsew", pady=(0, 2))
        vsb2.grid(row=2, column=1, sticky="ns")

        btn_ticket = ctk.CTkFrame(right, fg_color="white")
        btn_ticket.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 2))

        ctk.CTkButton(
            btn_ticket,
            text="Supprimer ligne",
            fg_color="#9e9e9e",
            hover_color="#757575",
            text_color="white",
            command=self.vente_supprimer_ligne
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_ticket,
            text="Vider ticket",
            fg_color="#b71c1c",
            hover_color="#7f0000",
            text_color="white",
            command=self.vente_vider_ticket
        ).pack(side="left", padx=5)

        pay_frame = ctk.CTkFrame(right, fg_color="#fff3e0", corner_radius=10)
        pay_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=3)
        pay_frame.grid_columnconfigure(1, weight=1)

        # Total & paiement
        ctk.CTkLabel(pay_frame, text="Montant payé (DA) :", text_color="#000000").grid(
            row=0, column=0, padx=8, pady=3, sticky="e"
        )
        self.vente_montant_paye_var = tk.StringVar()
        self.vente_montant_paye_entry = ctk.CTkEntry(
            pay_frame, textvariable=self.vente_montant_paye_var, width=120
        )
        self.vente_montant_paye_entry.grid(row=0, column=1, padx=8, pady=3, sticky="w")
        self.vente_montant_paye_entry.bind("<KeyRelease>", lambda e: self.vente_mettre_a_jour_affichage())

        ctk.CTkLabel(pay_frame, text="Monnaie rendue :", text_color="#000000").grid(
            row=1, column=0, padx=8, pady=3, sticky="e"
        )
        self.vente_monnaie_label = ctk.CTkLabel(pay_frame, text="0.00 DA", text_color="#000000")
        self.vente_monnaie_label.grid(row=1, column=1, padx=8, pady=3, sticky="w")

        ctk.CTkLabel(pay_frame, text="Mode de paiement :", text_color="#000000").grid(
            row=2, column=0, padx=8, pady=3, sticky="e"
        )
        self.vente_mode_var = tk.StringVar(value="Espèces")
        self.vente_mode_menu = ctk.CTkOptionMenu(
            pay_frame,
            variable=self.vente_mode_var,
            values=["Espèces", "Carte", "Chèque", "Autre"],
            width=140
        )
        self.vente_mode_menu.grid(row=2, column=1, padx=8, pady=3, sticky="w")

        # Caisse
        ctk.CTkLabel(pay_frame, text="Caisse :", text_color="#000000").grid(
            row=3, column=0, padx=8, pady=3, sticky="e"
        )
        self.vente_caisse_var = tk.StringVar()
        self.vente_caisse_map = {}
        self.vente_caisse_menu = ctk.CTkOptionMenu(
            pay_frame,
            variable=self.vente_caisse_var,
            values=[],
            command=self.vente_on_caisse_change,
            width=200
        )
        self.vente_caisse_menu.grid(row=3, column=1, padx=8, pady=3, sticky="w")

        ctk.CTkLabel(pay_frame, text="Nom client (facultatif) :", text_color="#000000").grid(
            row=4, column=0, padx=8, pady=3, sticky="e"
        )
        self.vente_client_entry = ctk.CTkEntry(pay_frame, width=200)
        self.vente_client_entry.grid(row=4, column=1, padx=8, pady=3, sticky="w")

        ctk.CTkButton(
            pay_frame,
            text="Valider la vente",
            fg_color="#d84315",
            hover_color="#bf360c",
            text_color="white",
            command=self.vente_valider
        ).grid(row=5, column=0, columnspan=2, pady=(4, 6))

    # LOGIQUE VENTE AU COMPTOIR --------------------------------

    def vente_actualiser_produits(self):
        terme = (self.vente_recherche_var.get() or "").strip()
        try:
            if terme:
                rows = self.db.rechercher_produits(terme, uniquement_actifs=True)
            else:
                rows = self.db.get_produits(uniquement_actifs=True)
        except Exception as e:
            messagebox.showerror("Vente", f"Erreur lecture produits : {e}", parent=self.root)
            return

        self.vente_produits_tree.delete(*self.vente_produits_tree.get_children())
        for p in rows:
            pid = p["id"]
            nom = p["nom"] or ""
            pv = float(p["prix_vente"] or 0)
            qte = int(p["quantite"] or 0)
            self.vente_produits_tree.insert(
                "",
                "end",
                values=(pid, nom, f"{pv:.2f}", qte)
            )

    def vente_actualiser_caisses(self):
        try:
            caisses = self.db.get_caisses()
        except Exception as e:
            messagebox.showerror("Vente", f"Erreur lecture caisses : {e}", parent=self.root)
            return

        self.vente_caisse_map = {}
        values = []
        for row in caisses:
            cid, nom, desc = row
            label = f"{cid} - {nom}"
            values.append(label)
            self.vente_caisse_map[label] = cid

        self.vente_caisse_menu.configure(values=values)

        if self.caisse_selectionnee_id is not None:
            for lbl, cid in self.vente_caisse_map.items():
                if cid == self.caisse_selectionnee_id:
                    self.vente_caisse_menu.set(lbl)
                    break
            else:
                if values:
                    self.vente_caisse_menu.set(values[0])
                    self.caisse_selectionnee_id = self.vente_caisse_map[values[0]]
        else:
            if values:
                self.vente_caisse_menu.set(values[0])
                self.caisse_selectionnee_id = self.vente_caisse_map[values[0]]

    def vente_on_caisse_change(self, choice: str):
        if not choice:
            return
        cid = self.vente_caisse_map.get(choice)
        if cid:
            self.caisse_selectionnee_id = cid

    def vente_ajouter_par_code(self):
        code = (self.vente_code_entry.get() or "").strip()
        if not code:
            return
        try:
            row = self.db.rechercher_produit_par_code(code)
        except Exception as e:
            messagebox.showerror("Vente", f"Erreur recherche code-barres : {e}", parent=self.root)
            return

        if not row:
            messagebox.showwarning("Vente", "Aucun produit trouvé avec ce code-barres.", parent=self.root)
            return

        pid, nom, prix, stock, cb, seuil = row
        try:
            qte = int((self.vente_qte_entry.get() or "1"))
        except ValueError:
            qte = 1
        if qte <= 0:
            qte = 1

        if stock is not None and qte > stock:
            messagebox.showwarning("Vente", "Quantité demandée supérieure au stock.", parent=self.root)
            return

        self._vente_ajouter_item(pid, nom, prix, qte)
        self.vente_code_entry.delete(0, "end")

    def vente_ajouter_produit_selection(self):
        sel = self.vente_produits_tree.selection()
        if not sel:
            messagebox.showwarning("Vente", "Sélectionnez un produit dans la liste.", parent=self.root)
            return
        vals = self.vente_produits_tree.item(sel[0]).get("values") or []
        if len(vals) < 4:
            return
        pid, nom, pv_str, stock = vals
        try:
            prix = float(str(pv_str).replace(",", "."))
        except ValueError:
            prix = 0.0

        try:
            qte = int((self.vente_qte_entry.get() or "1"))
        except ValueError:
            qte = 1
        if qte <= 0:
            qte = 1

        if stock is not None and qte > int(stock):
            messagebox.showwarning("Vente", "Quantité demandée supérieure au stock.", parent=self.root)
            return

        self._vente_ajouter_item(pid, nom, prix, qte)

    def _vente_ajouter_item(self, produit_id, nom, prix, qte):
        trouve = False
        for it in self.vente_panier:
            if it.get("produit_id") == produit_id and it.get("prix_unitaire") == prix:
                it["quantite"] += qte
                it["sous_total"] = it["quantite"] * it["prix_unitaire"]
                trouve = True
                break

        if not trouve:
            self.vente_panier.append({
                "produit_id": produit_id,
                "nom": nom,
                "quantite": qte,
                "prix_unitaire": prix,
                "sous_total": qte * prix
            })

        self.vente_mettre_a_jour_affichage()

    def vente_ajouter_produit_manuel(self):
        dlg = ManualProductDialog(self.root)
        if not dlg.result:
            return
        nom, prix, qte = dlg.result
        self.vente_panier.append({
            "produit_id": None,
            "nom": nom,
            "quantite": qte,
            "prix_unitaire": prix,
            "sous_total": prix * qte
        })
        self.vente_mettre_a_jour_affichage()

    def vente_mettre_a_jour_affichage(self):
        self.vente_ticket_tree.delete(*self.vente_ticket_tree.get_children())
        total = 0.0
        for i, it in enumerate(self.vente_panier):
            lib = it.get("nom") or ""
            qte = it.get("quantite") or 0
            pu = it.get("prix_unitaire") or 0
            st = it.get("sous_total") or 0
            total += float(st)
            self.vente_ticket_tree.insert(
                "",
                "end",
                iid=str(i),
                values=(lib, qte, f"{pu:.2f}", f"{st:.2f}")
            )

        self.vente_total = total
        self.vente_total_label.configure(text=f"{total:.2f} DA")

        try:
            mp = float((self.vente_montant_paye_var.get() or "0").replace(",", "."))
        except ValueError:
            mp = 0.0
        monnaie = mp - total if mp >= total else 0.0
        self.vente_monnaie_label.configure(text=f"{monnaie:.2f} DA")

    def vente_supprimer_ligne(self):
        sel = self.vente_ticket_tree.selection()
        if not sel:
            return
        iid = sel[0]
        try:
            idx = int(iid)
        except ValueError:
            return
        if 0 <= idx < len(self.vente_panier):
            self.vente_panier.pop(idx)
        self.vente_mettre_a_jour_affichage()

    def vente_vider_ticket(self):
        self.vente_panier.clear()
        self.vente_montant_paye_var.set("")
        self.vente_mettre_a_jour_affichage()

    def vente_valider(self):
        if not self.vente_panier:
            messagebox.showwarning("Vente", "Le ticket est vide.", parent=self.root)
            return

        if not self.caisse_selectionnee_id:
            messagebox.showwarning("Vente", "Aucune caisse sélectionnée.", parent=self.root)
            return

        try:
            total = float(self.vente_total or 0)
        except ValueError:
            total = 0.0

        try:
            mp = float((self.vente_montant_paye_var.get() or "0").replace(",", "."))
        except ValueError:
            mp = 0.0

        monnaie = mp - total if mp >= total else 0.0
        reste = total - mp if mp < total else 0.0

        mode = getattr(self, "vente_mode_var", tk.StringVar(value="Espèces")).get() or "Espèces"
        client_nom = getattr(self, "vente_client_entry", tk.Entry()).get().strip() or None

        # Crédit client si paiement partiel
        if reste > 0.01:
            dlg = CreditClientDialog(self.root, self.db, reste_du=reste)
            if not dlg.result:
                messagebox.showinfo("Vente", "Vente annulée (client pour crédit non sélectionné).", parent=self.root)
                return
            client_nom = dlg.result

        try:
            vente_id = self.db.enregistrer_vente_comptoir(
                caisse_id=self.caisse_selectionnee_id,
                items=self.vente_panier,
                mode_paiement=mode,
                montant_paye=mp,
                monnaie_rendue=monnaie,
                client_nom=client_nom
            )
        except Exception as e:
            messagebox.showerror("Vente", f"Erreur enregistrement vente : {e}", parent=self.root)
            return

        # Mouvement de caisse (ENTREE)
        if mp > 0:
            try:
                self.db.ajouter_mouvement_caisse(
                    caisse_id=self.caisse_selectionnee_id,
                    type_mvt="ENTREE",
                    montant=mp,
                    description=f"Vente comptoir N°{vente_id}"
                )
            except Exception as e:
                messagebox.showerror("Vente", f"Vente OK mais erreur mouvement caisse : {e}", parent=self.root)

        # Créance si paiement partiel
        if reste > 0.01:
            try:
                self.db.ajouter_creance(
                    client_nom=client_nom or "Client inconnu",
                    pc_marque="",
                    description=f"Vente comptoir N°{vente_id}",
                    montant_total=total,
                    montant_paye=mp,
                    montant_restant=reste,
                    date_retrait=datetime.now().strftime("%d/%m/%Y"),
                    ticket_id=None
                )
            except Exception as e:
                messagebox.showerror("Vente", f"Vente OK mais erreur enregistrement créance : {e}", parent=self.root)

        messagebox.showinfo("Vente", f"Vente enregistrée (N° {vente_id}).", parent=self.root)
        self.vente_vider_ticket()
        self.vente_actualiser_produits()

    # RUN ------------------------------------------------------

    def run(self):
        self.root.mainloop()
        self.db.close()
