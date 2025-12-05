import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Dossier du fichier database.py (dans le projet ou dans le bundle PyInstaller)
BASE_DIR = Path(__file__).resolve().parent

# Ancien dossier "data" à côté de database.py (toujours utilisé en mode développement)
DATA_DIR = BASE_DIR / "data"


def _get_default_db_path() -> Path:
    """
    Calcule un chemin par défaut pour la base de données.

    - En mode normal (lancé avec python main.py) :
        -> utilise <projet>/data/magasin.db (comme avant).
    - En mode exécutable PyInstaller (sys.frozen == True, ex: Program Files) :
        -> utilise un dossier utilisateur en écriture, par exemple :
           C:\\Users\\<utilisateur>\\AppData\\Roaming\\pyramide\\magasin.db
    """
    try:
        # Si l'appli est packagée par PyInstaller (exe)
        if getattr(sys, "frozen", False):
            if os.name == "nt":
                # Windows : APPDATA (Roaming)
                base = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
            else:
                # Linux / macOS : répertoire personnel
                base = Path.home()

            app_dir = base / "pyramide"
            app_dir.mkdir(parents=True, exist_ok=True)
            return app_dir / "magasin.db"

        # Mode développement : on reste dans <projet>/data/
        else:
            DATA_DIR.mkdir(exist_ok=True)
            return DATA_DIR / "magasin.db"

    except Exception:
        # En cas de problème, on tente au moins d'utiliser le dossier courant
        fallback_dir = Path.cwd()
        return fallback_dir / "magasin.db"


# Chemin par défaut de la base
DEFAULT_DB_PATH = _get_default_db_path()


