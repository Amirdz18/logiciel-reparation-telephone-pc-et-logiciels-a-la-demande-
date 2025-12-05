import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import customtkinter as ctk


class CaisseHistoriquePage(ctk.CTkFrame):
    """
    Page d'historique des caisses :

    - À gauche : liste des caisses + solde (stylé)
    - À droite : liste des mouvements de la caisse sélectionnée (stylé)
    - Boutons pour ajouter un mouvement manuel (ENTRÉE / SORTIE) en mode admin
      + supprimer un mouvement sélectionné (admin).
    """

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="#dbeafe")  # fond bleu très clair
        self.app = app          # instance de Application
        self.db = app.db        # base de données
        self.selected_caisse_id = None
        self.caisses_rows = {}
        self.mouv_rows = {}     # id_mouvement -> row

        self._configure_styles()
        self._build_ui()
        self._refresh_all()

    # ----------------------------------------------------------
    # STYLES
    # ----------------------------------------------------------

    def _configure_styles(self):
        """Configure le style ttk pour les Treeview (tableaux)."""
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Style pour la liste des caisses
        style.configure(
            "Caisses.Treeview",
            background="#E3F2FD",
            fieldbackground="#E3F2FD",
            foreground="#000000",
            rowheight=26,
            font=("Segoe UI", 11, "bold"),
            borderwidth=0,
        )
        style.configure(
            "Caisses.Treeview.Heading",
            background="#1E3A8A",
            foreground="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
        )
        style.map(
            "Caisses.Treeview",
            background=[("selected", "#90CAF9")],
            foreground=[("selected", "#000000")],
        )

        # Style pour la liste des mouvements
        style.configure(
            "Mouvements.Treeview",
            background="#FFF7ED",        # fond crème
            fieldbackground="#FFF7ED",
            foreground="#000000",
            rowheight=26,
            font=("Segoe UI", 11),
            borderwidth=0,
        )
        style.configure(
            "Mouvements.Treeview.Heading",
            background="#FB8C00",
            foreground="#4E342E",
            font=("Segoe UI", 11, "bold"),
        )
        style.map(
            "Mouvements.Treeview",
            background=[("selected", "#FFE082")],
            foreground=[("selected", "#000000")],
        )

    # ----------------------------------------------------------
    # UI
    # ----------------------------------------------------------

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # ---------- COLONNE GAUCHE : LISTE DES CAISSES ----------
        left = ctk.CTkFrame(self, fg_color="#1E3A8A", corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Bandeau titre à gauche
        ctk.CTkLabel(
            left,
            text="CAISSES",
            text_color="#FFFFFF",
            fg_color="#1E3A8A",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")

        ctk.CTkLabel(
            left,
            text="Sélectionnez une caisse pour voir son historique et saisir des mouvements.",
            text_color="#BBDEFB",
            fg_color="#1E3A8A",
            font=ctk.CTkFont(size=11),
            wraplength=260,
            justify="left"
        ).grid(row=1, column=0, padx=10, pady=(0, 8), sticky="w")

        # Cadre pour la liste
        list_frame = ctk.CTkFrame(left, fg_color="#E3F2FD", corner_radius=10)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 10))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "nom", "solde")
        self.caisses_tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                         height=8, style="Caisses.Treeview")
        self.caisses_tree.heading("id", text="ID")
        self.caisses_tree.heading("nom", text="Nom de la caisse")
        self.caisses_tree.heading("solde", text="Solde (DA)")

        self.caisses_tree.column("id", width=40, anchor="center")
        self.caisses_tree.column("nom", width=180, anchor="w")
        self.caisses_tree.column("solde", width=100, anchor="e")

        vsb_caisses = ttk.Scrollbar(list_frame, orient="vertical", command=self.caisses_tree.yview)
        self.caisses_tree.configure(yscrollcommand=vsb_caisses.set)

        self.caisses_tree.grid(row=0, column=0, sticky="nsew")
        vsb_caisses.grid(row=0, column=1, sticky="ns")

        self.caisses_tree.bind("<<TreeviewSelect>>", lambda e: self.on_caisse_select())

        # ---------- COLONNE DROITE : HISTORIQUE + BOUTONS ----------
        right = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Bandeau titre à droite
        header = ctk.CTkFrame(right, fg_color="#0D47A1", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="HISTORIQUE DES MOUVEMENTS DE CAISSE",
            text_color="#FFFFFF",
            fg_color="#0D47A1",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))

        self.solde_label = ctk.CTkLabel(
            header,
            text="Solde : 0.00 DA",
            text_color="#C8E6C9",
            fg_color="#0D47A1",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.solde_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))

        # Cadre principal des mouvements
        mov_frame = ctk.CTkFrame(right, fg_color="#FFF7ED", corner_radius=10)
        mov_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 5))
        mov_frame.grid_rowconfigure(0, weight=1)
        mov_frame.grid_columnconfigure(0, weight=1)

        # Ajout de l'ID pour pouvoir supprimer un mouvement précis
        cols_mov = ("id", "date", "type", "montant", "desc")
        self.mouv_tree = ttk.Treeview(
            mov_frame,
            columns=cols_mov,
            show="headings",
            height=12,
            style="Mouvements.Treeview"
        )
        self.mouv_tree.heading("id", text="ID")
        self.mouv_tree.heading("date", text="Date / Heure")
        self.mouv_tree.heading("type", text="Type")
        self.mouv_tree.heading("montant", text="Montant (DA)")
        self.mouv_tree.heading("desc", text="Description")

        self.mouv_tree.column("id", width=40, anchor="center")
        self.mouv_tree.column("date", width=150, anchor="center")
        self.mouv_tree.column("type", width=80, anchor="center")
        self.mouv_tree.column("montant", width=110, anchor="e")
        self.mouv_tree.column("desc", width=280, anchor="w")

        vsb_mouv = ttk.Scrollbar(mov_frame, orient="vertical", command=self.mouv_tree.yview)
        self.mouv_tree.configure(yscrollcommand=vsb_mouv.set)

        self.mouv_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 5))
        vsb_mouv.grid(row=0, column=1, sticky="ns", pady=(0, 5))

        # Boutons de mouvements manuels + suppression
        btn_frame = ctk.CTkFrame(right, fg_color="#FFFFFF", corner_radius=0)
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))

        ctk.CTkButton(
            btn_frame,
            text="Ajouter somme (ENTRÉE)",
            fg_color="#43A047",
            hover_color="#2E7D32",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.ajouter_mouvement_manuel("ENTREE"),
            width=200
        ).pack(side="left", padx=5, pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Retirer somme (SORTIE)",
            fg_color="#FB8C00",
            hover_color="#EF6C00",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.ajouter_mouvement_manuel("SORTIE"),
            width=210
        ).pack(side="left", padx=5, pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Supprimer mouvement",
            fg_color="#c62828",
            hover_color="#8e0000",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.supprimer_mouvement_selectionne,
            width=180
        ).pack(side="left", padx=5, pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Actualiser",
            fg_color="#9E9E9E",
            hover_color="#616161",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._refresh_all,
            width=120
        ).pack(side="left", padx=5, pady=4)

    # ----------------------------------------------------------
    # Chargement / rafraîchissement
    # ----------------------------------------------------------

    def _refresh_all(self):
        """Recharge la liste des caisses et l'historique de la caisse sélectionnée."""
        self.charger_caisses()
        self.charger_historique()

    def charger_caisses(self):
        """Charge la liste des caisses avec leur solde."""
        try:
            caisses = self.db.get_caisses()
        except Exception as e:
            messagebox.showerror("Caisses", f"Erreur lecture caisses : {e}", parent=self)
            return

        self.caisses_tree.delete(*self.caisses_tree.get_children())
        self.caisses_rows = {}
        self.selected_caisse_id = None

        for row in caisses:
            cid, nom, desc = row
            try:
                solde = self.db.get_solde_caisse(cid)
            except Exception:
                solde = 0.0

            self.caisses_rows[cid] = {
                "id": cid,
                "nom": nom,
                "desc": desc,
                "solde": solde,
            }
            self.caisses_tree.insert(
                "",
                "end",
                values=(cid, nom, f"{solde:.2f}")
            )

        # sélectionner automatiquement la première caisse
        children = self.caisses_tree.get_children()
        if children:
            self.caisses_tree.selection_set(children[0])
            self.on_caisse_select()
        else:
            # pas de caisse : vider l'historique
            self.solde_label.configure(text="Solde : 0.00 DA")
            self.mouv_tree.delete(*self.mouv_tree.get_children())
            self.mouv_rows = {}

    def on_caisse_select(self):
        """Quand une caisse est sélectionnée, mettre à jour l'historique et le solde."""
        sel = self.caisses_tree.selection()
        if not sel:
            self.selected_caisse_id = None
            self.solde_label.configure(text="Solde : 0.00 DA")
            self.mouv_tree.delete(*self.mouv_tree.get_children())
            self.mouv_rows = {}
            return

        vals = self.caisses_tree.item(sel[0]).get("values") or []
        if not vals:
            return
        cid = vals[0]
        try:
            cid = int(cid)
        except Exception:
            return

        self.selected_caisse_id = cid
        # synchroniser avec l'app pour la page VENTE
        self.app.caisse_selectionnee_id = cid

        try:
            solde = self.db.get_solde_caisse(cid)
        except Exception:
            solde = 0.0

        self.solde_label.configure(text=f"Solde : {solde:.2f} DA")
        self.charger_historique()

    def charger_historique(self):
        """Charge les mouvements de la caisse sélectionnée."""
        self.mouv_tree.delete(*self.mouv_tree.get_children())
        self.mouv_rows = {}
        if not self.selected_caisse_id:
            return

        try:
            rows = self.db.get_mouvements_caisse(self.selected_caisse_id)
        except Exception as e:
            messagebox.showerror("Caisses", f"Erreur lecture mouvements : {e}", parent=self)
            return

        for row in rows:
            mid = row["id"]
            date_mvt = row["date_mouvement"] or ""
            typ = row["type"] or ""
            montant = float(row["montant"] or 0)
            desc = row["description"] or ""

            self.mouv_rows[mid] = row
            self.mouv_tree.insert(
                "",
                "end",
                values=(mid, date_mvt, typ, f"{montant:.2f}", desc)
            )

    # ----------------------------------------------------------
    # Ajout de mouvements manuels (admin)
    # ----------------------------------------------------------

    def ajouter_mouvement_manuel(self, type_mvt: str):
        """
        Ajoute un mouvement de caisse (ENTREE ou SORTIE) manuellement.
        Accessible uniquement après validation admin.
        """
        if not self.selected_caisse_id:
            messagebox.showwarning("Caisses", "Sélectionnez une caisse d'abord.", parent=self)
            return

        # Admin uniquement
        if not self.app.demander_admin():
            return

        type_mvt = type_mvt.upper()
        if type_mvt not in ("ENTREE", "SORTIE"):
            messagebox.showerror("Caisses", "Type de mouvement invalide.", parent=self)
            return

        libelle = "Entrée manuelle" if type_mvt == "ENTREE" else "Sortie manuelle"

        try:
            montant = simpledialog.askfloat(
                "Mouvement de caisse",
                f"Montant à enregistrer ({libelle}) :",
                parent=self,
                minvalue=0.01
            )
        except Exception:
            montant = None

        if montant is None:
            return

        desc = simpledialog.askstring(
            "Mouvement de caisse",
            "Description (facultatif) :",
            parent=self
        )
        if not desc:
            desc = libelle

        try:
            self.db.ajouter_mouvement_caisse(
                caisse_id=self.selected_caisse_id,
                type_mvt=type_mvt,
                montant=montant,
                description=desc
            )
        except Exception as e:
            messagebox.showerror("Caisses", f"Erreur ajout mouvement : {e}", parent=self)
            return

        messagebox.showinfo("Caisses", "Mouvement enregistré.", parent=self)
        self._refresh_all()

    # ----------------------------------------------------------
    # Suppression d'un mouvement (admin)
    # ----------------------------------------------------------

    def supprimer_mouvement_selectionne(self):
        """
        Supprime définitivement le mouvement de caisse sélectionné.
        (Admin requis)
        """
        if not self.selected_caisse_id:
            messagebox.showwarning("Caisses", "Sélectionnez d'abord une caisse.", parent=self)
            return

        sel = self.mouv_tree.selection()
        if not sel:
            messagebox.showwarning("Caisses", "Sélectionnez un mouvement dans la liste.", parent=self)
            return

        vals = self.mouv_tree.item(sel[0]).get("values") or []
        if not vals:
            return

        mvt_id = vals[0]
        try:
            mvt_id = int(mvt_id)
        except Exception:
            messagebox.showerror("Caisses", "Mouvement invalide (ID manquant).", parent=self)
            return

        row = self.mouv_rows.get(mvt_id)
        montant = float(row["montant"] or 0) if row else 0.0
        typ = (row["type"] or "") if row else ""
        desc = (row["description"] or "") if row else ""

        # Admin uniquement
        if not self.app.demander_admin():
            return

        if not messagebox.askyesno(
            "Caisses",
            f"Supprimer ce mouvement de caisse ?\n\n"
            f"ID : {mvt_id}\n"
            f"Type : {typ}\n"
            f"Montant : {montant:.2f} DA\n"
            f"Description : {desc}\n\n"
            f"Cette opération est définitive.",
            parent=self
        ):
            return

        try:
            # Utilise la méthode propre du Database
            self.db.supprimer_mouvement_caisse(mvt_id)
        except Exception as e:
            messagebox.showerror("Caisses", f"Erreur lors de la suppression du mouvement : {e}", parent=self)
            return

        messagebox.showinfo("Caisses", "Mouvement supprimé.", parent=self)
        self._refresh_all()
