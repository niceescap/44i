#!/usr/bin/env python3
"""
Detector Remarquables — Dame de Trèfle
Module importable : detecter_remarquables(cartes) → liste de balises

Deux types détectés :
  Type 1 — Répertoriées : 2/3/4 cartes de même valeur (As→7), signification spécifique
  Type 2 — Génériques   : 2/3/4 petites cartes (2→6) ou suite 3+ consécutives → qualité harmonie

Balise retournée :
{
    "type":          "remarquable",
    "sous_type":     "carre|tierce|paire|suite",
    "cartes":        ["AC", "AH", ...],
    "signification": "..." ou None,
    "qualite":       "harmonie"
}
"""

from itertools import combinations

# ---------- ASSOCIATIONS RÉPERTORIÉES ----------
# Clé : "{quantite}_{valeur}"  ex: "4_A", "2_9"
ASSOCIATIONS_REPERTORIEES = {
    # Carrés
    "4_A":  "Un grand succès. La chance frappe à votre porte, saisissez l'opportunité.",
    "4_K":  "Appui, protection importante dans le travail ou l'environnement social.",
    "4_Q":  "Risque de médisances, de rivalités : faites preuve de prudence.",
    "4_J":  "Pourparlers, discussions constructives malgré les possibilités de tensions.",
    "4_10": "Changement important de la vie sur le point de se réaliser.",
    "4_9":  "Poursuivre ses efforts. Stabilité, équilibre retrouvé.",
    "4_8":  "Mariage ou union, association ou contrat signé.",
    "4_7":  "Grossesse, naissance, aboutissement d'un projet.",
    # Tierces
    "3_A":  "Équilibre, harmonie.",
    "3_K":  "Chance, amitié solide et durable.",
    "3_Q":  "Commérages, mésentente, tension dans le domaine affectif.",
    "3_J":  "Mésentente, déséquilibre dans les relations sociales.",
    "3_10": "Dettes, litiges possibles.",
    "3_9":  "Espoir, objectif atteint, aucune hésitation à avoir.",
    "3_8":  "Soucis, angoisse, désaccord dans le milieu familial.",
    "3_7":  "Début d'un projet, des décisions seront à prendre.",
    # Paires
    "2_A":  "Union, mariage, réconciliation.",
    "2_K":  "Découragement, sentiment de blocage. Patience.",
    "2_Q":  "Amitié mise à l'épreuve, risque de diffamation.",
    "2_J":  "Renaissance, projets agréables.",
    "2_10": "Évolution, changement positif après quelques difficultés.",
    "2_9":  "Changements professionnels, gains.",
    "2_8":  "Dispute, mésentente dans le couple.",
    "2_7":  "Obstacle dans le domaine professionnel ou sentimental.",
}

# Ordre des valeurs pour détecter les suites
ORDRE_VALEURS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
VALEURS_PETITES = {"2", "3", "4", "5", "6"}

SOUS_TYPE = {2: "paire", 3: "tierce", 4: "carre"}

# ---------- UTILITAIRES ----------
def valeur(code: str) -> str:
    """Extrait la valeur d'un code carte. '10H' → '10', 'AC' → 'A'"""
    return code[:-1]

def couleur(code: str) -> str:
    """Extrait la couleur d'un code carte. '10H' → 'H', 'AC' → 'C'"""
    return code[-1]

def indice_valeur(v: str) -> int:
    try:
        return ORDRE_VALEURS.index(v)
    except ValueError:
        return -1

# ---------- DÉTECTION ----------
def detecter_groupes(cartes: list) -> list:
    """Détecte les groupes de cartes de même valeur (paires, tierces, carrés)."""
    balises = []
    valeurs_map = {}

    for carte in cartes:
        v = valeur(carte)
        valeurs_map.setdefault(v, []).append(carte)

    for v, groupe in valeurs_map.items():
        n = len(groupe)
        if n < 2:
            continue

        sous_type = SOUS_TYPE.get(n, "carre")
        cle       = f"{n}_{v}"

        # Type 1 — répertoriée
        if cle in ASSOCIATIONS_REPERTORIEES:
            balises.append({
                "type":          "remarquable",
                "sous_type":     sous_type,
                "cartes":        groupe,
                "signification": ASSOCIATIONS_REPERTORIEES[cle],
                "qualite":       "harmonie"
            })
        # Type 2 — générique (petites cartes non répertoriées)
        elif v in VALEURS_PETITES:
            balises.append({
                "type":          "remarquable",
                "sous_type":     sous_type,
                "cartes":        groupe,
                "signification": None,
                "qualite":       "harmonie"
            })

    return balises

def detecter_suites(cartes: list) -> list:
    """Détecte les suites consécutives d'au moins 3 cartes."""
    balises  = []
    valeurs  = [(indice_valeur(valeur(c)), c) for c in cartes]
    valeurs  = [(i, c) for i, c in valeurs if i >= 0]
    valeurs.sort(key=lambda x: x[0])

    # Chercher toutes les suites de longueur >= 3
    n = len(valeurs)
    i = 0
    while i < n:
        suite = [valeurs[i]]
        j = i + 1
        while j < n and valeurs[j][0] == valeurs[j-1][0] + 1:
            suite.append(valeurs[j])
            j += 1
        if len(suite) >= 3:
            balises.append({
                "type":          "remarquable",
                "sous_type":     "suite",
                "cartes":        [c for _, c in suite],
                "signification": None,
                "qualite":       "harmonie"
            })
            i = j
        else:
            i += 1

    return balises

def detecter_remarquables(cartes: list) -> list:
    """
    Point d'entrée principal.
    Prend une liste de codes cartes, retourne les balises détectées.
    """
    balises  = detecter_groupes(cartes)
    balises += detecter_suites(cartes)
    return balises