class Database:
    def __init__(self, db_name=None):
        """
        db_name : chemin vers la base SQLite.
        - Si None, on utilise un emplacement par défaut :
          * En dev : <projet>/data/magasin.db
          * En exe (PyInstaller) : dossier utilisateur (APPDATA\\pyramide\\magasin.db)
        """
        if db_name is None:
            db_name = DEFAULT_DB_PATH

        # Connexion à la base SQLite
        self.conn = sqlite3.connect(str(db_name))
        # les lignes retournées seront des objets "Row" accessibles par nom de colonne
        self.conn.row_factory = sqlite3.Row
        # Activation des clés étrangères (par sécurité)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Création de toutes les tables nécessaires."""

        # ---------- TABLE CLIENTS ----------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prenom TEXT,
                telephone TEXT,
                email TEXT,
                adresse TEXT
            )
        """)

        # ---------- TABLE TICKETS DE RÉPARATION (DÉPÔT + RÉCEPTION) ----------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets_reparation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Infos client (simple pour l'instant)
                client_nom      TEXT NOT NULL,
                client_tel      TEXT,

                -- Infos téléphone (anciennement PC)
                pc_marque       TEXT NOT NULL,
                pc_modele       TEXT,
                pc_num_serie    TEXT,

                -- Accessoires remis
                avec_chargeur   INTEGER NOT NULL DEFAULT 0,  -- 0 = non, 1 = oui
                avec_batterie   INTEGER NOT NULL DEFAULT 0,  -- 0 = non, 1 = oui

                -- Dépôt
                diagnostic_initial TEXT,
                date_depot         TEXT NOT NULL,           -- ex: "01/12/2025"

                -- Réception / réparation
                travaux_effectues  TEXT,
                date_retrait       TEXT,                    -- rempli à la réception
                montant_total      REAL,
                montant_paye       REAL,
                montant_restant    REAL,

                -- Statut global
                statut TEXT NOT NULL DEFAULT 'En cours'     -- En cours / Terminé / Livré / Annulé / Supprimé...
            )
        """)

        # ---------- TABLE CRÉANCES / DETTES ----------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS creances_dettes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ticket_id       INTEGER,      -- lien vers ticket de réparation (optionnel)
                client_nom      TEXT NOT NULL,
                pc_marque       TEXT,
                description     TEXT,        -- ce qu'on a réparé / remarque
                montant_total   REAL NOT NULL,
                montant_paye    REAL NOT NULL,
                montant_restant REAL NOT NULL,
                date_retrait    TEXT NOT NULL,

                FOREIGN KEY (ticket_id) REFERENCES tickets_reparation(id)
            )
        """)

        # ---------- TABLE PRODUITS / STOCK ----------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS produits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_barres TEXT,             -- code-barres éventuel
                reference  TEXT,              -- référence interne
                nom        TEXT NOT NULL,     -- nom du produit
                categorie  TEXT,              -- ex: Téléphone, Accessoire, Composant...
                description TEXT,             -- infos supplémentaires
                prix_achat REAL NOT NULL DEFAULT 0,
                prix_vente REAL NOT NULL DEFAULT 0,
                quantite   INTEGER NOT NULL DEFAULT 0,
                seuil_alerte INTEGER NOT NULL DEFAULT 0,
                actif      INTEGER NOT NULL DEFAULT 1  -- 1 = actif, 0 = désactivé
            )
        """)

        # ---------- TABLE VENTES AU COMPTOIR ----------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_heure     TEXT NOT NULL,      -- "2025-12-01 14:30:00"
                caisse_id      INTEGER,            -- caisse utilisée
                client_nom     TEXT,               -- pour l'instant texte libre
                mode_paiement  TEXT NOT NULL,      -- espece / carte / autre
                montant_total  REAL NOT NULL,
                montant_paye   REAL NOT NULL,
                monnaie_rendue REAL NOT NULL,
                FOREIGN KEY (caisse_id) REFERENCES caisses(id)
            )
        """)

        # ---------- TABLE DÉTAILS DE VENTE ----------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS details_ventes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vente_id    INTEGER NOT NULL,
                produit_id  INTEGER,          -- NULL si produit manuel
                libelle     TEXT,             -- nom du produit manuel
                quantite    REAL NOT NULL,
                prix_unitaire REAL NOT NULL,
                sous_total  REAL NOT NULL,
                FOREIGN KEY (vente_id) REFERENCES ventes(id),
                FOREIGN KEY (produit_id) REFERENCES produits(id)
            )
        """)

        # ---------- TABLE CAISSES ----------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS caisses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL UNIQUE,
                description TEXT
            )
        """)

        # ---------- TABLE MOUVEMENTS DE CAISSE ----------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS mouvements_caisse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caisse_id INTEGER NOT NULL,
                date_mouvement TEXT NOT NULL,   -- "01/12/2025 10:30"
                type TEXT NOT NULL,             -- 'ENTREE' ou 'SORTIE'
                montant REAL NOT NULL,
                description TEXT,
                FOREIGN KEY (caisse_id) REFERENCES caisses(id)
            )
        """)

        self.conn.commit()

        # Créer des caisses par défaut si aucune
        self.initialiser_caisses()

    # ============================================================
    # CLIENTS
    # ============================================================

    def ajouter_client(self, nom, prenom="", telephone="", email="", adresse=""):
        self.cursor.execute("""
            INSERT INTO clients (nom, prenom, telephone, email, adresse)
            VALUES (?, ?, ?, ?, ?)
        """, (nom, prenom, telephone, email, adresse))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_clients(self):
        self.cursor.execute("SELECT * FROM clients ORDER BY nom")
        return self.cursor.fetchall()

    # ============================================================
    # TICKETS DE RÉPARATION (DÉPÔT / RÉCEPTION)
    # ============================================================

    def ajouter_ticket_depot(self, client_nom, pc_marque,
                             date_depot,
                             diagnostic_initial="",
                             avec_chargeur=False,
                             avec_batterie=False,
                             client_tel="",
                             pc_modele="",
                             pc_num_serie=""):
        """
        Enregistre un dépôt de téléphone (bon de dépôt).
        """
        self.cursor.execute("""
            INSERT INTO tickets_reparation
            (client_nom, client_tel,
             pc_marque, pc_modele, pc_num_serie,
             avec_chargeur, avec_batterie,
             diagnostic_initial, date_depot,
             travaux_effectues, date_retrait,
             montant_total, montant_paye, montant_restant,
             statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, 'En cours')
        """, (
            client_nom, client_tel,
            pc_marque, pc_modele, pc_num_serie,
            1 if avec_chargeur else 0,
            1 if avec_batterie else 0,
            diagnostic_initial, date_depot
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_tickets(self, statut=None):
        """
        Récupère les tickets de réparation.
        Si statut est donné, filtre par statut ('En cours', 'Terminé', 'Livré', etc.).
        """
        if statut:
            self.cursor.execute("""
                SELECT * FROM tickets_reparation
                WHERE statut = ?
                ORDER BY date_depot DESC, id DESC
            """, (statut,))
        else:
            self.cursor.execute("""
                SELECT * FROM tickets_reparation
                ORDER BY date_depot DESC, id DESC
            """)
        return self.cursor.fetchall()

    def get_ticket_by_id(self, ticket_id):
        """Retourne un ticket de réparation par son ID."""
        self.cursor.execute("""
            SELECT * FROM tickets_reparation
            WHERE id = ?
        """, (ticket_id,))
        return self.cursor.fetchone()

    def enregistrer_reception_pc(self, ticket_id, travaux_effectues,
                                 montant_total, montant_paye,
                                 date_retrait=None, statut="Livré"):
        """
        Met à jour un ticket lors de la réception / récupération du téléphone.

        - ticket_id : ID du ticket dans tickets_reparation
        - travaux_effectues : texte décrivant la réparation
        - montant_total : montant total de la réparation
        - montant_paye : ce que le client paye maintenant
        - date_retrait : date de retrait (jj/mm/aaaa), aujourd'hui par défaut
        - statut : 'Livré' (par défaut), ou 'Terminé', etc.

        Retourne le montant restant à payer (>= 0).
        """
        if date_retrait is None:
            date_retrait = datetime.now().strftime("%d/%m/%Y")

        montant_total = float(montant_total or 0)
        montant_paye = float(montant_paye or 0)
        montant_restant = montant_total - montant_paye
        if montant_restant < 0:
            montant_restant = 0.0

        self.cursor.execute("""
            UPDATE tickets_reparation
            SET travaux_effectues = ?,
                date_retrait = ?,
                montant_total = ?,
                montant_paye = ?,
                montant_restant = ?,
                statut = ?
            WHERE id = ?
        """, (
            travaux_effectues,
            date_retrait,
            montant_total,
            montant_paye,
            montant_restant,
            statut,
            ticket_id
        ))
        self.conn.commit()
        return montant_restant

    # ============================================================
    # CRÉANCES / DETTES
    # ============================================================

    def ajouter_creance(self, client_nom, pc_marque, description,
                        montant_total, montant_paye, montant_restant, date_retrait,
                        ticket_id=None):
        """
        Ajoute une créance / dette dans la base.
        ticket_id est optionnel (None dans ton interface actuelle).
        """
        self.cursor.execute("""
            INSERT INTO creances_dettes
            (ticket_id, client_nom, pc_marque, description,
             montant_total, montant_paye, montant_restant, date_retrait)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_id,
            client_nom,
            pc_marque,
            description,
            float(montant_total),
            float(montant_paye),
            float(montant_restant),
            date_retrait
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_creances(self):
        """Récupère toutes les créances / dettes."""
        self.cursor.execute("""
            SELECT * FROM creances_dettes
            ORDER BY date_retrait DESC, id DESC
        """)
        return self.cursor.fetchall()

    def mettre_a_jour_creance(self, creance_id, montant_paye, montant_restant):
        """
        Met à jour les montants d'une créance existante.
        """
        self.cursor.execute("""
            UPDATE creances_dettes
            SET montant_paye = ?, montant_restant = ?
            WHERE id = ?
        """, (float(montant_paye), float(montant_restant), creance_id))
        self.conn.commit()

    def supprimer_creance(self, creance_id):
        """
        Supprime définitivement une créance / dette.
        (Utilisé pour effacer les créances dont le reste à payer est 0.)
        """
        self.cursor.execute("""
            DELETE FROM creances_dettes
            WHERE id = ?
        """, (creance_id,))
        self.conn.commit()

    # ============================================================
    # PRODUITS / STOCK
    # ============================================================

    def ajouter_produit(self, nom, code_barres="",
                        reference="", categorie="", description="",
                        prix_achat=0.0, prix_vente=0.0,
                        quantite=0, seuil_alerte=0):
        """
        Ajoute un produit dans le stock.
        """
        self.cursor.execute("""
            INSERT INTO produits
            (code_barres, reference, nom, categorie, description,
             prix_achat, prix_vente, quantite, seuil_alerte, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            code_barres or None,
            reference or None,
            nom,
            categorie or None,
            description or None,
            float(prix_achat),
            float(prix_vente),
            int(quantite),
            int(seuil_alerte),
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_produits(self, uniquement_actifs=True):
        """
        Retourne la liste des produits.
        Si uniquement_actifs=True, ne retourne que ceux avec actif=1.
        """
        if uniquement_actifs:
            self.cursor.execute("""
                SELECT * FROM produits
                WHERE actif = 1
                ORDER BY nom
            """)
        else:
            self.cursor.execute("""
                SELECT * FROM produits
                ORDER BY nom
            """)
        return self.cursor.fetchall()

    def rechercher_produits(self, terme, uniquement_actifs=True):
        """
        Recherche par nom, référence, code_barres ou catégorie.
        """
        like = f"%{terme}%"
        if uniquement_actifs:
            self.cursor.execute("""
                SELECT * FROM produits
                WHERE actif = 1
                  AND (nom LIKE ? OR reference LIKE ? OR code_barres LIKE ? OR categorie LIKE ?)
                ORDER BY nom
            """, (like, like, like, like))
        else:
            self.cursor.execute("""
                SELECT * FROM produits
                WHERE (nom LIKE ? OR reference LIKE ? OR code_barres LIKE ? OR categorie LIKE ?)
                ORDER BY nom
            """, (like, like, like, like))
        return self.cursor.fetchall()

    def rechercher_produit_par_code(self, code_barres):
        """
        Recherche un produit par code-barres. 
        Retourne un tuple (id, nom, prix_vente, quantite, code_barres, seuil_alerte) ou None.
        """
        self.cursor.execute("""
            SELECT id, nom, prix_vente, quantite, code_barres, seuil_alerte
            FROM produits
            WHERE code_barres = ? AND actif = 1
        """, (code_barres,))
        row = self.cursor.fetchone()
        return row

    def modifier_produit(self, produit_id, nom=None, code_barres=None,
                         reference=None, categorie=None, description=None,
                         prix_achat=None, prix_vente=None,
                         quantite=None, seuil_alerte=None, actif=None):
        """
        Modifie les informations d'un produit.
        Les paramètres à None ne sont pas modifiés.
        """
        champs = []
        valeurs = []

        if nom is not None:
            champs.append("nom = ?")
            valeurs.append(nom)
        if code_barres is not None:
            champs.append("code_barres = ?")
            valeurs.append(code_barres)
        if reference is not None:
            champs.append("reference = ?")
            valeurs.append(reference)
        if categorie is not None:
            champs.append("categorie = ?")
            valeurs.append(categorie)
        if description is not None:
            champs.append("description = ?")
            valeurs.append(description)
        if prix_achat is not None:
            champs.append("prix_achat = ?")
            valeurs.append(float(prix_achat))
        if prix_vente is not None:
            champs.append("prix_vente = ?")
            valeurs.append(float(prix_vente))
        if quantite is not None:
            champs.append("quantite = ?")
            valeurs.append(int(quantite))
        if seuil_alerte is not None:
            champs.append("seuil_alerte = ?")
            valeurs.append(int(seuil_alerte))
        if actif is not None:
            champs.append("actif = ?")
            valeurs.append(1 if actif else 0)

        if not champs:
            return  # rien à modifier

        valeurs.append(produit_id)

        requete = f"UPDATE produits SET {', '.join(champs)} WHERE id = ?"
        self.cursor.execute(requete, valeurs)
        self.conn.commit()

    def supprimer_produit(self, produit_id):
        """
        Supprime définitivement un produit.
        Peut échouer si des ventes y font référence (clé étrangère).
        """
        self.cursor.execute("DELETE FROM produits WHERE id = ?", (produit_id,))
        self.conn.commit()

    def modifier_stock(self, produit_id, delta_quantite):
        """
        Modifie le stock d'un produit (ajout ou retrait).
        delta_quantite peut être positif (entrée) ou négatif (sortie).
        """
        self.cursor.execute("""
            UPDATE produits
            SET quantite = quantite + ?
            WHERE id = ?
        """, (int(delta_quantite), produit_id))
        self.conn.commit()

    def produits_stock_bas(self):
        """
        Retourne les produits dont le stock est inférieur ou égal au seuil d'alerte.
        """
        self.cursor.execute("""
            SELECT * FROM produits
            WHERE actif = 1
              AND seuil_alerte > 0
              AND quantite <= seuil_alerte
            ORDER BY nom
        """)
        return self.cursor.fetchall()

    # ============================================================
    # VENTES AU COMPTOIR
    # ============================================================

    def enregistrer_vente_comptoir(self, caisse_id, items,
                                   mode_paiement, montant_paye,
                                   monnaie_rendue, client_nom=None):
        """
        Enregistre une vente au comptoir et met à jour le stock.

        items = liste de dicts:
            {
                "produit_id": int ou None (si produit manuel),
                "nom": str,
                "quantite": float ou int,
                "prix_unitaire": float,
                "sous_total": float
            }
        """
        if not items:
            raise ValueError("La liste des articles est vide.")

        total = sum(float(it["sous_total"]) for it in items)
        date_heure = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.cursor.execute("""
            INSERT INTO ventes
            (date_heure, caisse_id, client_nom, mode_paiement,
             montant_total, montant_paye, monnaie_rendue)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            date_heure,
            caisse_id,
            client_nom,
            mode_paiement,
            float(total),
            float(montant_paye),
            float(monnaie_rendue),
        ))
        vente_id = self.cursor.lastrowid

        for it in items:
            pid = it.get("produit_id")
            nom = it.get("nom") or None
            qte = float(it.get("quantite") or 0)
            pu = float(it.get("prix_unitaire") or 0)
            st = float(it.get("sous_total") or 0)

            self.cursor.execute("""
                INSERT INTO details_ventes
                (vente_id, produit_id, libelle, quantite, prix_unitaire, sous_total)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (vente_id, pid, nom, qte, pu, st))

            if pid:
                self.modifier_stock(pid, -int(qte))

        self.conn.commit()
        return vente_id

    def get_ventes(self, date_debut=None, date_fin=None):
        """
        Retourne la liste des ventes.
        - si date_debut et date_fin (au format 'YYYY-MM-DD') sont donnés, filtre par date.
        """
        if date_debut and date_fin:
            self.cursor.execute("""
                SELECT * FROM ventes
                WHERE DATE(date_heure) BETWEEN ? AND ?
                ORDER BY date_heure DESC
            """, (date_debut, date_fin))
        else:
            self.cursor.execute("""
                SELECT * FROM ventes
                ORDER BY date_heure DESC
            """)
        return self.cursor.fetchall()

    def get_details_vente(self, vente_id):
        """
        Retourne les lignes détail pour une vente donnée.
        """
        self.cursor.execute("""
            SELECT * FROM details_ventes
            WHERE vente_id = ?
        """, (vente_id,))
        return self.cursor.fetchall()

    # ============================================================
    # CAISSES
    # ============================================================

    def initialiser_caisses(self):
        """Crée des caisses par défaut si aucune n'existe."""
        self.cursor.execute("SELECT COUNT(*) FROM caisses")
        n = self.cursor.fetchone()[0]
        if n == 0:
            self.ajouter_caisse("Caisse comptoir", "Caisse principale des ventes")
            self.ajouter_caisse("Caisse fournisseurs", "Paiement des fournisseurs")

    def ajouter_caisse(self, nom, description=""):
        self.cursor.execute("""
            INSERT OR IGNORE INTO caisses (nom, description)
            VALUES (?, ?)
        """, (nom, description))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_caisses(self):
        """Retourne la liste des caisses (id, nom, description)."""
        self.cursor.execute("SELECT id, nom, description FROM caisses ORDER BY id")
        return self.cursor.fetchall()

    # ============================================================
    # MOUVEMENTS DE CAISSE
    # ============================================================

    def ajouter_mouvement_caisse(self, caisse_id, type_mvt, montant,
                                 description="", date_mouvement=None):
        """
        Ajoute un mouvement de caisse.
        type_mvt : 'ENTREE' ou 'SORTIE'
        """
        type_mvt = (type_mvt or "").upper()
        if type_mvt not in ("ENTREE", "SORTIE"):
            raise ValueError("type_mvt doit être 'ENTREE' ou 'SORTIE'")

        if date_mouvement is None:
            date_mouvement = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        self.cursor.execute("""
            INSERT INTO mouvements_caisse
            (caisse_id, date_mouvement, type, montant, description)
            VALUES (?, ?, ?, ?, ?)
        """, (caisse_id, date_mouvement, type_mvt, float(montant), description))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_mouvements_caisse(self, caisse_id=None):
        """
        Retourne les mouvements de caisse.
        Si caisse_id est donné, filtre sur cette caisse.
        """
        if caisse_id:
            self.cursor.execute("""
                SELECT * FROM mouvements_caisse
                WHERE caisse_id = ?
                ORDER BY date_mouvement DESC, id DESC
            """, (caisse_id,))
        else:
            self.cursor.execute("""
                SELECT * FROM mouvements_caisse
                ORDER BY date_mouvement DESC, id DESC
            """)
        return self.cursor.fetchall()

    def supprimer_mouvement_caisse(self, mouvement_id: int):
        """
        Supprime définitivement un mouvement de caisse.
        """
        self.cursor.execute(
            "DELETE FROM mouvements_caisse WHERE id = ?",
            (mouvement_id,)
        )
        self.conn.commit()

    def get_solde_caisse(self, caisse_id):
        """
        Calcule le solde d'une caisse : somme(ENTREE) - somme(SORTIE)
        """
        self.cursor.execute("""
            SELECT
                COALESCE(SUM(
                    CASE WHEN type = 'ENTREE' THEN montant
                         WHEN type = 'SORTIE' THEN -montant
                    END
                ), 0)
            FROM mouvements_caisse
            WHERE caisse_id = ?
        """, (caisse_id,))
        solde = self.cursor.fetchone()[0]
        return float(solde or 0.0)

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    db = Database()
    print("Base :", DEFAULT_DB_PATH)
    print("Tables créées / vérifiées.")
    print("Clients  :", len(db.get_clients()))
    print("Tickets  :", len(db.get_tickets()))
    print("Créances :", len(db.get_creances()))
    print("Caisses  :", db.get_caisses())
    print("Mouvements de caisse :", len(db.get_mouvements_caisse()))
    produits = db.get_produits(uniquement_actifs=False)
    print("Produits :", len(produits))
    ventes = db.get_ventes()
    print("Ventes   :", len(ventes))
    db.close()
    print("OK.")
