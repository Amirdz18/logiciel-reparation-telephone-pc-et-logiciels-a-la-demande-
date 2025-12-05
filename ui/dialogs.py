import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import os
import tempfile
import subprocess

import customtkinter as ctk

from database import Database


class CreditClientDialog(ctk.CTkToplevel):
    """Fenêtre pour choisir / créer un client lors d'une vente à crédit."""
    def __init__(self, parent, db: Database, reste_du: float):
        super().__init__(parent)
        self.db = db
        self.reste_du = reste_du
        self.result = None

        self.title("Client pour vente à crédit")
        self.geometry("600x400")
        self.resizable(False, False)
        try:
            self.configure(fg_color="#E3F2FD")
        except Exception:
            pass

        self._build_ui()
        self._charger_clients()

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._select_existing())
        self.wait_window(self)

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="#E3F2FD", corner_radius=10)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        header = ctk.CTkFrame(main, fg_color="#1565C0", corner_radius=10)
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text="Vente à crédit",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FFFFFF",
        ).pack(anchor="w", padx=10, pady=(5, 0))
        ctk.CTkLabel(
            header,
            text=f"Reste dû : {self.reste_du:.2f} DA",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#BBDEFB",
        ).pack(anchor="w", padx=10, pady=(0, 5))
        ctk.CTkLabel(
            header,
            text="Choisissez un client existant ou créez un nouveau client pour enregistrer la créance.",
            font=ctk.CTkFont(size=11),
            text_color="#E3F2FD",
        ).pack(anchor="w", padx=10, pady=(0, 8))

        new_frame = ctk.CTkFrame(main, fg_color="#FFFFFF", corner_radius=10)
        new_frame.pack(fill="x", pady=(0, 10), padx=4)
        ctk.CTkLabel(
            new_frame,
            text="Nouveau client (si le client n'existe pas encore) :",
            text_color="#000000",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(8, 2), sticky="w")

        ctk.CTkLabel(new_frame, text="Nom du client * :", text_color="#000000").grid(
            row=1, column=0, padx=10, pady=4, sticky="e"
        )
        self.new_nom = ctk.CTkEntry(new_frame, width=250, placeholder_text="Nom et prénom...")
        self.new_nom.grid(row=1, column=1, padx=10, pady=4, sticky="w")

        ctk.CTkLabel(new_frame, text="Téléphone :", text_color="#000000").grid(
            row=2, column=0, padx=10, pady=4, sticky="e"
        )
        self.new_tel = ctk.CTkEntry(new_frame, width=250, placeholder_text="Téléphone (optionnel)")
        self.new_tel.grid(row=2, column=1, padx=10, pady=4, sticky="w")

        btn_new = ctk.CTkButton(
            new_frame,
            text="Créer et utiliser ce client",
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            text_color="white",
            command=self._create_new_client,
            width=200,
        )
        btn_new.grid(row=3, column=0, columnspan=2, pady=(8, 8))

        ctk.CTkLabel(
            main,
            text="Ou sélectionner un client existant :",
            text_color="#000000",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(0, 4))

        list_frame = ctk.CTkFrame(main, fg_color="#FFFFFF", corner_radius=10)
        list_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        list_frame.rowconfigure(1, weight=1)
        list_frame.columnconfigure(0, weight=1)

        search_frame = ctk.CTkFrame(list_frame, fg_color="#FFFFFF")
        search_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="Recherche (nom ou téléphone) :", text_color="#000000").grid(
            row=0, column=0, padx=(4, 4), pady=4, sticky="w"
        )
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=200)
        self.search_entry.grid(row=0, column=1, padx=(0, 4), pady=4, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self._charger_clients())

        btn_search = ctk.CTkButton(
            search_frame,
            text="Rechercher",
            width=100,
            command=self._charger_clients,
        )
        btn_search.grid(row=0, column=2, padx=(4, 4), pady=4)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("id", "nom", "tel"),
            show="headings",
            selectmode="browse",
            height=6
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 6))
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.heading("id", text="ID")
        self.tree.heading("nom", text="Nom")
        self.tree.heading("tel", text="Téléphone")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("nom", width=280, anchor="w")
        self.tree.column("tel", width=180, anchor="w")

        btns = ctk.CTkFrame(main, fg_color="#E3F2FD")
        btns.pack(fill="x", pady=(2, 0))
        ctk.CTkButton(
            btns,
            text="Utiliser le client sélectionné",
            fg_color="#4CAF50",
            hover_color="#388E3C",
            text_color="white",
            command=self._select_existing,
            width=200,
        ).pack(side="left", padx=(10, 4), pady=4)
        ctk.CTkButton(
            btns,
            text="Annuler",
            fg_color="#9E9E9E",
            hover_color="#757575",
            text_color="white",
            command=self._cancel,
            width=120,
        ).pack(side="right", padx=(4, 10), pady=4)

    def _charger_clients(self):
        search = (self.search_var.get() or "").strip().lower()
        try:
            rows = self.db.get_clients()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les clients : {e}", parent=self)
            return

        self.tree.delete(*self.tree.get_children())
        for row in rows:
            cid, nom, prenom, tel, email, adr = row
            full_nom = (nom or "") + ((" " + prenom) if prenom else "")
            if search:
                txt = (full_nom + " " + (tel or "")).lower()
                if search not in txt:
                    continue
            self.tree.insert("", "end", values=(cid, full_nom, tel or ""))

    def _create_new_client(self):
        nom = (self.new_nom.get() or "").strip()
        tel = (self.new_tel.get() or "").strip()

        if not nom:
            messagebox.showwarning("Client", "Le nom du client est obligatoire.", parent=self)
            return

        try:
            self.db.ajouter_client(nom=nom, prenom="", telephone=tel, email="", adresse="")
        except Exception as e:
            messagebox.showerror("Client", f"Erreur lors de la création du client : {e}", parent=self)
            return

        self.result = nom
        self.destroy()

    def _select_existing(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Client", "Sélectionnez un client ou créez-en un nouveau.", parent=self)
            return
        item = self.tree.item(sel[0])
        vals = item.get("values") or []
        full_nom = vals[1] if len(vals) > 1 else ""
        if not full_nom:
            messagebox.showerror("Client", "Client invalide.", parent=self)
            return
        self.result = full_nom
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class ManualProductDialog(ctk.CTkToplevel):
    """Fenêtre pour ajouter un produit manuel (hors stock) au ticket de vente."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Produit manuel")
        self.geometry("400x260")
        self.resizable(False, False)
        try:
            self.configure(fg_color="#FFF3E0")
        except Exception:
            pass

        self.result = None
        self._build_ui()

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._ok())
        self.wait_window(self)

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="#FFF3E0", corner_radius=10)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            main,
            text="Ajouter un produit manuel",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#BF360C",
        ).pack(pady=(5, 10))

        form = ctk.CTkFrame(main, fg_color="#FFF3E0")
        form.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(form, text="Nom du produit * :", text_color="#000000").grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )
        self.ent_nom = ctk.CTkEntry(form, width=220, placeholder_text="Nom de l'article...")
        self.ent_nom.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(form, text="Prix unitaire (DA) * :", text_color="#000000").grid(
            row=1, column=0, padx=5, pady=5, sticky="e"
        )
        self.ent_prix = ctk.CTkEntry(form, width=120, placeholder_text="0.00")
        self.ent_prix.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(form, text="Quantité * :", text_color="#000000").grid(
            row=2, column=0, padx=5, pady=5, sticky="e"
        )
        self.ent_qte = ctk.CTkEntry(form, width=80, placeholder_text="1")
        self.ent_qte.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.ent_qte.insert(0, "1")

        btns = ctk.CTkFrame(main, fg_color="#FFF3E0")
        btns.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            btns,
            text="Annuler",
            fg_color="#9E9E9E",
            hover_color="#757575",
            text_color="white",
            command=self._cancel,
            width=120,
        ).pack(side="left", padx=10, pady=4)

        ctk.CTkButton(
            btns,
            text="Valider",
            fg_color="#F57C00",
            hover_color="#E65100",
            text_color="white",
            command=self._ok,
            width=160,
        ).pack(side="right", padx=10, pady=4)

        self.ent_nom.focus_set()

    def _ok(self):
        nom = (self.ent_nom.get() or "").strip()
        if not nom:
            messagebox.showwarning("Produit manuel", "Le nom du produit est obligatoire.", parent=self)
            return

        try:
            prix = float((self.ent_prix.get() or "0").replace(",", "."))
        except ValueError:
            messagebox.showwarning("Produit manuel", "Prix invalide.", parent=self)
            return
        if prix <= 0:
            messagebox.showwarning("Produit manuel", "Le prix doit être > 0.", parent=self)
            return

        try:
            qte = int((self.ent_qte.get() or "0"))
        except ValueError:
            messagebox.showwarning("Produit manuel", "Quantité invalide (entier).", parent=self)
            return
        if qte <= 0:
            messagebox.showwarning("Produit manuel", "La quantité doit être >= 1.", parent=self)
            return

        self.result = (nom, prix, qte)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class AchatNewProductDialog(ctk.CTkToplevel):
    """
    Fenêtre pour créer rapidement un produit (ajout au stock)
    directement depuis le bon / facture d'achat.
    """
    def __init__(self, parent, db: Database, default_name: str = ""):
        super().__init__(parent)
        self.db = db
        self.result = None  # dict {id, nom, prix_achat, prix_vente, quantite}
        self.title("Nouveau produit (achat)")
        self.geometry("480x360")
        self.resizable(False, False)
        try:
            self.configure(fg_color="#E8F5E9")
        except Exception:
            pass

        self._build_ui(default_name)

        # --- affichage au-dessus + centrage + focus ---
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        try:
            if parent is not None:
                px = parent.winfo_rootx()
                py = parent.winfo_rooty()
                pw = parent.winfo_width()
                ph = parent.winfo_height()
                sw = self.winfo_width()
                sh = self.winfo_height()
                x = px + (pw - sw) // 2
                y = py + (ph - sh) // 2
                self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self.lift()
        self.focus_force()
        self.after(100, self.lift)

        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._ok())
        self.wait_window(self)

    def _build_ui(self, default_name: str):
        main = ctk.CTkFrame(self, fg_color="#E8F5E9", corner_radius=10)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            main,
            text="Créer un nouveau produit pour le stock",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2E7D32",
        ).pack(pady=(5, 10))

        form = ctk.CTkFrame(main, fg_color="#E8F5E9")
        form.pack(fill="x", padx=5, pady=5)

        # Nom
        ctk.CTkLabel(form, text="Nom du produit * :", text_color="#000000").grid(
            row=0, column=0, padx=5, pady=4, sticky="e"
        )
        self.ent_nom = ctk.CTkEntry(form, width=260, placeholder_text="Nom du produit...")
        self.ent_nom.grid(row=0, column=1, padx=5, pady=4, sticky="w")
        if default_name:
            self.ent_nom.insert(0, default_name)

        # Code-barres
        ctk.CTkLabel(form, text="Code-barres :", text_color="#000000").grid(
            row=1, column=0, padx=5, pady=4, sticky="e"
        )
        self.ent_code = ctk.CTkEntry(form, width=180, placeholder_text="Optionnel")
        self.ent_code.grid(row=1, column=1, padx=5, pady=4, sticky="w")

        # Référence
        ctk.CTkLabel(form, text="Référence :", text_color="#000000").grid(
            row=2, column=0, padx=5, pady=4, sticky="e"
        )
        self.ent_ref = ctk.CTkEntry(form, width=180, placeholder_text="Optionnel")
        self.ent_ref.grid(row=2, column=1, padx=5, pady=4, sticky="w")

        # Catégorie
        ctk.CTkLabel(form, text="Catégorie :", text_color="#000000").grid(
            row=3, column=0, padx=5, pady=4, sticky="e"
        )
        self.ent_cat = ctk.CTkEntry(form, width=180, placeholder_text="Optionnel (PC, Accessoire...)")
        self.ent_cat.grid(row=3, column=1, padx=5, pady=4, sticky="w")

        # Prix achat
        ctk.CTkLabel(form, text="Prix achat (DA) * :", text_color="#000000").grid(
            row=4, column=0, padx=5, pady=4, sticky="e"
        )
        self.ent_pa = ctk.CTkEntry(form, width=120, placeholder_text="0.00")
        self.ent_pa.grid(row=4, column=1, padx=5, pady=4, sticky="w")

        # Prix vente
        ctk.CTkLabel(form, text="Prix vente (DA) * :", text_color="#000000").grid(
            row=5, column=0, padx=5, pady=4, sticky="e"
        )
        self.ent_pv = ctk.CTkEntry(form, width=120, placeholder_text="0.00")
        self.ent_pv.grid(row=5, column=1, padx=5, pady=4, sticky="w")

        # Quantité pour cette facture
        ctk.CTkLabel(form, text="Quantité (pour cette facture) * :", text_color="#000000").grid(
            row=6, column=0, padx=5, pady=4, sticky="e"
        )
        self.ent_qte = ctk.CTkEntry(form, width=80, placeholder_text="1")
        self.ent_qte.grid(row=6, column=1, padx=5, pady=4, sticky="w")
        self.ent_qte.insert(0, "1")

        # Seuil alerte
        ctk.CTkLabel(form, text="Seuil alerte stock :", text_color="#000000").grid(
            row=7, column=0, padx=5, pady=4, sticky="e"
        )
        self.ent_seuil = ctk.CTkEntry(form, width=80, placeholder_text="0")
        self.ent_seuil.grid(row=7, column=1, padx=5, pady=4, sticky="w")

        btns = ctk.CTkFrame(main, fg_color="#E8F5E9")
        btns.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            btns,
            text="Annuler",
            fg_color="#9E9E9E",
            hover_color="#757575",
            text_color="white",
            command=self._cancel,
            width=120,
        ).pack(side="left", padx=10, pady=4)

        ctk.CTkButton(
            btns,
            text="Créer et ajouter à la facture",
            fg_color="#388E3C",
            hover_color="#2E7D32",
            text_color="white",
            command=self._ok,
            width=220,
        ).pack(side="right", padx=10, pady=4)

        self.ent_nom.focus_set()

    def _ok(self):
        nom = (self.ent_nom.get() or "").strip()
        if not nom:
            messagebox.showwarning("Produit", "Le nom du produit est obligatoire.", parent=self)
            return

        code = (self.ent_code.get() or "").strip()
        ref = (self.ent_ref.get() or "").strip()
        cat = (self.ent_cat.get() or "").strip()

        try:
            pa = float((self.ent_pa.get() or "0").replace(",", "."))
        except ValueError:
            messagebox.showwarning("Produit", "Prix d'achat invalide.", parent=self)
            return
        if pa <= 0:
            messagebox.showwarning("Produit", "Le prix d'achat doit être > 0.", parent=self)
            return

        try:
            pv = float((self.ent_pv.get() or "0").replace(",", "."))
        except ValueError:
            messagebox.showwarning("Produit", "Prix de vente invalide.", parent=self)
            return
        if pv <= 0:
            messagebox.showwarning("Produit", "Le prix de vente doit être > 0.", parent=self)
            return

        try:
            qte = int((self.ent_qte.get() or "0"))
        except ValueError:
            messagebox.showwarning("Produit", "Quantité invalide (entier).", parent=self)
            return
        if qte <= 0:
            messagebox.showwarning("Produit", "La quantité doit être >= 1.", parent=self)
            return

        try:
            seuil_str = (self.ent_seuil.get() or "0")
            seuil = int(seuil_str) if seuil_str.strip() != "" else 0
        except ValueError:
            messagebox.showwarning("Produit", "Seuil d'alerte invalide (entier).", parent=self)
            return

        try:
            # On crée le produit en base avec quantite initiale = 0.
            # Le stock sera augmenté par cette facture d'achat (dans AchatDialog._valider).
            pid = self.db.ajouter_produit(
                nom=nom,
                code_barres=code,
                reference=ref,
                categorie=cat,
                description="",
                prix_achat=pa,
                prix_vente=pv,
                quantite=0,
                seuil_alerte=seuil
            )
        except Exception as e:
            messagebox.showerror("Produit", f"Erreur lors de la création du produit : {e}", parent=self)
            return

        self.result = {
            "id": pid,
            "nom": nom,
            "prix_achat": pa,
            "prix_vente": pv,
            "quantite": qte
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class AchatDialog(ctk.CTkToplevel):
    """Bon / facture d'achat : met à jour stock + PA/PV et enregistre le paiement fournisseur."""
    def __init__(self, parent, db: Database, store_name: str = "pyramide", store_tel: str = ""):
        super().__init__(parent)
        self.db = db
        self.store_name = store_name or "pyramide"
        self.store_tel = store_tel or ""
        self.lignes = []  # {produit_id, nom, quantite, prix_achat, prix_vente, sous_total}
        self.result = False

        self.caisses_map = {}
        self.caisse_selectionnee_id = None
        self.achat_caisse_var = tk.StringVar()

        self.title("Bon / facture d'achat")
        self.geometry("1150x620")
        self.resizable(False, False)
        try:
            self.configure(fg_color="#F1F8E9")
        except Exception:
            pass

        self._build_ui()
        self._charger_caisses()
        self._charger_produits()
        self._maj_total()

        # --- affichage au-dessus + centrage + focus ---
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        try:
            if parent is not None:
                px = parent.winfo_rootx()
                py = parent.winfo_rooty()
                pw = parent.winfo_width()
                ph = parent.winfo_height()
                sw = self.winfo_width()
                sh = self.winfo_height()
                x = px + (pw - sw) // 2
                y = py + (ph - sh) // 2
                self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self.lift()
        self.focus_force()
        self.after(100, self.lift)

        self.bind("<Escape>", lambda e: self._cancel())
        # Entrée = ajouter / valider la ligne en cours
        self.bind("<Return>", lambda e: self._ajouter_ligne_depuis_selection())
        self.wait_window(self)

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="#F1F8E9")
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(main, fg_color="#C5E1A5", corner_radius=10)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8), padx=2)
        header.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            header,
            text="Bon / facture d'achat",
            text_color="#33691E",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, padx=10, pady=(6, 2), sticky="w")

        ctk.CTkLabel(header, text="Fournisseur :", text_color="#000000").grid(
            row=1, column=0, padx=8, pady=2, sticky="e"
        )
        self.achat_four_entry = ctk.CTkEntry(header, width=220, placeholder_text="Nom du fournisseur")
        self.achat_four_entry.grid(row=1, column=1, padx=4, pady=2, sticky="w")

        ctk.CTkLabel(header, text="N° facture / bon :", text_color="#000000").grid(
            row=1, column=2, padx=8, pady=2, sticky="e"
        )
        self.achat_num_entry = ctk.CTkEntry(header, width=160, placeholder_text="Fac-2025-001")
        self.achat_num_entry.grid(row=1, column=3, padx=4, pady=2, sticky="w")

        ctk.CTkLabel(header, text="Date :", text_color="#000000").grid(
            row=2, column=0, padx=8, pady=2, sticky="e"
        )
        self.achat_date_entry = ctk.CTkEntry(header, width=120)
        self.achat_date_entry.grid(row=2, column=1, padx=4, pady=2, sticky="w")
        self.achat_date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # Colonne gauche : produits
        left = ctk.CTkFrame(main, fg_color="#F1F8E9")
        left.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 5))
        left.grid_rowconfigure(1, weight=1)

        search_frame = ctk.CTkFrame(left, fg_color="#F1F8E9")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="Recherche produit :", text_color="#000000").grid(
            row=0, column=0, padx=5, pady=3, sticky="w"
        )
        self.achat_search_var = tk.StringVar()
        self.achat_search_entry = ctk.CTkEntry(search_frame, textvariable=self.achat_search_var, width=200)
        self.achat_search_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        self.achat_search_entry.bind("<Return>", lambda e: self._charger_produits())

        ctk.CTkButton(
            search_frame,
            text="Chercher",
            width=80,
            fg_color="#558B2F",
            hover_color="#33691E",
            text_color="white",
            command=self._charger_produits
        ).grid(row=0, column=2, padx=5, pady=3)

        # NOUVEAU PRODUIT (ACHAT)
        ctk.CTkButton(
            search_frame,
            text="Nouveau produit",
            width=120,
            fg_color="#8BC34A",
            hover_color="#689F38",
            text_color="white",
            command=self._nouveau_produit
        ).grid(row=0, column=3, padx=5, pady=3)

        prod_frame = ctk.CTkFrame(left, fg_color="#FFFFFF", corner_radius=8)
        prod_frame.grid(row=1, column=0, sticky="nsew")
        cols = ("id", "nom", "code", "stock", "pa", "pv")
        self.achat_produits_tree = ttk.Treeview(prod_frame, columns=cols, show="headings", height=10)
        self.achat_produits_tree.heading("id", text="ID")
        self.achat_produits_tree.heading("nom", text="Produit")
        self.achat_produits_tree.heading("code", text="Code")
        self.achat_produits_tree.heading("stock", text="Stock")
        self.achat_produits_tree.heading("pa", text="P. achat")
        self.achat_produits_tree.heading("pv", text="P. vente")

        self.achat_produits_tree.column("id", width=40, anchor="center")
        self.achat_produits_tree.column("nom", width=170, anchor="w")
        self.achat_produits_tree.column("code", width=80, anchor="w")
        self.achat_produits_tree.column("stock", width=60, anchor="e")
        self.achat_produits_tree.column("pa", width=80, anchor="e")
        self.achat_produits_tree.column("pv", width=80, anchor="e")

        vsb_prod = ttk.Scrollbar(prod_frame, orient="vertical", command=self.achat_produits_tree.yview)
        self.achat_produits_tree.configure(yscrollcommand=vsb_prod.set)

        self.achat_produits_tree.pack(side="left", fill="both", expand=True)
        vsb_prod.pack(side="right", fill="y")

        self.achat_produits_tree.bind("<Double-1>", lambda e: self._ajouter_ligne_depuis_selection())

        # Milieu : saisie d'une ligne (Qté, PA, PV)
        mid = ctk.CTkFrame(main, fg_color="#F1F8E9")
        mid.grid(row=1, column=1, sticky="nw", padx=(5, 5), pady=(0, 3))

        self.achat_lbl_produit_sel = ctk.CTkLabel(
            mid,
            text="Produit sélectionné : (aucun)",
            text_color="#33691E",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.achat_lbl_produit_sel.grid(row=0, column=0, columnspan=6, padx=5, pady=(0, 3), sticky="w")

        ctk.CTkLabel(mid, text="Quantité * :", text_color="#000000").grid(
            row=1, column=0, padx=5, pady=2, sticky="e"
        )
        self.achat_qte_entry = ctk.CTkEntry(mid, width=80)
        self.achat_qte_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        self.achat_qte_entry.insert(0, "1")

        ctk.CTkLabel(mid, text="Prix achat (DA) * :", text_color="#000000").grid(
            row=1, column=2, padx=5, pady=2, sticky="e"
        )
        self.achat_pa_entry = ctk.CTkEntry(mid, width=90)
        self.achat_pa_entry.grid(row=1, column=3, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(mid, text="Prix vente (DA) * :", text_color="#000000").grid(
            row=1, column=4, padx=5, pady=2, sticky="e"
        )
        self.achat_pv_entry = ctk.CTkEntry(mid, width=90)
        self.achat_pv_entry.grid(row=1, column=5, padx=5, pady=2, sticky="w")

        ctk.CTkButton(
            mid,
            text="Ajouter / valider la ligne",
            fg_color="#558B2F",
            hover_color="#33691E",
            text_color="white",
            command=self._ajouter_ligne_depuis_selection
        ).grid(row=2, column=0, columnspan=6, padx=5, pady=(4, 4), sticky="ew")

        # Colonne droite : lignes facture
        right = ctk.CTkFrame(main, fg_color="#F1F8E9")
        right.grid(row=2, column=1, sticky="nsew", padx=(5, 0))
        right.grid_rowconfigure(0, weight=1)

        lines_frame = ctk.CTkFrame(right, fg_color="#FFFFFF", corner_radius=8)
        lines_frame.grid(row=0, column=0, sticky="nsew")
        cols2 = ("nom", "qte", "pa", "pv", "st")
        self.achat_lignes_tree = ttk.Treeview(lines_frame, columns=cols2, show="headings", height=8)
        self.achat_lignes_tree.heading("nom", text="Article")
        self.achat_lignes_tree.heading("qte", text="Qté")
        self.achat_lignes_tree.heading("pa", text="P. achat")
        self.achat_lignes_tree.heading("pv", text="P. vente")
        self.achat_lignes_tree.heading("st", text="Sous-total")

        self.achat_lignes_tree.column("nom", width=220, anchor="w")
        self.achat_lignes_tree.column("qte", width=60, anchor="e")
        self.achat_lignes_tree.column("pa", width=80, anchor="e")
        self.achat_lignes_tree.column("pv", width=80, anchor="e")
        self.achat_lignes_tree.column("st", width=100, anchor="e")

        vsb_lines = ttk.Scrollbar(lines_frame, orient="vertical", command=self.achat_lignes_tree.yview)
        self.achat_lignes_tree.configure(yscrollcommand=vsb_lines.set)

        self.achat_lignes_tree.pack(side="left", fill="both", expand=True)
        vsb_lines.pack(side="right", fill="y")

        bottom_right = ctk.CTkFrame(right, fg_color="#F1F8E9")
        bottom_right.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        bottom_right.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bottom_right, text="TOTAL HT :", text_color="#000000").grid(
            row=0, column=0, padx=5, pady=2, sticky="e"
        )
        self.achat_total_label = ctk.CTkLabel(
            bottom_right, text="0.00 DA",
            text_color="#33691E",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.achat_total_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(bottom_right, text="Caisse (paiement fournisseur) :", text_color="#000000").grid(
            row=1, column=0, padx=5, pady=2, sticky="e"
        )
        self.achat_caisse_option = ctk.CTkOptionMenu(
            bottom_right,
            variable=self.achat_caisse_var,
            values=[],
            command=self._on_caisse_change,
            width=260
        )
        self.achat_caisse_option.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        btns2 = ctk.CTkFrame(bottom_right, fg_color="#F1F8E9")
        btns2.grid(row=2, column=0, columnspan=2, pady=(2, 0))

        ctk.CTkButton(
            btns2,
            text="Supprimer ligne",
            fg_color="#9E9E9E",
            hover_color="#757575",
            text_color="white",
            command=self._supprimer_ligne
        ).pack(side="left", padx=4, pady=2)

        ctk.CTkButton(
            btns2,
            text="Valider facture (ajouter au stock)",
            fg_color="#558B2F",
            hover_color="#33691E",
            text_color="white",
            command=self._valider
        ).pack(side="left", padx=4, pady=2)

        ctk.CTkButton(
            btns2,
            text="Annuler",
            fg_color="#b71c1c",
            hover_color="#7f0000",
            text_color="white",
            command=self._cancel
        ).pack(side="left", padx=4, pady=2)

    # --- Méthodes AchatDialog supplémentaires ---

    def _nouveau_produit(self):
        """
        Crée un nouveau produit en base et l'ajoute directement
        dans les lignes de la facture d'achat.
        """
        default_name = (self.achat_search_var.get() or "").strip()
        dlg = AchatNewProductDialog(self, self.db, default_name=default_name)
        if not dlg.result:
            return

        pdata = dlg.result  # dict {id, nom, prix_achat, prix_vente, quantite}
        qte = pdata["quantite"]
        pa = pdata["prix_achat"]
        pv = pdata["prix_vente"]
        st = pa * qte

        self.lignes.append({
            "produit_id": pdata["id"],
            "nom": pdata["nom"],
            "quantite": qte,
            "prix_achat": pa,
            "prix_vente": pv,
            "sous_total": st
        })

        # On recharge la liste des produits pour voir le nouveau dans le stock
        self._charger_produits()
        self._rafraichir_lignes()
        self._maj_total()

    def _charger_caisses(self):
        try:
            caisses = self.db.get_caisses()
        except Exception as e:
            messagebox.showerror("Achats", f"Erreur lecture caisses : {e}", parent=self)
            return

        self.caisses_map = {}
        values = []
        for cid, nom, desc in caisses:
            label = f"{cid} - {nom}"
            values.append(label)
            self.caisses_map[label] = cid

        if not values:
            self.achat_caisse_option.configure(values=["(aucune caisse)"])
            self.achat_caisse_option.set("(aucune caisse)")
            self.caisse_selectionnee_id = None
            return

        self.achat_caisse_option.configure(values=values)
        self.achat_caisse_var.set(values[0])
        self.caisse_selectionnee_id = self.caisses_map[values[0]]

    def _on_caisse_change(self, choice: str):
        if not choice:
            self.caisse_selectionnee_id = None
        else:
            self.caisse_selectionnee_id = self.caisses_map.get(choice)

    def _charger_produits(self):
        terme = (self.achat_search_var.get() or "").strip()
        try:
            if terme:
                rows = self.db.rechercher_produits(terme, uniquement_actifs=False)
            else:
                rows = self.db.get_produits(uniquement_actifs=False)
        except Exception as e:
            messagebox.showerror("Achats", f"Erreur lecture produits : {e}", parent=self)
            return

        self.achat_produits_tree.delete(*self.achat_produits_tree.get_children())
        for p in rows:
            pid, code, ref, nom, cat, desc, pa, pv, qte, seuil, actif = p
            self.achat_produits_tree.insert(
                "",
                "end",
                values=(
                    pid,
                    nom or "",
                    code or "",
                    int(qte or 0),
                    f"{float(pa or 0):.2f}",
                    f"{float(pv or 0):.2f}",
                )
            )

    def _get_produit_selectionne(self):
        sel = self.achat_produits_tree.selection()
        if not sel:
            return None
        vals = self.achat_produits_tree.item(sel[0]).get("values") or []
        if len(vals) < 6:
            return None
        pid, nom, code, stock, pa, pv = vals
        try:
            pa_val = float(str(pa).replace(",", ".")) if pa not in (None, "") else 0.0
        except ValueError:
            pa_val = 0.0
        try:
            pv_val = float(str(pv).replace(",", ".")) if pv not in (None, "") else 0.0
        except ValueError:
            pv_val = 0.0
        return {
            "id": pid,
            "nom": nom,
            "code": code,
            "stock": stock,
            "prix_achat": pa_val,
            "prix_vente": pv_val,
        }

    def _ajouter_ligne_depuis_selection(self):
        prod = self._get_produit_selectionne()
        if not prod:
            messagebox.showwarning("Achats", "Sélectionnez un produit dans la liste.", parent=self)
            return

        self.achat_lbl_produit_sel.configure(text=f"Produit sélectionné : {prod['nom']}")

        try:
            qte = int((self.achat_qte_entry.get() or "0"))
        except ValueError:
            messagebox.showwarning("Achats", "Quantité invalide (entier).", parent=self)
            return
        if qte <= 0:
            messagebox.showwarning("Achats", "La quantité doit être >= 1.", parent=self)
            return

        pa_str = (self.achat_pa_entry.get() or "").replace(",", ".")
        if pa_str.strip() == "":
            pa = prod["prix_achat"] or 0.0
        else:
            try:
                pa = float(pa_str)
            except ValueError:
                messagebox.showwarning("Achats", "Prix d'achat invalide.", parent=self)
                return
        if pa <= 0:
            messagebox.showwarning("Achats", "Le prix d'achat doit être > 0.", parent=self)
            return

        pv_str = (self.achat_pv_entry.get() or "").replace(",", ".")
        if pv_str.strip() == "":
            pv = prod["prix_vente"] or 0.0
        else:
            try:
                pv = float(pv_str)
            except ValueError:
                messagebox.showwarning("Achats", "Prix de vente invalide.", parent=self)
                return
        if pv <= 0:
            messagebox.showwarning("Achats", "Le prix de vente doit être > 0.", parent=self)
            return

        st = pa * qte
        self.lignes.append({
            "produit_id": prod["id"],
            "nom": prod["nom"],
            "quantite": qte,
            "prix_achat": pa,
            "prix_vente": pv,
            "sous_total": st
        })

        self._rafraichir_lignes()
        self._maj_total()

    def _rafraichir_lignes(self):
        self.achat_lignes_tree.delete(*self.achat_lignes_tree.get_children())
        for i, l in enumerate(self.lignes):
            self.achat_lignes_tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    l["nom"],
                    l["quantite"],
                    f"{l['prix_achat']:.2f}",
                    f"{l['prix_vente']:.2f}",
                    f"{l['sous_total']:.2f}"
                )
            )

    def _maj_total(self):
        total = sum(l["sous_total"] for l in self.lignes)
        self.achat_total_label.configure(text=f"{total:.2f} DA")

    def _supprimer_ligne(self):
        sel = self.achat_lignes_tree.selection()
        if not sel:
            return
        iid = sel[0]
        try:
            idx = int(iid)
        except ValueError:
            return
        if 0 <= idx < len(self.lignes):
            self.lignes.pop(idx)
        self._rafraichir_lignes()
        self._maj_total()

    def _valider(self):
        if not self.lignes:
            messagebox.showwarning("Achats", "Aucune ligne dans la facture.", parent=self)
            return

        total_ht = sum(l["sous_total"] for l in self.lignes)

        # Mise à jour produits (stock + prix)
        try:
            for l in self.lignes:
                pid = l["produit_id"]
                qte = l["quantite"]
                pa = l["prix_achat"]
                pv = l["prix_vente"]
                self.db.modifier_produit(produit_id=pid, prix_achat=pa, prix_vente=pv)
                self.db.modifier_stock(produit_id=pid, delta_quantite=qte)
        except Exception as e:
            messagebox.showerror("Achats", f"Erreur lors de la mise à jour du stock : {e}", parent=self)
            return

        # Mouvement de caisse (paiement fournisseur)
        if self.caisse_selectionnee_id and total_ht > 0:
            desc = f"Achat {self.achat_num_entry.get().strip() or ''} - {self.achat_four_entry.get().strip() or 'Fournisseur'}"
            try:
                self.db.ajouter_mouvement_caisse(
                    caisse_id=self.caisse_selectionnee_id,
                    type_mvt="SORTIE",
                    montant=total_ht,
                    description=desc
                )
            except Exception as e:
                messagebox.showerror(
                    "Achats",
                    f"Stock mis à jour, mais erreur lors de l'enregistrement du paiement en caisse : {e}",
                    parent=self
                )

        messagebox.showinfo("Achats", "Facture enregistrée, stock et prix mis à jour.", parent=self)

        # Impression du bon / facture d'achat
        self._imprimer_bon_achat()

        self.result = True
        self.destroy()

    def _imprimer_bon_achat(self):
        """
        Génère un ticket texte et l'envoie à l'impression (si possible).
        """
        if not self.lignes:
            return

        try:
            total_ht = sum(l["sous_total"] for l in self.lignes)
        except Exception:
            total_ht = 0.0

        lignes_txt = []

        # En-tête magasin (facultatif)
        if getattr(self, "store_name", None):
            lignes_txt.append(str(self.store_name).center(40))
        if getattr(self, "store_tel", ""):
            lignes_txt.append(f"Tél : {self.store_tel}".center(40))
        if lignes_txt:
            lignes_txt.append("")

        lignes_txt.append("BON / FACTURE D'ACHAT".center(40))
        date_txt = (self.achat_date_entry.get() or "").strip()
        num_txt = (self.achat_num_entry.get() or "").strip()
        four_txt = (self.achat_four_entry.get() or "").strip() or "Fournisseur"

        lignes_txt.append(f"Date : {date_txt}")
        if num_txt:
            lignes_txt.append(f"N° : {num_txt}")
        lignes_txt.append(f"Fournisseur : {four_txt}")
        lignes_txt.append("-" * 40)
        lignes_txt.append(f"{'Article':20}{'Qté':>4}{'P.A':>7}{'Tot':>9}")

        for l in self.lignes:
            nom = (l.get("nom") or "")[:20]
            qte = int(l.get("quantite") or 0)
            pa = float(l.get("prix_achat") or 0)
            st = float(l.get("sous_total") or 0)
            lignes_txt.append(f"{nom:20}{qte:>4}{pa:>7.2f}{st:>9.2f}")

        lignes_txt.append("-" * 40)
        lignes_txt.append(f"TOTAL : {total_ht:.2f} DA")
        lignes_txt.append("")
        lignes_txt.append("Merci".center(40))

        contenu = "\n".join(lignes_txt)

        try:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as f:
                f.write(contenu)
                temp_path = f.name

            if os.name == "nt":
                # Windows : impression via programme associé
                os.startfile(temp_path, "print")
            else:
                # Autres OS : tentative via 'lp'
                try:
                    subprocess.run(["lp", temp_path], check=False)
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Impression", f"Erreur lors de l'impression du bon d'achat : {e}", parent=self)

    def _cancel(self):
        self.result = False
        self.destroy()


