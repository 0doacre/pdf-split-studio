# 📄 PDF Split & Merge Studio

**Application de bureau moderne, ultra-rapide et 100% hors-ligne pour la découpe, la fusion, la compression et la sécurisation de documents PDF.**

---

## 🌟 Points Forts & Fonctionnalités

### 1. ✂️ Modes de Découpage Avancés
* **Page par page** : Découpe l'ensemble du PDF en fichiers indépendants d'une page chacun (`nom_page_1.pdf`, `nom_page_2.pdf`...).
* **Par intervalle régulier (Paquets de N pages)** : Découpe le PDF tous les *N* pages (ex: par 2 pages, par 5 pages...).
* **En X parties égales** : Divise équitablement le document en un nombre prédéfini de fichiers.
* **Plages personnalisées** : Saisie libre d'intervalles (ex: `1-3, 5, 8-12`) avec option de générer des fichiers distincts ou de fusionner les plages choisies en un seul fichier.
* **Sélection visuelle interactive** : Grille avec miniatures de toutes les pages générées à la volée. Filtres en un clic (*Tout cocher, Décocher, Pages paires, Pages impaires, Inverser*).
  * Option : *Extraire chaque page cochée séparément*
  * Option : *Fusionner la sélection en un seul PDF*
  * Option : *Supprimer les pages cochées (garder le reste)*
* **Points de coupure** : Découpe le PDF après des pages spécifiques (ex: couper après la page 3 et la page 7).

### 2. 📁 Gestion du Dossier de Destination
* **Automatique (Dossier Source)** : Exporte directement dans le dossier d'où provient le PDF d'origine.
* **Sous-dossier dédié** : Option cochée par défaut pour créer un sous-dossier propre (ex: `NomDuFichier_decoupe/`), évitant d'encombrer le répertoire source.
* **Dossier Personnalisé** : Sélection libre de n'importe quel dossier via l'explorateur Windows natif.
* **Bouton Direct** : *« Ouvrir le dossier dans l'Explorateur »* disponible dès la fin de chaque traitement.

### 3. 💎 Qualité Source vs Compression de Taille
* **Qualité Originale (100% Sans Perte / Lossless)** : Préservation stricte au bit près des données vectorielles, polices et résolutions d'images originales.
* **Qualité Haute (200 DPI, JPEG 85%)** : Légère optimisation pour documents textuels et impressions.
* **Qualité Standard (150 DPI, JPEG 75%)** : Équilibre parfait pour envoi par e-mail et partage web.
* **Forte Compression (96 DPI, JPEG 55%)** : Réduction agressive de la taille du fichier.
* **Personnalisée** : Curseurs dynamiques de résolution (DPI de 72 à 300) et de qualité de compression JPEG (30% à 95%).
* Optimisation interne des flux de contenu et déduplication des objets répétitifs (polices, logos).

### 4. 🔗 Fusion de Multiples PDF (Merge)
* Ajout de multiples fichiers PDF par sélection multiple ou glisser-déposer.
* Réorganisation libre de l'ordre des documents (boutons ⬆️ et ⬇️).
* Filtrage des pages à inclure par fichier (ex: inclure seulement les pages `1-5` du doc A et `2, 4-6` du doc B).
* Choix du nom du fichier de sortie (`Document_fusionne.pdf`).
* Choix de la qualité et du dossier de destination.

### 5. 🔄 Organiseur Visuel & Rotation
* Rotation individuelle de chaque page par pas de 90° dans le sens horaire.
* Rotation globale de toutes les pages en un clic (`Tourner tout +90°`).
* Aperçu haute résolution plein écran par simple clic sur une miniature.

### 6. 🔒 Sécurité & Confidentialité Totale
* **100% Hors-ligne** : Aucune donnée ne quitte votre ordinateur. Aucune requête réseau externe, aucune dépendance CDN distante.
* **Nettoyeur de métadonnées** : Élimine les métadonnées cachées (nom de l'auteur, logiciel de création, historique, date de modification) avant export.
* **Chiffrement AES-256** : Protection optionnelle de tout fichier exporté par un mot de passe fort.

---

## 🚀 Comment Lancer le Logiciel

### Méthode 1 : Double-clic sur le lanceur (Recommandé)
* Double-cliquez sur **`Lancer_PDF_Split.bat`**
* Ou double-cliquez sur **`Lancer_Sans_Console.vbs`** (lancement silencieux sans fenêtre noire d'invite de commande).

### Méthode 2 : Ligne de commande
Dans le dossier du projet :
```bash
# Lancement avec fenêtre de bureau native (Edge WebView2)
python app.py

# Ou forcer l'ouverture dans votre navigateur web par défaut
python app.py --web
```

---

## 🏗️ Structure du Projet

```text
c:\projets\PDF split/
│
├── app.py                      # Lanceur principal (pywebview bureau ou navigateur)
├── Lancer_PDF_Split.bat        # Raccourci de lancement Windows
├── Lancer_Sans_Console.vbs     # Raccourci silencieux sans console
├── requirements.txt            # Dépendances Python
├── README.md                   # Documentation complète
│
├── backend/
│   ├── __init__.py
│   ├── pdf_service.py          # Logique de découpe, fusion, rotation et sécurité
│   ├── compression.py          # Moteur de compression et d'optimisation
│   ├── thumbnail_service.py    # Rendu haute vitesse des miniatures (pypdfium2)
│   └── server.py               # Serveur API FastAPI local (127.0.0.1)
│
├── frontend/
│   ├── index.html              # Interface utilisateur moderne
│   ├── css/
│   │   └── style.css           # Thème sombre glassmorphic, design premium
│   └── js/
│       └── app.js              # Logique interactive, glisser-déposer, miniatures
│
└── tests/
    ├── test_pdf_service.py     # Tests unitaires des fonctions PDF
    └── test_api_endpoints.py   # Tests d'intégration des routes API
```

---

## 🧪 Exécution des Tests de Validation

Pour vérifier le bon fonctionnement de l'ensemble du logiciel :
```bash
python -m unittest discover tests
```
Toutes les suites de tests valident les 6 modes de découpe, la fusion, la préservation de qualité, la compression, le déchiffrement et le nettoyage des métadonnées.
