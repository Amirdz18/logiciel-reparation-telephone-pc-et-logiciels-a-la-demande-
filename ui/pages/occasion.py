# ui/pages/occasion.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import customtkinter as ctk


class OccasionPage(ctk.CTkFrame):
    """
    Module : téléphones d'occasion achetés.

    - Nom du téléphone, marque, IMEI, date d'achat
    - Informations vendeur : nom, prénom, pièce (CNI / permis),
      lieu et date de délivrance, téléphone, adresse
    """

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="#FFF8E1")
        self.app = app
        self.db = app.db

        self.selected_id = None
        self.rows_by_id = {}

        self._ensure_table()
        self._configure_styles()
        self._build_ui()
        self.charger_achats()

    # ---------------------------------------------------------
    # TABLE SQL
    # ---------------------------------------------------------

    def _ensure_table(self):
        """
        Crée la table des achats d'occasion si elle n'existe pas.
        """
        try:
            cur = self.db.cursor
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS occasion_achats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tel_nom TEXT,
                    tel_marque TEXT,
                    tel_imei TEXT,
                    date_achat TEXT,
                    vendeur_nom TEXT,
                    vendeur_prenom TEXT,
                    vendeur_piece_type TEXT,
                    vendeur_piece_num TEXT,
                    vendeur_piece_lieu TEXT,
                    vendeur_piece_date TEXT,
                    vendeur_tel TEXT,
                    vendeur_adresse TEXT
                )
                """
            )
            self.db.conn.commit()
        except Exception as e:
            messagebox.showerror("Occasion", f"Erreur création table occasion_achats : {e}", parent=self)

    # ---------------------------------------------------------
    # STYLES
    # ---------------------------------------------------------

    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Occasion.Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#000000",
            rowheight=24,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Occasion.Treeview.Heading",
            background="#F9A825",
            foreground="#000000",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Occasion.Treeview",
            background=[("selected", "#FFE082")],
            foreground=[("selected", "#000000")],
        )

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Bande du haut
        top = ctk.CTkFrame(self, fg_color="#FFFDE7")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 5))
        top.grid_columnconfigure(0, weight=0)
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            top,
            text="← Accueil",
            command=self.app.show_accueil,
            fg_color="#BDBDBD",
            hover_color="#9E9E9E",
            text_color="#000000",
            width=100
        ).grid(row=0, column=0, padx=(0, 10), pady=8, sticky="w")

        # Titre bien visible à droite
        ctk.CTkLabel(
            top,
            text="Téléphones occasion achetés",
            text_color="#F57F17",
            fg_color="#FFFDE7",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=1, padx=10, pady=8, sticky="e")

        # Colonne gauche : formulaire dans une zone défilante (scrollable)
        left_container = ctk.CTkFrame(self, fg_color="#FFF8E1")
        left_container.grid(row=1, column=0, sticky="nsew", padx=(20, 5), pady=(0, 15))
        left_container.grid_rowconfigure(0, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        # Scrollable pour être sûr de voir le bouton sur tous les écrans
        left = ctk.CTkScrollableFrame(left_container, fg_color="#FFF8E1")
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=0)
        left.grid_columnconfigure(1, weight=1)

        rowi = 0
        ctk.CTkLabel(
            left,
            text="Informations téléphone",
            text_color="#F57F17",
            fg_color="#FFF8E1",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=rowi, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 10))

        rowi += 1
        ctk.CTkLabel(left, text="Nom téléphone * :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.tel_nom_entry = ctk.CTkEntry(left, width=260)
        self.tel_nom_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=3)

        rowi += 1
        ctk.CTkLabel(left, text="Marque * :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.tel_marque_entry = ctk.CTkEntry(left, width=260)
        self.tel_marque_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=3)

        rowi += 1
        ctk.CTkLabel(left, text="N° IMEI :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.tel_imei_entry = ctk.CTkEntry(left, width=260)
        self.tel_imei_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=3)

        rowi += 1
        ctk.CTkLabel(left, text="Date d'achat :", text_color="#000000").grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.date_achat_entry = ctk.CTkEntry(left, width=140)
        self.date_achat_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=3)
        self.date_achat_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # Bloc vendeur
        rowi += 1
        vendeur_frame = ctk.CTkFrame(left, fg_color="#FFF8E1")
        vendeur_frame.grid(row=rowi, column=0, columnspan=2, sticky="ew", padx=5, pady=(10, 5))
        vendeur_frame.grid_columnconfigure(1, weight=1)

        rv = 0
        ctk.CTkLabel(
            vendeur_frame,
            text="Informations vendeur",
            text_color="#BF360C",
            fg_color="#FFF8E1",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=rv, column=0, columnspan=2, sticky="w", padx=0, pady=(0, 6))

        rv += 1
        ctk.CTkLabel(vendeur_frame, text="Nom * :", text_color="#000000").grid(
            row=rv, column=0, sticky="e", padx=5, pady=2
        )
        self.v_nom_entry = ctk.CTkEntry(vendeur_frame, width=220)
        self.v_nom_entry.grid(row=rv, column=1, sticky="ew", padx=5, pady=2)

        rv += 1
        ctk.CTkLabel(vendeur_frame, text="Prénom :", text_color="#000000").grid(
            row=rv, column=0, sticky="e", padx=5, pady=2
        )
        self.v_prenom_entry = ctk.CTkEntry(vendeur_frame, width=220)
        self.v_prenom_entry.grid(row=rv, column=1, sticky="ew", padx=5, pady=2)

        rv += 1
        ctk.CTkLabel(vendeur_frame, text="Type pièce :", text_color="#000000").grid(
            row=rv, column=0, sticky="e", padx=5, pady=2
        )
        self.v_piece_type_var = tk.StringVar(value="Carte identité")
        self.v_piece_type_menu = ctk.CTkOptionMenu(
            vendeur_frame,
            variable=self.v_piece_type_var,
            values=["Carte identité", "Permis de conduire", "Autre"],
            width=180
        )
        self.v_piece_type_menu.grid(row=rv, column=1, sticky="w", padx=5, pady=2)

        rv += 1
        ctk.CTkLabel(vendeur_frame, text="N° pièce * :", text_color="#000000").grid(
            row=rv, column=0, sticky="e", padx=5, pady=2
        )
        self.v_piece_num_entry = ctk.CTkEntry(vendeur_frame, width=220)
        self.v_piece_num_entry.grid(row=rv, column=1, sticky="ew", padx=5, pady=2)

        rv += 1
        ctk.CTkLabel(vendeur_frame, text="Lieu délivrance :", text_color="#000000").grid(
            row=rv, column=0, sticky="e", padx=5, pady=2
        )
        self.v_piece_lieu_entry = ctk.CTkEntry(vendeur_frame, width=220)
        self.v_piece_lieu_entry.grid(row=rv, column=1, sticky="ew", padx=5, pady=2)

        rv += 1
        ctk.CTkLabel(vendeur_frame, text="Date délivrance :", text_color="#000000").grid(
            row=rv, column=0, sticky="e", padx=5, pady=2
        )
        self.v_piece_date_entry = ctk.CTkEntry(vendeur_frame, width=140)
        self.v_piece_date_entry.grid(row=rv, column=1, sticky="w", padx=5, pady=2)

        rv += 1
        ctk.CTkLabel(vendeur_frame, text="Téléphone vendeur :", text_color="#000000").grid(
            row=rv, column=0, sticky="e", padx=5, pady=2
        )
        self.v_tel_entry = ctk.CTkEntry(vendeur_frame, width=220)
        self.v_tel_entry.grid(row=rv, column=1, sticky="ew", padx=5, pady=2)

        rv += 1
        ctk.CTkLabel(vendeur_frame, text="Adresse vendeur :", text_color="#000000").grid(
            row=rv, column=0, sticky="e", padx=5, pady=2
        )
        self.v_adresse_entry = ctk.CTkEntry(vendeur_frame, width=220)
        self.v_adresse_entry.grid(row=rv, column=1, sticky="ew", padx=5, pady=2)

        # Boutons formulaire (toujours visibles grâce au scroll)
        rowi += 1
        btn_frame = ctk.CTkFrame(left, fg_color="#FFF8E1")
        btn_frame.grid(row=rowi, column=0, columnspan=2, sticky="ew", padx=5, pady=(15, 10))

        ctk.CTkButton(
            btn_frame,
            text="Nouveau",
            fg_color="#9E9E9E",
            hover_color="#757575",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.occasion_nouveau,
            width=110,
            height=36
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame,
            text="Valider l'achat",
            fg_color="#F57C00",
            hover_color="#E65100",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.occasion_enregistrer,
            width=150,
            height=40
        ).pack(side="left", padx=8)

        # Colonne droite : liste des achats
        right = ctk.CTkFrame(self, fg_color="#FFFFFF")
        right.grid(row=1, column=1, sticky="nsew", padx=(5, 20), pady=(0, 15))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right,
            text="Historique des achats d'occasion",
            text_color="#F57F17",
            fg_color="#FFFFFF",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        frame_tree = ctk.CTkFrame(right, fg_color="#FFFFFF")
        frame_tree.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        frame_tree.grid_rowconfigure(0, weight=1)
        frame_tree.grid_columnconfigure(0, weight=1)

        cols = ("id", "date", "tel_nom", "marque", "imei", "vendeur", "tel_v")
        self.tree = ttk.Treeview(
            frame_tree,
            columns=cols,
            show="headings",
            style="Occasion.Treeview"
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Date achat")
        self.tree.heading("tel_nom", text="Téléphone")
        self.tree.heading("marque", text="Marque")
        self.tree.heading("imei", text="IMEI")
        self.tree.heading("vendeur", text="Vendeur")
        self.tree.heading("tel_v", text="Tél vendeur")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("date", width=90, anchor="center")
        self.tree.column("tel_nom", width=130, anchor="w")
        self.tree.column("marque", width=90, anchor="w")
        self.tree.column("imei", width=110, anchor="w")
        self.tree.column("vendeur", width=140, anchor="w")
        self.tree.column("tel_v", width=100, anchor="w")

        vsb = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # ---------------------------------------------------------
    # LOGIQUE
    # ---------------------------------------------------------

    def occasion_nouveau(self):
        """Réinitialise le formulaire."""
        self.selected_id = None
        for e in [
            self.tel_nom_entry,
            self.tel_marque_entry,
            self.tel_imei_entry,
            self.v_nom_entry,
            self.v_prenom_entry,
            self.v_piece_num_entry,
            self.v_piece_lieu_entry,
            self.v_piece_date_entry,
            self.v_tel_entry,
            self.v_adresse_entry,
        ]:
            e.delete(0, "end")

        self.date_achat_entry.delete(0, "end")
        self.date_achat_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.v_piece_type_var.set("Carte identité")

    def occasion_enregistrer(self):
        """Enregistre un nouvel achat d'occasion en base."""
        tel_nom = (self.tel_nom_entry.get() or "").strip()
        tel_marque = (self.tel_marque_entry.get() or "").strip()
        tel_imei = (self.tel_imei_entry.get() or "").strip()
        date_achat = (self.date_achat_entry.get() or "").strip()

        v_nom = (self.v_nom_entry.get() or "").strip()
        v_prenom = (self.v_prenom_entry.get() or "").strip()
        piece_type = (self.v_piece_type_var.get() or "").strip()
        piece_num = (self.v_piece_num_entry.get() or "").strip()
        piece_lieu = (self.v_piece_lieu_entry.get() or "").strip()
        piece_date = (self.v_piece_date_entry.get() or "").strip()
        v_tel = (self.v_tel_entry.get() or "").strip()
        v_adresse = (self.v_adresse_entry.get() or "").strip()

        # Vérifs minimales
        if not tel_nom:
            messagebox.showwarning("Occasion", "Le nom du téléphone est obligatoire.", parent=self)
            return
        if not tel_marque:
            messagebox.showwarning("Occasion", "La marque du téléphone est obligatoire.", parent=self)
            return
        if not v_nom:
            messagebox.showwarning("Occasion", "Le nom du vendeur est obligatoire.", parent=self)
            return
        if not piece_num:
            messagebox.showwarning("Occasion", "Le numéro de pièce du vendeur est obligatoire.", parent=self)
            return
        if not date_achat:
            date_achat = datetime.now().strftime("%d/%m/%Y")

        try:
            cur = self.db.cursor
            cur.execute(
                """
                INSERT INTO occasion_achats (
                    tel_nom, tel_marque, tel_imei, date_achat,
                    vendeur_nom, vendeur_prenom,
                    vendeur_piece_type, vendeur_piece_num,
                    vendeur_piece_lieu, vendeur_piece_date,
                    vendeur_tel, vendeur_adresse
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tel_nom, tel_marque, tel_imei, date_achat,
                    v_nom, v_prenom,
                    piece_type, piece_num,
                    piece_lieu, piece_date,
                    v_tel, v_adresse
                )
            )
            self.db.conn.commit()
        except Exception as e:
            messagebox.showerror("Occasion", f"Erreur enregistrement achat : {e}", parent=self)
            return

        messagebox.showinfo("Occasion", "Achat d'occasion enregistré.", parent=self)
        self.occasion_nouveau()
        self.charger_achats()

    def charger_achats(self):
        """Charge tous les achats d'occasion."""
        self.rows_by_id = {}
        try:
            cur = self.db.cursor
            cur.execute(
                "SELECT * FROM occasion_achats ORDER BY id DESC"
            )
            rows = cur.fetchall()
        except Exception as e:
            messagebox.showerror("Occasion", f"Erreur lecture achats : {e}", parent=self)
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in rows:
            rid = r["id"]
            self.rows_by_id[rid] = r
            tel_nom = r["tel_nom"] or ""
            marque = r["tel_marque"] or ""
            imei = r["tel_imei"] or ""
            date_achat = r["date_achat"] or ""
            vendeur_nom = (r["vendeur_nom"] or "") + (
                " " + (r["vendeur_prenom"] or "") if r["vendeur_prenom"] else ""
            )
            vendeur_tel = r["vendeur_tel"] or ""

            self.tree.insert(
                "",
                "end",
                values=(rid, date_achat, tel_nom, marque, imei, vendeur_nom, vendeur_tel)
            )

    def _on_select(self, event=None):
        """Remplit le formulaire à partir de la ligne sélectionnée (lecture/modif)."""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0]).get("values") or []
        if not vals:
            return
        rid = vals[0]
        try:
            rid = int(rid)
        except Exception:
            return

        row = self.rows_by_id.get(rid)
        if not row:
            return

        self.selected_id = rid

        # Remplir les champs
        self.tel_nom_entry.delete(0, "end")
        self.tel_nom_entry.insert(0, row["tel_nom"] or "")

        self.tel_marque_entry.delete(0, "end")
        self.tel_marque_entry.insert(0, row["tel_marque"] or "")

        self.tel_imei_entry.delete(0, "end")
        self.tel_imei_entry.insert(0, row["tel_imei"] or "")

        self.date_achat_entry.delete(0, "end")
        self.date_achat_entry.insert(0, row["date_achat"] or "")

        self.v_nom_entry.delete(0, "end")
        self.v_nom_entry.insert(0, row["vendeur_nom"] or "")

        self.v_prenom_entry.delete(0, "end")
        self.v_prenom_entry.insert(0, row["vendeur_prenom"] or "")

        self.v_piece_type_var.set(row["vendeur_piece_type"] or "Carte identité")

        self.v_piece_num_entry.delete(0, "end")
        self.v_piece_num_entry.insert(0, row["vendeur_piece_num"] or "")

        self.v_piece_lieu_entry.delete(0, "end")
        self.v_piece_lieu_entry.insert(0, row["vendeur_piece_lieu"] or "")

        self.v_piece_date_entry.delete(0, "end")
        self.v_piece_date_entry.insert(0, row["vendeur_piece_date"] or "")

        self.v_tel_entry.delete(0, "end")
        self.v_tel_entry.insert(0, row["vendeur_tel"] or "")

        self.v_adresse_entry.delete(0, "end")
        self.v_adresse_entry.insert(0, row["vendeur_adresse"] or "")