class VenteDialog(ctk.CTkToplevel):
    """
    Facture / bon de vente détaillé depuis Produits/Stock.
    - Sélection de produits du stock
    - Saisie quantités + prix de vente
    - Paiement (montant payé, monnaie, mode)
    - Caisse + éventuelle créance si paiement partiel
    """
    def __init__(self, parent, db: Database, store_name: str = "pyramide", store_tel: str = ""):
        super().__init__(parent)
        self.db = db
        self.store_name = store_name or "pyramide"
        self.store_tel = store_tel or ""
        self.lignes = []  # {produit_id, nom, quantite, prix_unitaire, sous_total}
        self.result = False

        self.caisses_map = {}
        self.caisse_selectionnee_id = None
        self.vente_caisse_var = tk.StringVar()
        self.vente_mode_var = tk.StringVar(value="Espèces")
        self.vente_montant_paye_var = tk.StringVar()

        self.title("Facture / bon de vente")
        self.geometry("1150x620")
        self.resizable(False, False)
        try:
            self.configure(fg_color="#FFEBEE")
        except Exception:
            pass

        self._build_ui()
        self._charger_caisses()
        self._charger_produits()
        self._maj_total()

        # --- affichage au-dessus + centrage + focus ---
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        try:
            if parent is not None:
                px = parent.winfo_rootx()
                py = parent.winfo_rooty()
                pw = parent.winfo_width()
                ph = parent.winfo_height()
                sw = self.winfo_width()
                sh = self.winfo_height()
                x = px + (pw - sw) // 2
                y = py + (ph - sh) // 2
                self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self.lift()
        self.focus_force()
        self.after(100, self.lift)

        self.bind("<Escape>", lambda e: self._cancel())
        # Entrée = ajouter / valider la ligne
        self.bind("<Return>", lambda e: self._ajouter_ligne_depuis_selection())
        self.wait_window(self)

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="#FFEBEE")
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(main, fg_color="#FFCDD2", corner_radius=10)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8), padx=2)
        header.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            header,
            text="Facture / bon de vente",
            text_color="#B71C1C",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, padx=10, pady=(6, 2), sticky="w")

        ctk.CTkLabel(header, text="Client :", text_color="#000000").grid(
            row=1, column=0, padx=8, pady=2, sticky="e"
        )
        self.vente_client_entry = ctk.CTkEntry(header, width=220, placeholder_text="Nom du client (optionnel)")
        self.vente_client_entry.grid(row=1, column=1, padx=4, pady=2, sticky="w")

        ctk.CTkLabel(header, text="N° facture / bon :", text_color="#000000").grid(
            row=1, column=2, padx=8, pady=2, sticky="e"
        )
        self.vente_num_entry = ctk.CTkEntry(header, width=160, placeholder_text="V-2025-001")
        self.vente_num_entry.grid(row=1, column=3, padx=4, pady=2, sticky="w")

        ctk.CTkLabel(header, text="Date :", text_color="#000000").grid(
            row=2, column=0, padx=8, pady=2, sticky="e"
        )
        self.vente_date_entry = ctk.CTkEntry(header, width=120)
        self.vente_date_entry.grid(row=2, column=1, padx=4, pady=2, sticky="w")
        self.vente_date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # Colonne gauche : produits
        left = ctk.CTkFrame(main, fg_color="#FFEBEE")
        left.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 5))
        left.grid_rowconfigure(1, weight=1)

        search_frame = ctk.CTkFrame(left, fg_color="#FFEBEE")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="Recherche produit :", text_color="#000000").grid(
            row=0, column=0, padx=5, pady=3, sticky="w"
        )
        self.vente_search_var = tk.StringVar()
        self.vente_search_entry = ctk.CTkEntry(search_frame, textvariable=self.vente_search_var, width=200)
        self.vente_search_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        self.vente_search_entry.bind("<Return>", lambda e: self._charger_produits())

        ctk.CTkButton(
            search_frame,
            text="Chercher",
            width=80,
            fg_color="#E53935",
            hover_color="#C62828",
            text_color="white",
            command=self._charger_produits
        ).grid(row=0, column=2, padx=5, pady=3)

        prod_frame = ctk.CTkFrame(left, fg_color="#FFFFFF", corner_radius=8)
        prod_frame.grid(row=1, column=0, sticky="nsew")
        cols = ("id", "nom", "code", "stock", "pv")
        self.vente_produits_tree = ttk.Treeview(prod_frame, columns=cols, show="headings", height=10)
        self.vente_produits_tree.heading("id", text="ID")
        self.vente_produits_tree.heading("nom", text="Produit")
        self.vente_produits_tree.heading("code", text="Code")
        self.vente_produits_tree.heading("stock", text="Stock")
        self.vente_produits_tree.heading("pv", text="P. vente")

        self.vente_produits_tree.column("id", width=40, anchor="center")
        self.vente_produits_tree.column("nom", width=180, anchor="w")
        self.vente_produits_tree.column("code", width=90, anchor="w")
        self.vente_produits_tree.column("stock", width=60, anchor="e")
        self.vente_produits_tree.column("pv", width=80, anchor="e")

        vsb_prod = ttk.Scrollbar(prod_frame, orient="vertical", command=self.vente_produits_tree.yview)
        self.vente_produits_tree.configure(yscrollcommand=vsb_prod.set)

        self.vente_produits_tree.pack(side="left", fill="both", expand=True)
        vsb_prod.pack(side="right", fill="y")

        self.vente_produits_tree.bind("<Double-1>", lambda e: self._ajouter_ligne_depuis_selection())

        # Milieu : saisie d'une ligne (Qté, PU)
        mid = ctk.CTkFrame(main, fg_color="#FFEBEE")
        mid.grid(row=1, column=1, sticky="nw", padx=(5, 5), pady=(0, 3))

        self.vente_lbl_produit_sel = ctk.CTkLabel(
            mid,
            text="Produit sélectionné : (aucun)",
            text_color="#B71C1C",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.vente_lbl_produit_sel.grid(row=0, column=0, columnspan=6, padx=5, pady=(0, 3), sticky="w")

        ctk.CTkLabel(mid, text="Quantité * :", text_color="#000000").grid(
            row=1, column=0, padx=5, pady=2, sticky="e"
        )
        self.vente_qte_entry = ctk.CTkEntry(mid, width=80)
        self.vente_qte_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        self.vente_qte_entry.insert(0, "1")

        ctk.CTkLabel(mid, text="Prix vente (DA) * :", text_color="#000000").grid(
            row=1, column=2, padx=5, pady=2, sticky="e"
        )
        self.vente_pv_entry = ctk.CTkEntry(mid, width=100)
        self.vente_pv_entry.grid(row=1, column=3, padx=5, pady=2, sticky="w")

        ctk.CTkButton(
            mid,
            text="Ajouter / valider la ligne",
            fg_color="#E53935",
            hover_color="#C62828",
            text_color="white",
            command=self._ajouter_ligne_depuis_selection
        ).grid(row=2, column=0, columnspan=6, padx=5, pady=(4, 4), sticky="ew")

        # Colonne droite : lignes facture + paiement
        right = ctk.CTkFrame(main, fg_color="#FFEBEE")
        right.grid(row=2, column=1, sticky="nsew", padx=(5, 0))
        right.grid_rowconfigure(0, weight=1)

        lines_frame = ctk.CTkFrame(right, fg_color="#FFFFFF", corner_radius=8)
        lines_frame.grid(row=0, column=0, sticky="nsew")
        cols2 = ("nom", "qte", "pu", "st")
        self.vente_lignes_tree = ttk.Treeview(lines_frame, columns=cols2, show="headings", height=8)
        self.vente_lignes_tree.heading("nom", text="Article")
        self.vente_lignes_tree.heading("qte", text="Qté")
        self.vente_lignes_tree.heading("pu", text="P. vente")
        self.vente_lignes_tree.heading("st", text="Sous-total")

        self.vente_lignes_tree.column("nom", width=220, anchor="w")
        self.vente_lignes_tree.column("qte", width=60, anchor="e")
        self.vente_lignes_tree.column("pu", width=80, anchor="e")
        self.vente_lignes_tree.column("st", width=100, anchor="e")

        vsb_lines = ttk.Scrollbar(lines_frame, orient="vertical", command=self.vente_lignes_tree.yview)
        self.vente_lignes_tree.configure(yscrollcommand=vsb_lines.set)

        self.vente_lignes_tree.pack(side="left", fill="both", expand=True)
        vsb_lines.pack(side="right", fill="y")

        bottom_right = ctk.CTkFrame(right, fg_color="#FFEBEE")
        bottom_right.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        bottom_right.grid_columnconfigure(1, weight=1)

        # Total
        ctk.CTkLabel(bottom_right, text="TOTAL :", text_color="#000000").grid(
            row=0, column=0, padx=5, pady=2, sticky="e"
        )
        self.vente_total_label = ctk.CTkLabel(
            bottom_right, text="0.00 DA",
            text_color="#B71C1C",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.vente_total_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        # Montant payé
        ctk.CTkLabel(bottom_right, text="Montant payé (DA) :", text_color="#000000").grid(
            row=1, column=0, padx=5, pady=2, sticky="e"
        )
        self.vente_montant_paye_entry = ctk.CTkEntry(
            bottom_right,
            width=120,
            textvariable=self.vente_montant_paye_var
        )
        self.vente_montant_paye_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        self.vente_montant_paye_entry.bind("<KeyRelease>", lambda e: self._maj_total())

        # Monnaie
        ctk.CTkLabel(bottom_right, text="Monnaie rendue :", text_color="#000000").grid(
            row=2, column=0, padx=5, pady=2, sticky="e"
        )
        self.vente_monnaie_label = ctk.CTkLabel(
            bottom_right, text="0.00 DA", text_color="#000000"
        )
        self.vente_monnaie_label.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        # Mode de paiement
        ctk.CTkLabel(bottom_right, text="Mode de paiement :", text_color="#000000").grid(
            row=3, column=0, padx=5, pady=2, sticky="e"
        )
        self.vente_mode_option = ctk.CTkOptionMenu(
            bottom_right,
            variable=self.vente_mode_var,
            values=["Espèces", "Carte", "Chèque", "Autre"],
            width=160
        )
        self.vente_mode_option.grid(row=3, column=1, padx=5, pady=2, sticky="w")

        # Caisse
        ctk.CTkLabel(bottom_right, text="Caisse :", text_color="#000000").grid(
            row=4, column=0, padx=5, pady=2, sticky="e"
        )
        self.vente_caisse_option = ctk.CTkOptionMenu(
            bottom_right,
            variable=self.vente_caisse_var,
            values=[],
            command=self._on_caisse_change,
            width=260
        )
        self.vente_caisse_option.grid(row=4, column=1, padx=5, pady=2, sticky="w")

        btns2 = ctk.CTkFrame(bottom_right, fg_color="#FFEBEE")
        btns2.grid(row=5, column=0, columnspan=2, pady=(4, 0))

        ctk.CTkButton(
            btns2,
            text="Supprimer ligne",
            fg_color="#9E9E9E",
            hover_color="#757575",
            text_color="white",
            command=self._supprimer_ligne
        ).pack(side="left", padx=4, pady=2)

        ctk.CTkButton(
            btns2,
            text="Valider facture (enregistrer vente)",
            fg_color="#E53935",
            hover_color="#C62828",
            text_color="white",
            command=self._valider
        ).pack(side="left", padx=4, pady=2)

        ctk.CTkButton(
            btns2,
            text="Annuler",
            fg_color="#b71c1c",
            hover_color="#7f0000",
            text_color="white",
            command=self._cancel
        ).pack(side="left", padx=4, pady=2)

    # --------- LOGIQUE VENTE DÉTAILLÉE ----------

    def _charger_caisses(self):
        try:
            caisses = self.db.get_caisses()
        except Exception as e:
            messagebox.showerror("Vente", f"Erreur lecture caisses : {e}", parent=self)
            return

        self.caisses_map = {}
        values = []
        for cid, nom, desc in caisses:
            label = f"{cid} - {nom}"
            values.append(label)
            self.caisses_map[label] = cid

        if not values:
            self.vente_caisse_option.configure(values=["(aucune caisse)"])
            self.vente_caisse_option.set("(aucune caisse)")
            self.caisse_selectionnee_id = None
            return

        self.vente_caisse_option.configure(values=values)
        self.vente_caisse_var.set(values[0])
        self.caisse_selectionnee_id = self.caisses_map[values[0]]

    def _on_caisse_change(self, choice: str):
        if not choice:
            self.caisse_selectionnee_id = None
        else:
            self.caisse_selectionnee_id = self.caisses_map.get(choice)

    def _charger_produits(self):
        terme = (self.vente_search_var.get() or "").strip()
        try:
            if terme:
                rows = self.db.rechercher_produits(terme, uniquement_actifs=True)
            else:
                rows = self.db.get_produits(uniquement_actifs=True)
        except Exception as e:
            messagebox.showerror("Vente", f"Erreur lecture produits : {e}", parent=self)
            return

        self.vente_produits_tree.delete(*self.vente_produits_tree.get_children())
        for p in rows:
            pid, code, ref, nom, cat, desc, pa, pv, qte, seuil, actif = p
            self.vente_produits_tree.insert(
                "",
                "end",
                values=(
                    pid,
                    nom or "",
                    code or "",
                    int(qte or 0),
                    f"{float(pv or 0):.2f}",
                )
            )

    def _get_produit_selectionne(self):
        sel = self.vente_produits_tree.selection()
        if not sel:
            return None
        vals = self.vente_produits_tree.item(sel[0]).get("values") or []
        if len(vals) < 5:
            return None
        pid, nom, code, stock, pv = vals
        try:
            pv_val = float(str(pv).replace(",", ".")) if pv not in (None, "") else 0.0
        except ValueError:
            pv_val = 0.0
        return {
            "id": pid,
            "nom": nom,
            "code": code,
            "stock": stock,
            "prix_vente": pv_val,
        }

    def _ajouter_ligne_depuis_selection(self):
        prod = self._get_produit_selectionne()
        if not prod:
            messagebox.showwarning("Vente", "Sélectionnez un produit dans la liste.", parent=self)
            return

        self.vente_lbl_produit_sel.configure(text=f"Produit sélectionné : {prod['nom']}")

        try:
            qte = int((self.vente_qte_entry.get() or "0"))
        except ValueError:
            messagebox.showwarning("Vente", "Quantité invalide (entier).", parent=self)
            return
        if qte <= 0:
            messagebox.showwarning("Vente", "La quantité doit être >= 1.", parent=self)
            return

        if prod["stock"] is not None and qte > int(prod["stock"]):
            messagebox.showwarning("Vente", "Quantité demandée supérieure au stock.", parent=self)
            return

        pv_str = (self.vente_pv_entry.get() or "").replace(",", ".")
        if pv_str.strip() == "":
            pv = prod["prix_vente"] or 0.0
        else:
            try:
                pv = float(pv_str)
            except ValueError:
                messagebox.showwarning("Vente", "Prix de vente invalide.", parent=self)
                return
        if pv <= 0:
            messagebox.showwarning("Vente", "Le prix de vente doit être > 0.", parent=self)
            return

        st = pv * qte
        self.lignes.append({
            "produit_id": prod["id"],
            "nom": prod["nom"],
            "quantite": qte,
            "prix_unitaire": pv,
            "sous_total": st
        })

        self._rafraichir_lignes()
        self._maj_total()

    def _rafraichir_lignes(self):
        self.vente_lignes_tree.delete(*self.vente_lignes_tree.get_children())
        for i, l in enumerate(self.lignes):
            self.vente_lignes_tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    l["nom"],
                    l["quantite"],
                    f"{l['prix_unitaire']:.2f}",
                    f"{l['sous_total']:.2f}"
                )
            )

    def _maj_total(self):
        total = sum(l["sous_total"] for l in self.lignes)
        self.vente_total_label.configure(text=f"{total:.2f} DA")

        try:
            mp = float((self.vente_montant_paye_var.get() or "0").replace(",", "."))
        except ValueError:
            mp = 0.0
        monnaie = mp - total if mp >= total else 0.0
        self.vente_monnaie_label.configure(text=f"{monnaie:.2f} DA")

    def _supprimer_ligne(self):
        sel = self.vente_lignes_tree.selection()
        if not sel:
            return
        iid = sel[0]
        try:
            idx = int(iid)
        except ValueError:
            return
        if 0 <= idx < len(self.lignes):
            self.lignes.pop(idx)
        self._rafraichir_lignes()
        self._maj_total()

    def _valider(self):
        if not self.lignes:
            messagebox.showwarning("Vente", "Aucune ligne dans la facture.", parent=self)
            return

        if not self.caisse_selectionnee_id:
            messagebox.showwarning("Vente", "Aucune caisse sélectionnée.", parent=self)
            return

        total = sum(l["sous_total"] for l in self.lignes)

        try:
            mp = float((self.vente_montant_paye_var.get() or "0").replace(",", "."))
        except ValueError:
            mp = 0.0

        monnaie = mp - total if mp >= total else 0.0
        reste = total - mp if mp < total else 0.0

        mode = self.vente_mode_var.get() or "Espèces"
        client_nom = (self.vente_client_entry.get() or "").strip() or None

        # Crédit client si paiement partiel
        if reste > 0.01:
            dlg = CreditClientDialog(self, self.db, reste_du=reste)
            if not dlg.result:
                messagebox.showinfo("Vente", "Vente annulée (client pour crédit non sélectionné).", parent=self)
                return
            client_nom = dlg.result

        # Préparation des items pour la DB
        items = [
            {
                "produit_id": l["produit_id"],
                "nom": l["nom"],
                "quantite": l["quantite"],
                "prix_unitaire": l["prix_unitaire"],
                "sous_total": l["sous_total"],
            }
            for l in self.lignes
        ]

        try:
            vente_id = self.db.enregistrer_vente_comptoir(
                caisse_id=self.caisse_selectionnee_id,
                items=items,
                mode_paiement=mode,
                montant_paye=mp,
                monnaie_rendue=monnaie,
                client_nom=client_nom
            )
        except Exception as e:
            messagebox.showerror("Vente", f"Erreur enregistrement vente : {e}", parent=self)
            return

        # Mouvement de caisse (entrée)
        if mp > 0:
            desc_num = (self.vente_num_entry.get() or "").strip() or f"Vente N°{vente_id}"
            desc = f"{desc_num} - {client_nom or 'Client'}"
            try:
                self.db.ajouter_mouvement_caisse(
                    caisse_id=self.caisse_selectionnee_id,
                    type_mvt="ENTREE",
                    montant=mp,
                    description=desc
                )
            except Exception as e:
                messagebox.showerror("Vente", f"Vente OK mais erreur mouvement caisse : {e}", parent=self)

        # Créance si paiement partiel
        if reste > 0.01:
            try:
                desc = (self.vente_num_entry.get() or "").strip() or f"Vente N°{vente_id}"
                self.db.ajouter_creance(
                    client_nom=client_nom or "Client inconnu",
                    pc_marque="",
                    description=desc,
                    montant_total=total,
                    montant_paye=mp,
                    montant_restant=reste,
                    date_retrait=datetime.now().strftime("%d/%m/%Y"),
                    ticket_id=None
                )
            except Exception as e:
                messagebox.showerror("Vente", f"Vente OK mais erreur enregistrement créance : {e}", parent=self)

        messagebox.showinfo("Vente", f"Vente enregistrée (N° {vente_id}).", parent=self)

        # Impression du bon de vente
        self._imprimer_bon_vente(
            total=total,
            montant_paye=mp,
            monnaie=monnaie,
            reste=reste,
            client_nom=client_nom,
            mode_paiement=mode,
            vente_id=vente_id,
        )

        self.result = True
        self.destroy()

    def _imprimer_bon_vente(self, total, montant_paye, monnaie, reste, client_nom, mode_paiement, vente_id):
        """
        Génère un ticket texte pour la facture / bon de vente et l'envoie à l'impression.
        """
        if not self.lignes:
            return

        lignes_txt = []

        # En-tête magasin
        if getattr(self, "store_name", None):
            lignes_txt.append(str(self.store_name).center(40))
        if getattr(self, "store_tel", ""):
            lignes_txt.append(f"Tél : {self.store_tel}".center(40))
        if lignes_txt:
            lignes_txt.append("")

        lignes_txt.append("FACTURE / BON DE VENTE".center(40))
        date_txt = (self.vente_date_entry.get() or "").strip()
        num_txt = (self.vente_num_entry.get() or "").strip() or f"Vente N°{vente_id}"
        client_txt = client_nom or (self.vente_client_entry.get() or "").strip() or "Client"

        lignes_txt.append(f"Date : {date_txt}")
        lignes_txt.append(f"N° : {num_txt}")
        lignes_txt.append(f"Client : {client_txt}")
        lignes_txt.append(f"Paiement : {mode_paiement}")
        lignes_txt.append("-" * 40)
        lignes_txt.append(f"{'Article':20}{'Qté':>4}{'PU':>7}{'Tot':>9}")

        for l in self.lignes:
            nom = (l.get("nom") or "")[:20]
            qte = int(l.get("quantite") or 0)
            pu = float(l.get("prix_unitaire") or 0)
            st = float(l.get("sous_total") or 0)
            lignes_txt.append(f"{nom:20}{qte:>4}{pu:>7.2f}{st:>9.2f}")

        lignes_txt.append("-" * 40)
        lignes_txt.append(f"TOTAL : {total:.2f} DA")
        lignes_txt.append(f"Payé : {montant_paye:.2f} DA")
        lignes_txt.append(f"Monnaie : {monnaie:.2f} DA")
        if reste > 0.01:
            lignes_txt.append(f"Reste : {reste:.2f} DA")
        lignes_txt.append("")
        lignes_txt.append("Merci pour votre achat".center(40))

        contenu = "\n".join(lignes_txt)

        try:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as f:
                f.write(contenu)
                temp_path = f.name

            if os.name == "nt":
                os.startfile(temp_path, "print")
            else:
                try:
                    subprocess.run(["lp", temp_path], check=False)
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Impression", f"Erreur lors de l'impression du bon de vente : {e}", parent=self)

    def _cancel(self):
        self.result = False
        self.destroy()


