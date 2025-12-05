import os
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import customtkinter as ctk


class DepotPage(ctk.CTkFrame):
    """
    Page de dépôt téléphone / client.

    - Colonne gauche : formulaire de saisie (client, téléphone, diagnostic, etc.)
    - Colonne droite : liste des tickets (En cours ou Tous)
    """

    TICKET_WIDTH = 32  # largeur du ticket en caractères (pour imprimante thermique 58mm)

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="#e3f2fd")
        self.app = app
        self.db = app.db

        self.tickets_rows = {}
        self.selected_ticket_id = None

        self._configure_styles()
        self._build_ui()
        self.depot_charger_tickets()

    # ----------------------------------------------------------
    # STYLES
    # ----------------------------------------------------------

    def _configure_styles(self):
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "DepotTickets.Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#000000",
            rowheight=28,
            font=("Segoe UI", 11),
            borderwidth=0,
        )
        style.configure(
            "DepotTickets.Treeview.Heading",
            background="#1565C0",
            foreground="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
        )
        style.map(
            "DepotTickets.Treeview",
            background=[("selected", "#BBDEFB")],
            foreground=[("selected", "#000000")],
        )

    # ----------------------------------------------------------
    # UI
    # ----------------------------------------------------------

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---------- BARRE DU HAUT ----------
        top = ctk.CTkFrame(self, fg_color="white")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 5))

        ctk.CTkButton(
            top,
            text="← Accueil",
            command=self.app.show_accueil,
            fg_color="#cccccc",
            hover_color="#b0b0b0",
            text_color="#000000",
            width=100
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            top,
            text="Dépôt téléphone / client",
            text_color="#0D47A1",
            fg_color="white",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            top,
            text="Saisissez les informations du client et du téléphone, puis enregistrez le dépôt.",
            text_color="#555555",
            fg_color="white",
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=20)

        # ---------- COLONNE GAUCHE : FORMULAIRE ----------
        left = ctk.CTkFrame(self, fg_color="#E3F2FD")
        left.grid(row=1, column=0, sticky="nsew", padx=(20, 5), pady=(0, 15))
        left.grid_columnconfigure(1, weight=1)

        form_title = ctk.CTkLabel(
            left,
            text="Nouveau dépôt",
            text_color="#0D47A1",
            fg_color="#E3F2FD",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        form_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 10))

        rowi = 1

        # --- Infos client ---
        ctk.CTkLabel(left, text="Nom du client * :", text_color="#000000",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.dep_client_nom_entry = ctk.CTkEntry(left, width=280, font=ctk.CTkFont(size=14, weight="bold"))
        self.dep_client_nom_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=3)

        rowi += 1
        ctk.CTkLabel(left, text="Téléphone client :", text_color="#000000",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.dep_client_tel_entry = ctk.CTkEntry(left, width=220, font=ctk.CTkFont(size=14))
        self.dep_client_tel_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=3)

        # --- Infos téléphone ---
        rowi += 1
        ctk.CTkLabel(left, text="Marque téléphone * :", text_color="#000000",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.dep_pc_marque_entry = ctk.CTkEntry(left, width=280, font=ctk.CTkFont(size=14, weight="bold"))
        self.dep_pc_marque_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=3)

        rowi += 1
        ctk.CTkLabel(left, text="Modèle téléphone :", text_color="#000000",
                     font=ctk.CTkFont(size=13)).grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.dep_pc_modele_entry = ctk.CTkEntry(left, width=280, font=ctk.CTkFont(size=14))
        self.dep_pc_modele_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=3)

        rowi += 1
        ctk.CTkLabel(left, text="N° de série :", text_color="#000000",
                     font=ctk.CTkFont(size=13)).grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.dep_pc_serie_entry = ctk.CTkEntry(left, width=280, font=ctk.CTkFont(size=14))
        self.dep_pc_serie_entry.grid(row=rowi, column=1, sticky="ew", padx=5, pady=3)

        # --- Accessoires ---
        rowi += 1
        acc_frame = ctk.CTkFrame(left, fg_color="#E3F2FD")
        acc_frame.grid(row=rowi, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 3))

        self.dep_chargeur_var = tk.BooleanVar(value=True)
        self.dep_batterie_var = tk.BooleanVar(value=True)

        ctk.CTkCheckBox(
            acc_frame,
            text="Avec chargeur",
            variable=self.dep_chargeur_var,
            onvalue=True,
            offvalue=False,
            fg_color="#1E88E5",
            text_color="#000000",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=5)

        ctk.CTkCheckBox(
            acc_frame,
            text="Avec batterie",
            variable=self.dep_batterie_var,
            onvalue=True,
            offvalue=False,
            fg_color="#1E88E5",
            text_color="#000000",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=5)

        # --- Date dépôt ---
        rowi += 1
        ctk.CTkLabel(left, text="Date dépôt :", text_color="#000000",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=rowi, column=0, sticky="e", padx=5, pady=3
        )
        self.dep_date_entry = ctk.CTkEntry(left, width=160, font=ctk.CTkFont(size=14))
        self.dep_date_entry.grid(row=rowi, column=1, sticky="w", padx=5, pady=3)
        self.dep_date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # --- Diagnostic initial ---
        rowi += 1
        ctk.CTkLabel(left, text="Diagnostic initial :", text_color="#000000",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=rowi, column=0, sticky="ne", padx=5, pady=3
        )
        self.dep_diag_text = tk.Text(left, height=4, width=40, font=("Consolas", 12, "bold"))
        self.dep_diag_text.grid(row=rowi, column=1, sticky="ew", padx=5, pady=3)

        # --- Boutons en bas du formulaire ---
        rowi += 1
        btn_frame = ctk.CTkFrame(left, fg_color="#E3F2FD")
        btn_frame.grid(row=rowi, column=0, columnspan=2, sticky="ew", padx=5, pady=(10, 5))

        ctk.CTkButton(
            btn_frame,
            text="Nouveau",
            fg_color="#9E9E9E",
            hover_color="#616161",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.depot_nouveau,
            width=100
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame,
            text="Enregistrer le dépôt",
            fg_color="#0D47A1",
            hover_color="#002171",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.depot_enregistrer,
            width=200
        ).pack(side="left", padx=4)

        # ---------- COLONNE DROITE : LISTE DES TICKETS ----------
        right = ctk.CTkFrame(self, fg_color="#FFFFFF")
        right.grid(row=1, column=1, sticky="nsew", padx=(5, 20), pady=(0, 15))
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(right, fg_color="#1565C0")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Tickets de dépôt",
            text_color="#FFFFFF",
            fg_color="#1565C0",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))

        ctk.CTkLabel(
            header,
            text="Visualisez les téléphones déposés (En cours ou Tous).",
            text_color="#BBDEFB",
            fg_color="#1565C0",
            font=ctk.CTkFont(size=11),
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))

        # Filtre + prévisualisation
        filter_frame = ctk.CTkFrame(right, fg_color="#FFFFFF")
        filter_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 2))
        filter_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(filter_frame, text="Afficher :", text_color="#000000",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(5, 2), pady=2)

        self.depot_filtre_var = tk.StringVar(value="En cours")
        self.depot_filtre_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.depot_filtre_var,
            values=["En cours", "Tous"],
            width=120
        )
        self.depot_filtre_menu.pack(side="left", padx=2, pady=2)

        ctk.CTkButton(
            filter_frame,
            text="Actualiser",
            fg_color="#1565C0",
            hover_color="#0D47A1",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.depot_charger_tickets,
            width=100
        ).pack(side="left", padx=5, pady=2)

        ctk.CTkButton(
            filter_frame,
            text="Prévisualiser / Imprimer",
            fg_color="#00796b",
            hover_color="#004d40",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.depot_previsualiser_ticket,
            width=170
        ).pack(side="left", padx=5, pady=2)

        # Tableau
        tickets_frame = ctk.CTkFrame(right, fg_color="#FFFFFF")
        tickets_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        tickets_frame.grid_rowconfigure(0, weight=1)
        tickets_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "client", "tel", "pc", "date", "statut")
        self.depot_tickets_tree = ttk.Treeview(
            tickets_frame,
            columns=cols,
            show="headings",
            height=12,
            style="DepotTickets.Treeview"
        )
        self.depot_tickets_tree.heading("id", text="ID")
        self.depot_tickets_tree.heading("client", text="Client")
        self.depot_tickets_tree.heading("tel", text="Téléphone client")
        self.depot_tickets_tree.heading("pc", text="Téléphone (marque / modèle)")
        self.depot_tickets_tree.heading("date", text="Date dépôt")
        self.depot_tickets_tree.heading("statut", text="Statut")

        self.depot_tickets_tree.column("id", width=40, anchor="center")
        self.depot_tickets_tree.column("client", width=140, anchor="w")
        self.depot_tickets_tree.column("tel", width=110, anchor="w")
        self.depot_tickets_tree.column("pc", width=180, anchor="w")
        self.depot_tickets_tree.column("date", width=100, anchor="center")
        self.depot_tickets_tree.column("statut", width=80, anchor="center")

        vsb2 = ttk.Scrollbar(tickets_frame, orient="vertical", command=self.depot_tickets_tree.yview)
        self.depot_tickets_tree.configure(yscrollcommand=vsb2.set)

        self.depot_tickets_tree.grid(row=0, column=0, sticky="nsew")
        vsb2.grid(row=0, column=1, sticky="ns")

        self.depot_tickets_tree.bind("<<TreeviewSelect>>", lambda e: self.depot_on_select())

    # ----------------------------------------------------------
    # LOGIQUE FORMULAIRE
    # ----------------------------------------------------------

    def depot_nouveau(self):
        """Réinitialise le formulaire de dépôt."""
        self.selected_ticket_id = None
        for e in [
            self.dep_client_nom_entry,
            self.dep_client_tel_entry,
            self.dep_pc_marque_entry,
            self.dep_pc_modele_entry,
            self.dep_pc_serie_entry,
        ]:
            e.delete(0, "end")

        self.dep_chargeur_var.set(True)
        self.dep_batterie_var.set(True)

        self.dep_date_entry.delete(0, "end")
        self.dep_date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

        self.dep_diag_text.delete("1.0", "end")

    def depot_enregistrer(self):
        """Enregistre un nouveau ticket de dépôt dans la base."""
        client_nom = (self.dep_client_nom_entry.get() or "").strip()
        client_tel = (self.dep_client_tel_entry.get() or "").strip()
        pc_marque = (self.dep_pc_marque_entry.get() or "").strip()
        pc_modele = (self.dep_pc_modele_entry.get() or "").strip()
        pc_serie = (self.dep_pc_serie_entry.get() or "").strip()
        diag = (self.dep_diag_text.get("1.0", "end") or "").strip()
        date_depot = (self.dep_date_entry.get() or "").strip()

        if not client_nom:
            messagebox.showwarning("Dépôt", "Le nom du client est obligatoire.", parent=self)
            return
        if not pc_marque:
            messagebox.showwarning("Dépôt", "La marque du téléphone est obligatoire.", parent=self)
            return
        if not date_depot:
            date_depot = datetime.now().strftime("%d/%m/%Y")

        try:
            self.db.ajouter_ticket_depot(
                client_nom=client_nom,
                pc_marque=pc_marque,
                date_depot=date_depot,
                diagnostic_initial=diag,
                avec_chargeur=self.dep_chargeur_var.get(),
                avec_batterie=self.dep_batterie_var.get(),
                client_tel=client_tel,
                pc_modele=pc_modele,
                pc_num_serie=pc_serie
            )
        except Exception as e:
            messagebox.showerror("Dépôt", f"Erreur enregistrement dépôt : {e}", parent=self)
            return

        messagebox.showinfo("Dépôt", "Dépôt enregistré.", parent=self)
        self.depot_nouveau()
        self.depot_charger_tickets()

    # ----------------------------------------------------------
    # LISTE DES TICKETS
    # ----------------------------------------------------------

    def depot_charger_tickets(self):
        """Charge la liste des tickets selon le filtre (En cours / Tous)."""
        filtre = self.depot_filtre_var.get() if hasattr(self, "depot_filtre_var") else "En cours"

        try:
            if filtre == "En cours":
                rows = self.db.get_tickets(statut="En cours")
            else:
                rows = self.db.get_tickets(statut=None)
        except Exception as e:
            messagebox.showerror("Dépôt", f"Erreur lecture tickets : {e}", parent=self)
            return

        self.depot_tickets_tree.delete(*self.depot_tickets_tree.get_children())
        self.tickets_rows = {}

        for row in rows:
            tid = row["id"]
            client = row["client_nom"] or ""
            tel = row["client_tel"] or ""
            pc = (row["pc_marque"] or "") + ((" " + (row["pc_modele"] or "")) if row["pc_modele"] else "")
            date_depot = row["date_depot"] or ""
            statut = row["statut"] or ""
            self.tickets_rows[tid] = row
            self.depot_tickets_tree.insert(
                "",
                "end",
                values=(tid, client, tel, pc, date_depot, statut)
            )

    def depot_on_select(self):
        """
        Quand on clique sur un ticket dans la liste,
        on remplit le formulaire avec ses infos (lecture pratique).
        """
        sel = self.depot_tickets_tree.selection()
        if not sel:
            return
        vals = self.depot_tickets_tree.item(sel[0]).get("values") or []
        if not vals:
            return
        tid = vals[0]
        try:
            tid = int(tid)
        except Exception:
            return

        row = self.tickets_rows.get(tid)
        if not row:
            return

        self.selected_ticket_id = tid

        self.dep_client_nom_entry.delete(0, "end")
        self.dep_client_nom_entry.insert(0, row["client_nom"] or "")

        self.dep_client_tel_entry.delete(0, "end")
        self.dep_client_tel_entry.insert(0, row["client_tel"] or "")

        self.dep_pc_marque_entry.delete(0, "end")
        self.dep_pc_marque_entry.insert(0, row["pc_marque"] or "")

        self.dep_pc_modele_entry.delete(0, "end")
        self.dep_pc_modele_entry.insert(0, row["pc_modele"] or "")

        self.dep_pc_serie_entry.delete(0, "end")
        self.dep_pc_serie_entry.insert(0, row["pc_num_serie"] or "")

        self.dep_chargeur_var.set(bool(row["avec_chargeur"]))
        self.dep_batterie_var.set(bool(row["avec_batterie"]))

        self.dep_date_entry.delete(0, "end")
        self.dep_date_entry.insert(0, row["date_depot"] or "")

        self.dep_diag_text.delete("1.0", "end")
        self.dep_diag_text.insert("1.0", row["diagnostic_initial"] or "")

    # ----------------------------------------------------------
    # FORMATAGE DU TICKET POUR IMPRIMANTE THERMIQUE
    # ----------------------------------------------------------

    def _wrap_text(self, text: str, width: int):
        """Coupe le texte en lignes de longueur <= width (en respectant les espaces)."""
        lines = []
        for paragraph in (text or "").splitlines():
            paragraph = paragraph.strip()
            while len(paragraph) > width:
                cut = paragraph.rfind(" ", 0, width + 1)
                if cut == -1:
                    cut = width
                lines.append(paragraph[:cut])
                paragraph = paragraph[cut:].lstrip()
            if paragraph:
                lines.append(paragraph)
        return lines

    def _center(self, text: str, width: int):
        """Centre le texte sur width caractères."""
        return text.center(width)

    def _line(self, ch: str = "-"):
        """Retourne une ligne de séparation de largeur TICKET_WIDTH."""
        return ch * self.TICKET_WIDTH

    def _build_ticket_text(self, tid: int, row):
        """Construit le texte du ticket au format ticket de caisse (largeur fixe)."""
        W = self.TICKET_WIDTH

        store_name = (getattr(self.app, "store_name", "MAGASIN") or "").upper()
        store_tel = getattr(self.app, "store_tel", "")

        lignes = []
        # En-tête magasin
        lignes.append(self._center(store_name[:W], W))
        if store_tel:
            lignes.append(self._center(f"Tél: {store_tel}"[:W], W))
        lignes.append(self._line())

        # Info ticket
        lignes.append(self._center("TICKET DEPOT", W))
        lignes.append(self._center(f"N° {tid}", W))
        date_dep = row["date_depot"] or ""
        lignes.append(self._center(f"Date: {date_dep}"[:W], W))
        lignes.append(self._line())

        # Client
        client = row["client_nom"] or ""
        for l in self._wrap_text(f"Client: {client}", W):
            lignes.append(l)
        if row["client_tel"]:
            for l in self._wrap_text(f"Tel: {row['client_tel']}", W):
                lignes.append(l)

        lignes.append(self._line())

        # Téléphone + accessoires
        pc_txt = (row["pc_marque"] or "") + ((" " + (row["pc_modele"] or "")) if row["pc_modele"] else "")
        for l in self._wrap_text(f"Téléphone: {pc_txt}", W):
            lignes.append(l)
        if row["pc_num_serie"]:
            for l in self._wrap_text(f"S/N: {row['pc_num_serie']}", W):
                lignes.append(l)

        acc = []
        if row["avec_chargeur"]:
            acc.append("Chargeur")
        if row["avec_batterie"]:
            acc.append("Batterie")
        if acc:
            for l in self._wrap_text("Acc: " + ", ".join(acc), W):
                lignes.append(l)

        lignes.append(self._line())

        # Diagnostic
        diag = row["diagnostic_initial"] or ""
        if diag.strip():
            lignes.append("Diag:")
            for l in self._wrap_text(diag, W):
                lignes.append(l)
            lignes.append(self._line())

        # Signature
        lignes.append("")
        lignes.append(self._center("Signature client", W))
        lignes.append("")
        lignes.append("")
        lignes.append(self._line())
        lignes.append(self._center("Merci de conserver ce ticket", W))

        # Quelques lignes vides pour bien sortir le ticket
        lignes.append("")
        lignes.append("")
        lignes.append("")

        return "\n".join(lignes)

    # ----------------------------------------------------------
    # PRÉVISUALISATION / IMPRESSION DU TICKET
    # ----------------------------------------------------------

    def depot_previsualiser_ticket(self):
        """Ouvre une fenêtre avec l'aperçu du ticket façon ticket de caisse."""
        sel = self.depot_tickets_tree.selection()
        if not sel:
            messagebox.showwarning("Dépôt", "Sélectionnez un ticket dans la liste.", parent=self)
            return
        vals = self.depot_tickets_tree.item(sel[0]).get("values") or []
        if not vals:
            return
        tid = vals[0]
        try:
            tid = int(tid)
        except Exception:
            return

        row = self.tickets_rows.get(tid)
        if not row:
            messagebox.showerror("Dépôt", "Impossible de retrouver les données du ticket.", parent=self)
            return

        contenu = self._build_ticket_text(tid, row)

        # Fenêtre de prévisualisation
        win = ctk.CTkToplevel(self)
        win.title(f"Ticket de dépôt N°{tid}")
        win.geometry("400x540")
        win.grab_set()  # fenêtre modale

        ctk.CTkLabel(
            win,
            text=f"Aperçu ticket N°{tid}",
            text_color="#0D47A1",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=10, pady=(10, 5), anchor="w")

        txt = ctk.CTkTextbox(
            win,
            width=360,
            height=420,
            font=ctk.CTkFont(family="Consolas", size=12)  # police monospace
        )
        txt.pack(padx=10, pady=5, fill="both", expand=True)
        txt.insert("1.0", contenu)
        txt.configure(state="disabled")

        btn_frame = ctk.CTkFrame(win, fg_color="white")
        btn_frame.pack(padx=10, pady=(5, 10), fill="x")

        ctk.CTkButton(
            btn_frame,
            text="Imprimer (imprimante thermique)",
            fg_color="#00796b",
            hover_color="#004d40",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.depot_imprimer_ticket(contenu)
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Fermer",
            fg_color="#9E9E9E",
            hover_color="#616161",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=win.destroy
        ).pack(side="right", padx=5)

    def depot_imprimer_ticket(self, contenu: str):
        """
        Envoie le ticket à l'imprimante.
        - Sous Windows : utilise os.startfile(..., 'print') -> va à l'imprimante par défaut
        - Pour une imprimante thermique : la choisir comme imprimante par défaut dans Windows.
        """
        try:
            # créer un fichier temporaire
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
            tmp.write(contenu)
            tmp_path = tmp.name
            tmp.close()

            if os.name == "nt":
                # Windows : imprime avec l'imprimante par défaut (mettre l'imprimante thermique par défaut)
                os.startfile(tmp_path, "print")
                messagebox.showinfo(
                    "Impression",
                    "Ticket envoyé à l'imprimante par défaut.\n"
                    "Assure-toi que l'imprimante thermique est l'imprimante par défaut.",
                    parent=self
                )
            else:
                # Autres systèmes
                messagebox.showinfo(
                    "Impression",
                    f"Fichier de ticket sauvegardé :\n{tmp_path}\n"
                    "Ouvrez-le et imprimez-le avec votre imprimante thermique.",
                    parent=self
                )
        except Exception as e:
            messagebox.showerror("Impression", f"Erreur lors de l'impression : {e}", parent=self)
