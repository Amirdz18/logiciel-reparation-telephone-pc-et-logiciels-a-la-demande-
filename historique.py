# ui/pages/historique.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import customtkinter as ctk


class HistoriquePage(ctk.CTkFrame):
    """
    Page Historique des clients :
      - Téléphones déposés / remis (réparations, tous statuts sauf 'Supprimé')
      - Téléphones d'occasion achetés (table occasion_achats)
      - Ventes au comptoir (table ventes / details_ventes)

    Onglets :
      - "Réparations" : tous les tickets de réparation (En cours, Livré, Annulé, etc., sauf 'Supprimé')
      - "Occasions"   : tous les achats d'occasion
      - "Ventes"      : toutes les ventes au comptoir
    """
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="#f3f5ff")
        self.app = app
        self.db = app.db

        self.current_ticket_id = None     # id de l'élément sélectionné (ticket, achat ou vente)
        self.all_items = []               # éléments affichés (réparations, occasions ou ventes)

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Hist.Treeview",
            background="#ffffff",
            foreground="#1a237e",
            fieldbackground="#ffffff",
            rowheight=26,
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.configure(
            "Hist.Treeview.Heading",
            background="#6a1b9a",
            foreground="#ffffff",
            font=("Segoe UI", 11, "bold")
        )
        style.map(
            "Hist.Treeview",
            background=[("selected", "#e1bee7")],
            foreground=[("selected", "#000000")]
        )

    def _build_ui(self):
        # Bande de titre
        top = ctk.CTkFrame(self, fg_color="#4a148c")
        top.pack(fill="x", padx=0, pady=(0, 5))

        ctk.CTkButton(
            top, text="← Accueil", command=self.app.show_accueil,
            fg_color="#7b1fa2", hover_color="#4a148c",
            text_color="white", width=110
        ).pack(side="left", padx=15, pady=10)

        ctk.CTkLabel(
            top, text="Historique des clients (réparations / occasions / ventes)",
            fg_color="#4a148c", text_color="white",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left", padx=20, pady=10)

        # Contenu principal
        main = ctk.CTkFrame(self, fg_color="#f3f5ff")
        main.pack(fill="both", expand=True, padx=20, pady=10)
        main.grid_columnconfigure(0, weight=2)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # Titre liste
        ctk.CTkLabel(
            main,
            text="Liste des téléphones (réparations / occasions / ventes au comptoir)",
            text_color="#4a148c",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(0, 2))

        # Table des éléments (à gauche)
        left = ctk.CTkFrame(main, fg_color="#ffffff", corner_radius=12)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=4)

        # --- Barre de recherche + type ---
        search_frame = ctk.CTkFrame(left, fg_color="#ffffff")
        search_frame.pack(fill="x", padx=4, pady=(4, 0))

        ctk.CTkLabel(
            search_frame,
            text="Recherche client :",
            text_color="#4a148c",
        ).pack(side="left", padx=(0, 4))

        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            width=160
        )
        self.search_entry.pack(side="left", padx=(0, 4))

        # Mise à jour automatique à chaque frappe
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        ctk.CTkButton(
            search_frame,
            text="Afficher tout",
            fg_color="#9e9e9e",
            hover_color="#757575",
            text_color="white",
            width=110,
            command=self._reset_search
        ).pack(side="left", padx=(4, 4))

        # Sélecteur de type : Réparations / Occasions / Ventes
        ctk.CTkLabel(
            search_frame,
            text="Type :",
            text_color="#4a148c",
        ).pack(side="left", padx=(10, 4))

        self.histo_type_var = tk.StringVar(value="Réparations")
        self.histo_type_menu = ctk.CTkOptionMenu(
            search_frame,
            variable=self.histo_type_var,
            values=["Réparations", "Occasions", "Ventes"],
            width=130,
            command=self._on_type_change
        )
        self.histo_type_menu.pack(side="left", padx=(0, 4))

        # --- fin barre de recherche ---

        cols = ("id", "date_dep", "date_ret", "client", "tel", "pc", "montant")
        self.tree = ttk.Treeview(
            left,
            columns=cols,
            show="headings",
            style="Hist.Treeview"
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("date_dep", text="Date dépôt / achat / vente")
        self.tree.heading("date_ret", text="Date retrait")
        self.tree.heading("client", text="Client / Vendeur")
        self.tree.heading("tel", text="Téléphone")
        self.tree.heading("pc", text="Appareil / Résumé")
        self.tree.heading("montant", text="Montant")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("date_dep", width=150, anchor="center")
        self.tree.column("date_ret", width=110, anchor="center")
        self.tree.column("client", width=160, anchor="w")
        self.tree.column("tel", width=120, anchor="w")
        self.tree.column("pc", width=220, anchor="w")
        self.tree.column("montant", width=100, anchor="e")

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        vsb.pack(side="right", fill="y", padx=(0, 4), pady=4)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Détails à droite
        right = ctk.CTkFrame(main, fg_color="#f9fafc", corner_radius=12)
        right.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=4)

        ctk.CTkLabel(
            right,
            text="Détails de l'élément sélectionné",
            text_color="#4a148c",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=8, pady=(8, 4), sticky="w")

        self._make_detail_row(right, "Client / Vendeur :", 1)
        self._make_detail_row(right, "Téléphone client / vendeur :", 2)
        self._make_detail_row(right, "Téléphone (appareil) :", 3)
        self._make_detail_row(right, "Date dépôt / achat / vente :", 4)
        self._make_detail_row(right, "Date retrait :", 5)
        self._make_detail_row(right, "Montant total :", 6)
        self._make_detail_row(right, "Montant payé :", 7)
        self._make_detail_row(right, "Reste à payer :", 8)

        # Récupération des labels
        self.lbl_client = right.grid_slaves(row=1, column=1)[0]
        self.lbl_tel = right.grid_slaves(row=2, column=1)[0]
        self.lbl_pc = right.grid_slaves(row=3, column=1)[0]
        self.lbl_date_dep = right.grid_slaves(row=4, column=1)[0]
        self.lbl_date_ret = right.grid_slaves(row=5, column=1)[0]
        self.lbl_mt_total = right.grid_slaves(row=6, column=1)[0]
        self.lbl_mt_paye = right.grid_slaves(row=7, column=1)[0]
        self.lbl_mt_reste = right.grid_slaves(row=8, column=1)[0]

        ctk.CTkLabel(
            right,
            text="Travaux effectués / Détails / Remarques :",
            text_color="#000000",
        ).grid(row=9, column=0, padx=8, pady=(6, 2), sticky="nw")

        self.travaux_text = ctk.CTkTextbox(right, width=260, height=90)
        self.travaux_text.grid(row=9, column=1, padx=8, pady=(6, 2), sticky="w")

        btns = ctk.CTkFrame(right, fg_color="#f9fafc")
        btns.grid(row=10, column=0, columnspan=2, pady=(6, 8))

        ctk.CTkButton(
            btns,
            text="Aperçu facture / fiche",
            fg_color="#6a1b9a", hover_color="#4a148c",
            text_color="white",
            command=self._previsualiser_facture
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btns,
            text="Vider détails",
            fg_color="#9e9e9e", hover_color="#757575",
            text_color="white",
            command=self._reset_detail
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btns,
            text="Supprimer de l'historique (admin)",
            fg_color="#c62828", hover_color="#8e0000",
            text_color="white",
            command=self._supprimer_selection
        ).pack(side="left", padx=4)

    def _make_detail_row(self, parent, label_text, row):
        ctk.CTkLabel(
            parent,
            text=label_text,
            text_color="#000000"
        ).grid(row=row, column=0, padx=8, pady=2, sticky="e")
        lab = ctk.CTkLabel(
            parent,
            text="",
            text_color="#000000",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        lab.grid(row=row, column=1, padx=8, pady=2, sticky="w")

    # ---------------------------------------------------------
    # LOGIQUE CHARGEMENT
    # ---------------------------------------------------------
    def charger_historique(self):
        """
        Charge tous les tickets de réparation (quel que soit le statut),
        sauf ceux marqués 'Supprimé'.
        Ainsi, tous les dépôts / réceptions sont visibles.
        """
        self._reset_detail()
        self.histo_type_var.set("Réparations")

        try:
            cur = self.db.cursor
            cur.execute(
                "SELECT * FROM tickets_reparation "
                "ORDER BY date_depot DESC, id DESC"
            )
            rows = cur.fetchall()
        except Exception as e:
            messagebox.showerror("Historique", f"Erreur lecture tickets : {e}")
            return

        tickets = [dict(r) for r in rows]
        filtres = [
            t for t in tickets
            if (t.get("statut") or "").lower() != "supprimé"
        ]

        self.all_items = filtres

        if hasattr(self, "search_var"):
            self.search_var.set("")

        self._remplir_tree(self.all_items)

    def charger_historique_occasions(self):
        """Charge tous les achats d'occasion comme éléments d'historique."""
        self._reset_detail()
        self.histo_type_var.set("Occasions")

        try:
            cur = self.db.cursor
            cur.execute(
                "SELECT * FROM occasion_achats ORDER BY date_achat DESC, id DESC"
            )
            rows = cur.fetchall()
        except Exception as e:
            messagebox.showerror("Historique", f"Erreur lecture achats d'occasion : {e}")
            return

        tickets = []
        for r in rows:
            tid = r["id"]
            client_nom = (r["vendeur_nom"] or "") + (
                " " + (r["vendeur_prenom"] or "") if r["vendeur_prenom"] else ""
            )
            client_tel = r["vendeur_tel"] or ""
            pc_marque = r["tel_marque"] or ""
            pc_modele = f"{r['tel_nom'] or ''} IMEI:{r['tel_imei'] or ''}".strip()
            date_dep = r["date_achat"] or ""
            date_ret = ""
            mt = 0.0

            tickets.append({
                "id": tid,
                "client_nom": client_nom,
                "client_tel": client_tel,
                "pc_marque": pc_marque,
                "pc_modele": pc_modele,
                "date_depot": date_dep,
                "date_retrait": date_ret,
                "montant_total": mt,
                "montant_paye": 0.0,
                "montant_restant": 0.0,
            })

        self.all_items = tickets

        if hasattr(self, "search_var"):
            self.search_var.set("")

        self._remplir_tree(self.all_items)

    def charger_historique_ventes(self):
        """Charge toutes les ventes au comptoir comme éléments d'historique."""
        self._reset_detail()
        self.histo_type_var.set("Ventes")

        try:
            ventes = self.db.get_ventes()
        except Exception as e:
            messagebox.showerror("Historique", f"Erreur lecture ventes : {e}")
            return

        tickets = []
        for v in ventes:
            vid = v["id"]
            client_nom = v["client_nom"] or "Vente comptoir"
            date_heure = v["date_heure"] or ""
            mt_total = float(v["montant_total"] or 0)
            mp = float(v["montant_paye"] or 0)
            mr = 0.0

            # On peut aussi compter le nombre d'articles pour un résumé
            try:
                details = self.db.get_details_vente(vid)
                nb_articles = sum(float(d["quantite"] or 0) for d in details)
            except Exception:
                nb_articles = 0

            pc_marque = "Vente comptoir"
            pc_modele = f"{nb_articles:.0f} article(s)" if nb_articles > 0 else ""

            # Transformer "YYYY-MM-DD HH:MM:SS" en "dd/mm/YYYY HH:MM"
            date_aff = date_heure
            try:
                dt = datetime.strptime(date_heure, "%Y-%m-%d %H:%M:%S")
                date_aff = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

            tickets.append({
                "id": vid,
                "client_nom": client_nom,
                "client_tel": "",
                "pc_marque": pc_marque,
                "pc_modele": pc_modele,
                "date_depot": date_aff,
                "date_retrait": "",
                "montant_total": mt_total,
                "montant_paye": mp,
                "montant_restant": mr,
            })

        self.all_items = tickets

        if hasattr(self, "search_var"):
            self.search_var.set("")

        self._remplir_tree(self.all_items)

    def _remplir_tree(self, tickets):
        """Remplit le Treeview avec la liste d'éléments donnée."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for t in tickets:
            tid = t["id"]
            client_nom = t.get("client_nom", "")
            client_tel = t.get("client_tel", "")
            pc = f"{t.get('pc_marque') or ''} {t.get('pc_modele') or ''}".strip()
            date_dep = t.get("date_depot", "")
            date_ret = t.get("date_retrait", "")
            mt = t.get("montant_total", 0)

            self.tree.insert(
                "",
                "end",
                values=(
                    tid,
                    date_dep or "",
                    date_ret or "",
                    client_nom or "",
                    client_tel or "",
                    pc,
                    f"{float(mt or 0):.2f}",
                )
            )

    def _on_type_change(self, choice):
        """Quand on change le type (Réparations / Occasions / Ventes)."""
        if choice == "Occasions":
            self.charger_historique_occasions()
        elif choice == "Ventes":
            self.charger_historique_ventes()
        else:
            self.charger_historique()

    def _on_search_change(self, event=None):
        """Filtre la liste en fonction du début du nom du client / vendeur."""
        terme = (self.search_var.get() or "").strip().lower()

        if not terme:
            filtres = self.all_items
        else:
            filtres = [
                t for t in self.all_items
                if (t.get("client_nom") or "").lower().startswith(terme)
            ]

        self._remplir_tree(filtres)
        self._reset_detail()

    def _reset_search(self):
        """Réinitialise la recherche et affiche toute la liste courante."""
        if hasattr(self, "search_var"):
            self.search_var.set("")
        self._remplir_tree(self.all_items)
        self._reset_detail()

    def _reset_detail(self):
        self.current_ticket_id = None
        if hasattr(self, "lbl_client"):
            self.lbl_client.configure(text="")
            self.lbl_tel.configure(text="")
            self.lbl_pc.configure(text="")
            self.lbl_date_dep.configure(text="")
            self.lbl_date_ret.configure(text="")
            self.lbl_mt_total.configure(text="")
            self.lbl_mt_paye.configure(text="")
            self.lbl_mt_reste.configure(text="")
            self.travaux_text.delete("1.0", "end")

    # ---------------------------------------------------------
    # SÉLECTION D'UN ÉLÉMENT
    # ---------------------------------------------------------
    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0]).get("values") or []
        if not vals:
            return
        tid = vals[0]

        type_actuel = self.histo_type_var.get()

        # Mode Réparations
        if type_actuel == "Réparations":
            try:
                t = self.db.get_ticket_by_id(tid)
            except Exception as e:
                messagebox.showerror("Historique", f"Erreur lecture ticket : {e}")
                return
            if not t:
                messagebox.showerror("Historique", "Ticket introuvable en base.")
                return

            self.current_ticket_id = tid

            client_nom = t["client_nom"] or ""
            client_tel = t["client_tel"] or ""
            pc = f"{t['pc_marque'] or ''} {t['pc_modele'] or ''}".strip()
            date_dep = t["date_depot"] or ""
            date_ret = t["date_retrait"] or ""
            mt = float(t["montant_total"] or 0)
            mp = float(t["montant_paye"] or 0)
            mr = float(t["montant_restant"] or 0)

            travaux = t["travaux_effectues"] or ""
            if not travaux:
                diag = t["diagnostic_initial"] or ""
                if diag:
                    travaux = "Travaux effectués : " + diag

            self.lbl_client.configure(text=client_nom)
            self.lbl_tel.configure(text=client_tel)
            self.lbl_pc.configure(text=pc)
            self.lbl_date_dep.configure(text=date_dep)
            self.lbl_date_ret.configure(text=date_ret)
            self.lbl_mt_total.configure(text=f"{mt:.2f} DA")
            self.lbl_mt_paye.configure(text=f"{mp:.2f} DA")
            self.lbl_mt_reste.configure(text=f"{mr:.2f} DA")

            self.travaux_text.delete("1.0", "end")
            self.travaux_text.insert("1.0", travaux)

        # Mode Occasions
        elif type_actuel == "Occasions":
            try:
                cur = self.db.cursor
                cur.execute("SELECT * FROM occasion_achats WHERE id = ?", (tid,))
                r = cur.fetchone()
            except Exception as e:
                messagebox.showerror("Historique", f"Erreur lecture achat d'occasion : {e}")
                return
            if not r:
                messagebox.showerror("Historique", "Achat d'occasion introuvable en base.")
                return

            self.current_ticket_id = tid

            client_nom = (r["vendeur_nom"] or "") + (
                " " + (r["vendeur_prenom"] or "") if r["vendeur_prenom"] else ""
            )
            client_tel = r["vendeur_tel"] or ""
            pc = f"{r['tel_marque'] or ''} {r['tel_nom'] or ''} IMEI:{r['tel_imei'] or ''}".strip()
            date_dep = r["date_achat"] or ""
            date_ret = ""
            mt = 0.0
            mp = 0.0
            mr = 0.0

            lignes = []
            lignes.append("Achat téléphone d'occasion.")
            lignes.append("")
            lignes.append(f"Type pièce : {r['vendeur_piece_type'] or ''}")
            lignes.append(f"N° pièce   : {r['vendeur_piece_num'] or ''}")
            lignes.append(f"Lieu deliv.: {r['vendeur_piece_lieu'] or ''}")
            lignes.append(f"Date deliv.: {r['vendeur_piece_date'] or ''}")
            lignes.append(f"Adresse    : {r['vendeur_adresse'] or ''}")
            travaux = "\n".join(lignes)

            self.lbl_client.configure(text=client_nom)
            self.lbl_tel.configure(text=client_tel)
            self.lbl_pc.configure(text=pc)
            self.lbl_date_dep.configure(text=date_dep)
            self.lbl_date_ret.configure(text=date_ret)
            self.lbl_mt_total.configure(text=f"{mt:.2f} DA")
            self.lbl_mt_paye.configure(text=f"{mp:.2f} DA")
            self.lbl_mt_reste.configure(text=f"{mr:.2f} DA")

            self.travaux_text.delete("1.0", "end")
            self.travaux_text.insert("1.0", travaux)

        # Mode Ventes
        else:
            try:
                cur = self.db.cursor
                cur.execute("SELECT * FROM ventes WHERE id = ?", (tid,))
                v = cur.fetchone()
            except Exception as e:
                messagebox.showerror("Historique", f"Erreur lecture vente : {e}")
                return
            if not v:
                messagebox.showerror("Historique", "Vente introuvable en base.")
                return

            self.current_ticket_id = tid

            client_nom = v["client_nom"] or "Vente comptoir"
            client_tel = ""
            date_heure = v["date_heure"] or ""
            mt = float(v["montant_total"] or 0)
            mp = float(v["montant_paye"] or 0)
            mr = 0.0

            # Conversion date
            date_dep = date_heure
            try:
                dt = datetime.strptime(date_heure, "%Y-%m-%d %H:%M:%S")
                date_dep = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

            # Détails de la vente
            try:
                details = self.db.get_details_vente(tid)
            except Exception as e:
                details = []
                messagebox.showerror("Historique", f"Erreur lecture détails de vente : {e}")

            lignes = []
            lignes.append("Détails de la vente au comptoir :")
            lignes.append("")
            for d in details:
                lib = d["libelle"] or ""
                qte = float(d["quantite"] or 0)
                pu = float(d["prix_unitaire"] or 0)
                st = float(d["sous_total"] or 0)
                lignes.append(f"- {lib} | Qté: {qte:.0f} | PU: {pu:.2f} | Total: {st:.2f}")
            if not details:
                lignes.append("(aucun détail trouvé)")
            travaux = "\n".join(lignes)

            pc_resume = f"Vente comptoir - {len(details)} article(s)" if details else "Vente comptoir"

            self.lbl_client.configure(text=client_nom)
            self.lbl_tel.configure(text=client_tel)
            self.lbl_pc.configure(text=pc_resume)
            self.lbl_date_dep.configure(text=date_dep)
            self.lbl_date_ret.configure(text="")
            self.lbl_mt_total.configure(text=f"{mt:.2f} DA")
            self.lbl_mt_paye.configure(text=f"{mp:.2f} DA")
            self.lbl_mt_reste.configure(text=f"{mr:.2f} DA")

            self.travaux_text.delete("1.0", "end")
            self.travaux_text.insert("1.0", travaux)

    # ---------------------------------------------------------
    # SUPPRESSION (ADMIN)
    # ---------------------------------------------------------
    def _supprimer_selection(self):
        """Suppression d'un élément de l'historique (admin requis)."""
        if not self.current_ticket_id:
            messagebox.showinfo("Historique", "Sélectionnez d'abord un élément dans la liste.")
            return

        # Demande droit administrateur
        if not hasattr(self.app, "demander_admin") or not self.app.demander_admin():
            return

        type_actuel = self.histo_type_var.get()

        if type_actuel == "Réparations":
            # On ne supprime pas physiquement, on change juste le statut
            if not messagebox.askyesno(
                "Historique",
                "Marquer ce ticket de réparation comme SUPPRIMÉ ?\n"
                "Il ne sera plus visible dans l'historique.",
            ):
                return
            try:
                cur = self.db.cursor
                cur.execute(
                    "UPDATE tickets_reparation SET statut = ? WHERE id = ?",
                    ("Supprimé", self.current_ticket_id)
                )
                self.db.conn.commit()
            except Exception as e:
                messagebox.showerror("Historique", f"Erreur lors de la suppression : {e}")
                return
            messagebox.showinfo("Historique", "Ticket de réparation supprimé de l'historique.")
            self.charger_historique()

        elif type_actuel == "Occasions":
            # Occasions : suppression physique de l'achat
            if not messagebox.askyesno(
                "Historique",
                "Supprimer définitivement cet achat d'occasion ?",
            ):
                return
            try:
                cur = self.db.cursor
                cur.execute("DELETE FROM occasion_achats WHERE id = ?", (self.current_ticket_id,))
                self.db.conn.commit()
            except Exception as e:
                messagebox.showerror("Historique", f"Erreur lors de la suppression : {e}")
                return
            messagebox.showinfo("Historique", "Achat d'occasion supprimé de l'historique.")
            self.charger_historique_occasions()

        else:
            # Ventes : on ne supprime pas pour ne pas casser la caisse / stock
            messagebox.showwarning(
                "Historique",
                "La suppression des ventes n'est pas autorisée depuis l'historique.\n"
                "Pour garder la cohérence du stock et des caisses, les ventes restent en base."
            )
            return

        self._reset_detail()

    # ---------------------------------------------------------
    # PRÉVISUALISATION FACTURE / FICHE
    # ---------------------------------------------------------
    def _previsualiser_facture(self):
        if not self.current_ticket_id:
            messagebox.showinfo("Facture", "Sélectionnez d'abord un élément dans la liste.")
            return

        type_actuel = self.histo_type_var.get()

        # Mode Réparations : facture réparation téléphone
        if type_actuel == "Réparations":
            try:
                t = self.db.get_ticket_by_id(self.current_ticket_id)
            except Exception as e:
                messagebox.showerror("Facture", f"Erreur lecture ticket : {e}")
                return
            if not t:
                messagebox.showerror("Facture", "Ticket introuvable en base.")
                return

            client_nom = t["client_nom"] or ""
            client_tel = t["client_tel"] or ""
            pc = f"{t['pc_marque'] or ''} {t['pc_modele'] or ''}".strip()
            serie = t["pc_num_serie"] or ""
            date_dep = t["date_depot"] or ""
            date_ret = t["date_retrait"] or ""
            mt = float(t["montant_total"] or 0)
            mp = float(t["montant_paye"] or 0)
            mr = float(t["montant_restant"] or 0)

            travaux = t["travaux_effectues"] or ""
            if not travaux:
                diag = t["diagnostic_initial"] or ""
                if diag:
                    travaux = "Travaux effectués : " + diag

            store_name = getattr(self.app, "store_name", "MAGASIN") or "MAGASIN"

            texte = (
                f"{store_name}\n"
                "----------------------------------------\n"
                "FACTURE RÉPARATION TÉLÉPHONE\n"
                "----------------------------------------\n"
                f"Date dépôt  : {date_dep}\n"
                f"Date retrait: {date_ret}\n"
                f"Client      : {client_nom}\n"
                f"Tél client  : {client_tel}\n"
                f"Téléphone   : {pc}\n"
                f"N° Série    : {serie}\n"
                "----------------------------------------\n"
                "Travaux effectués :\n"
                f"{travaux}\n"
                "----------------------------------------\n"
                f"Montant total : {mt:.2f} DA\n"
                f"Montant payé  : {mp:.2f} DA\n"
                f"Reste dû      : {mr:.2f} DA\n"
                "----------------------------------------\n"
                "Merci pour votre confiance.\n"
            )

        # Mode Occasions : fiche d'achat
        elif type_actuel == "Occasions":
            try:
                cur = self.db.cursor
                cur.execute("SELECT * FROM occasion_achats WHERE id = ?", (self.current_ticket_id,))
                r = cur.fetchone()
            except Exception as e:
                messagebox.showerror("Facture", f"Erreur lecture achat d'occasion : {e}")
                return
            if not r:
                messagebox.showerror("Facture", "Achat d'occasion introuvable en base.")
                return

            vendeur = (r["vendeur_nom"] or "") + (
                " " + (r["vendeur_prenom"] or "") if r["vendeur_prenom"] else ""
            )
            vendeur_tel = r["vendeur_tel"] or ""
            vendeur_adr = r["vendeur_adresse"] or ""
            tel = f"{r['tel_marque'] or ''} {r['tel_nom'] or ''}".strip()
            imei = r["tel_imei"] or ""
            date_achat = r["date_achat"] or ""
            piece_type = r["vendeur_piece_type"] or ""
            piece_num = r["vendeur_piece_num"] or ""
            piece_lieu = r["vendeur_piece_lieu"] or ""
            piece_date = r["vendeur_piece_date"] or ""

            store_name = getattr(self.app, "store_name", "MAGASIN") or "MAGASIN"

            texte = (
                f"{store_name}\n"
                "----------------------------------------\n"
                "FICHE ACHAT TÉLÉPHONE D'OCCASION\n"
                "----------------------------------------\n"
                f"Date achat  : {date_achat}\n"
                f"Vendeur     : {vendeur}\n"
                f"Tél vendeur : {vendeur_tel}\n"
                f"Adresse     : {vendeur_adr}\n"
                "----------------------------------------\n"
                f"Téléphone   : {tel}\n"
                f"IMEI        : {imei}\n"
                "----------------------------------------\n"
                f"Pièce       : {piece_type}\n"
                f"N° pièce    : {piece_num}\n"
                f"Lieu deliv. : {piece_lieu}\n"
                f"Date deliv. : {piece_date}\n"
                "----------------------------------------\n"
                "Document interne - achat d'occasion.\n"
            )

        # Mode Ventes : facture de vente
        else:
            try:
                cur = self.db.cursor
                cur.execute("SELECT * FROM ventes WHERE id = ?", (self.current_ticket_id,))
                v = cur.fetchone()
            except Exception as e:
                messagebox.showerror("Facture", f"Erreur lecture vente : {e}")
                return
            if not v:
                messagebox.showerror("Facture", "Vente introuvable en base.")
                return

            client_nom = v["client_nom"] or "Vente comptoir"
            date_heure = v["date_heure"] or ""
            mode_paiement = v["mode_paiement"] or ""
            mt = float(v["montant_total"] or 0)
            mp = float(v["montant_paye"] or 0)
            monnaie = float(v["monnaie_rendue"] or 0)
            mr = 0.0

            # Conversion date
            date_aff = date_heure
            try:
                dt = datetime.strptime(date_heure, "%Y-%m-%d %H:%M:%S")
                date_aff = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

            # Détails
            try:
                details = self.db.get_details_vente(self.current_ticket_id)
            except Exception as e:
                details = []
                messagebox.showerror("Facture", f"Erreur lecture détails de vente : {e}")

            lignes = []
            lignes.append("Détails de la vente :")
            lignes.append("")
            for d in details:
                lib = d["libelle"] or ""
                qte = float(d["quantite"] or 0)
                pu = float(d["prix_unitaire"] or 0)
                st = float(d["sous_total"] or 0)
                lignes.append(f"- {lib} | Qté: {qte:.0f} | PU: {pu:.2f} | Total: {st:.2f}")
            if not details:
                lignes.append("(aucun détail trouvé)")
            lignes_txt = "\n".join(lignes)

            store_name = getattr(self.app, "store_name", "MAGASIN") or "MAGASIN"

            texte = (
                f"{store_name}\n"
                "----------------------------------------\n"
                "FACTURE VENTE AU COMPTOIR\n"
                "----------------------------------------\n"
                f"Date/heure  : {date_aff}\n"
                f"Client      : {client_nom}\n"
                f"Mode pay.   : {mode_paiement}\n"
                "----------------------------------------\n"
                f"{lignes_txt}\n"
                "----------------------------------------\n"
                f"Montant total : {mt:.2f} DA\n"
                f"Montant payé  : {mp:.2f} DA\n"
                f"Monnaie       : {monnaie:.2f} DA\n"
                "----------------------------------------\n"
                "Merci pour votre achat.\n"
            )

        # Fenêtre d'aperçu
        fen = ctk.CTkToplevel(self.app.root)
        fen.title(f"Aperçu - #{self.current_ticket_id}")
        fen.geometry("480x540")

        txt = ctk.CTkTextbox(fen, wrap="word")
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", texte)

        ctk.CTkButton(
            fen, text="Fermer",
            fg_color="#6a1b9a", hover_color="#4a148c",
            text_color="white",
            command=fen.destroy
        ).pack(pady=6)
        fen.grab_set()
        fen.focus_set()