class AdminLoginDialog(ctk.CTkToplevel):
    """
    Fenêtre de login administrateur simple.
    Mot de passe par défaut : 'admin' (à personnaliser).
    Utilisation :
        dlg = AdminLoginDialog(parent)
        if dlg.result:  # True si OK
            ...
    """
    def __init__(self, parent, db: Database = None, password: str = None):
        super().__init__(parent)
        self.db = db
        # Mot de passe par défaut (change-le si tu veux)
        self.admin_password = password or "admin"
        self.result = False

        self.title("Connexion administrateur")
        self.geometry("400x220")
        self.resizable(False, False)
        try:
            self.configure(fg_color="#ECEFF1")
        except Exception:
            pass

        self._build_ui()

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.bind("<Return>", lambda e: self._on_ok())
        self.wait_window(self)

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="#ECEFF1", corner_radius=10)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        header = ctk.CTkFrame(main, fg_color="#37474F", corner_radius=10)
        header.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            header,
            text="Accès administrateur",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(6, 2))
        ctk.CTkLabel(
            header,
            text="Entrez le mot de passe administrateur pour continuer.",
            text_color="#CFD8DC",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=10, pady=(0, 6))

        form = ctk.CTkFrame(main, fg_color="#ECEFF1")
        form.pack(fill="x", pady=5, padx=5)

        ctk.CTkLabel(form, text="Mot de passe :", text_color="#000000").grid(
            row=0, column=0, padx=10, pady=8, sticky="e"
        )
        self.ent_pwd = ctk.CTkEntry(form, width=220, show="*")
        self.ent_pwd.grid(row=0, column=1, padx=5, pady=8, sticky="w")
        self.ent_pwd.focus_set()

        btns = ctk.CTkFrame(main, fg_color="#ECEFF1")
        btns.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            btns,
            text="Annuler",
            fg_color="#9E9E9E",
            hover_color="#757575",
            text_color="white",
            command=self._on_cancel,
            width=120,
        ).pack(side="left", padx=10, pady=4)

        ctk.CTkButton(
            btns,
            text="Valider",
            fg_color="#00796B",
            hover_color="#004D40",
            text_color="white",
            command=self._on_ok,
            width=160,
        ).pack(side="right", padx=10, pady=4)

    def _on_ok(self):
        pwd = self.ent_pwd.get() or ""
        if pwd == self.admin_password:
            self.result = True
            self.destroy()
        else:
            messagebox.showerror("Administrateur", "Mot de passe incorrect.", parent=self)
            self.ent_pwd.delete(0, "end")
            self.ent_pwd.focus_set()

    def _on_cancel(self):
        self.result = False
        self.destroy()
