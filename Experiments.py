"""Expériences du simulateur : courbes avec intervalles de confiance.

Lancer avec :  python experiments.py
(il faut matplotlib :  pip install matplotlib)

Les graphiques (textes en anglais) sont enregistrés dans le dossier  figures/
et tous les chiffres dans  figures/resultats.csv
Durée : quelques minutes. Pour aller plus vite, baisser R ci-dessous.
"""
import csv
import os
import statistics

import matplotlib
matplotlib.use("Agg")                    # pas de fenêtre : on enregistre les images
import matplotlib.pyplot as plt

from config import default_config
from simulator import Simulator
from policies import AlwaysAccept, Threshold, UtilityVsCost, Efficiency

R = 5                                    # nombre de réplications (graines différentes) par point
DOSSIER = "figures"

# Couleurs : une par politique, toujours la même
COULEURS = {"AlwaysAccept": "#2a78d6", "Threshold": "#eb6834", "UtilityVsCost": "#1baf7a",
            "Efficiency": "#eda100"}

# t de Student à 95 % selon le nombre de réplications (pour l'intervalle de confiance)
T_STUDENT = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447,
             8: 2.365, 9: 2.306, 10: 2.262}


def politiques():
    """Les 4 politiques comparées (recréées à chaque fois)."""
    return [("AlwaysAccept", AlwaysAccept()),
            ("Threshold", Threshold(15)),
            ("UtilityVsCost", UtilityVsCost(1.0)),
            ("Efficiency", Efficiency(0.5))]


# ---------------------------------------------------------------- outils
def repliquer(config, fabrique_politique):
    """Lance R simulations avec des graines différentes.
    Retourne moyenne et demi-largeur de l'IC à 95 % du blocage et de l'utilité/s."""
    blocages, utilites = [], []
    for k in range(R):
        config = dict(config, seed=1000 + k)
        r = Simulator(config, fabrique_politique()).run()
        blocages.append(r["blocking"])
        utilites.append(r["reward_per_s"])

    def moyenne_ic(xs):
        m = statistics.mean(xs)
        if len(xs) < 2:
            return m, 0.0
        return m, T_STUDENT.get(len(xs), 1.96) * statistics.stdev(xs) / len(xs) ** 0.5

    return moyenne_ic(blocages), moyenne_ic(utilites)


def style_axe(ax, titre, xlabel, ylabel):
    ax.set_title(titre, fontsize=12, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, color="#dddddd", linewidth=0.8)
    ax.set_axisbelow(True)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)


def enregistrer(fig, nom):
    os.makedirs(DOSSIER, exist_ok=True)
    chemin = os.path.join(DOSSIER, nom)
    fig.tight_layout()
    fig.savefig(chemin, dpi=150)
    plt.close(fig)
    print(f"   → graphique enregistré : {chemin}")


LIGNES_CSV = []


def noter(experience, x, politique, bl, ut):
    LIGNES_CSV.append([experience, x, politique, f"{bl[0]:.4f}", f"{bl[1]:.4f}",
                       f"{ut[0]:.4f}", f"{ut[1]:.4f}"])
    print(f"   {str(x):>8s}  {politique:15s}  blocage = {bl[0]:6.1%} ± {bl[1]:.1%}"
          f"   utilité/s = {ut[0]:5.2f} ± {ut[1]:.2f}")


def courbes(experience, valeurs_x, fabrique_config, xlabel, titre, nom_fichier):
    """Pour chaque valeur de x et chaque politique : R réplications, puis 2 graphiques."""
    print(f"\n=== {titre} ===")
    resultats = {nom: ([], []) for nom, _ in politiques()}
    for x in valeurs_x:
        for nom, _ in politiques():
            fab = lambda nom=nom: dict(politiques())[nom]
            bl, ut = repliquer(fabrique_config(x), fab)
            resultats[nom][0].append(bl)
            resultats[nom][1].append(ut)
            noter(experience, x, nom, bl, ut)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    for nom, (bls, uts) in resultats.items():
        c = COULEURS[nom]
        ax1.errorbar(valeurs_x, [b[0] * 100 for b in bls], yerr=[b[1] * 100 for b in bls],
                     color=c, marker="o", markersize=6, linewidth=2, capsize=3, label=nom)
        ax2.errorbar(valeurs_x, [u[0] for u in uts], yerr=[u[1] for u in uts],
                     color=c, marker="o", markersize=6, linewidth=2, capsize=3, label=nom)
    style_axe(ax1, "Rejection rate", xlabel, "rejected flows (%)")
    style_axe(ax2, "Utility obtained", xlabel, "utility per second")
    poignees, noms = ax1.get_legend_handles_labels()
    fig.legend(poignees, noms, loc="upper right", ncol=4, frameon=False)   # légende au-dessus des courbes
    fig.suptitle(titre, fontsize=13, x=0.01, ha="left")
    enregistrer(fig, nom_fichier)


# ---------------------------------------------------------------- expériences
def exp_charge():
    """Expérience 1 : on multiplie tous les ζj par un facteur (plus ou moins de trafic)."""
    base = default_config()["zeta"]
    courbes("load", [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
            lambda f: default_config(zeta=[z * f for z in base]),
            "load factor (× default ζ)",
            "Effect of the traffic load", "1_charge.png")


def exp_capacite():
    """Expérience 2 : on fait varier ψi (et θi proportionnellement : θi = 2 ψi Mb/s)."""
    courbes("capacity", [10, 15, 20, 25, 30],
            lambda p: default_config(psi=[p] * 4, theta=[2.0 * p] * 4),
            "capacity ψ (simultaneous flows per server), θ = 2ψ Mb/s",
            "Effect of the server capacity", "2_capacite.png")


def exp_lambda():
    """Expérience 3 : compromis rejet / utilité de UtilityVsCost selon λ."""
    print("\n=== Compromis de UtilityVsCost selon λ ===")
    lams = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
    bls, uts = [], []
    for lam in lams:
        bl, ut = repliquer(default_config(), lambda lam=lam: UtilityVsCost(lam))
        bls.append(bl)
        uts.append(ut)
        noter("lambda", lam, "UtilityVsCost", bl, ut)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    c = COULEURS["UtilityVsCost"]
    ax1.errorbar(lams, [b[0] * 100 for b in bls], yerr=[b[1] * 100 for b in bls],
                 color=c, marker="o", markersize=6, linewidth=2, capsize=3)
    ax2.errorbar(lams, [u[0] for u in uts], yerr=[u[1] for u in uts],
                 color=c, marker="o", markersize=6, linewidth=2, capsize=3)
    style_axe(ax1, "Rejection rate", "λ (weight of the cost)", "rejected flows (%)")
    style_axe(ax2, "Utility obtained", "λ (weight of the cost)", "utility per second")
    fig.suptitle("UtilityVsCost: a bigger λ makes the policy more selective",
                 fontsize=13, x=0.01, ha="left")
    enregistrer(fig, "3_lambda.png")


def u_local(p, M=4):
    """Load balancer « local » : l'area j envoie vers le serveur j avec proba p, sinon ailleurs."""
    autre = (1 - p) / (M - 1)
    return [[p if i == j else autre for i in range(M)] for j in range(M)]


def exp_load_balancer():
    """Expérience 4 : routage uniforme contre routage local."""
    print("\n=== Effet du load balancer ===")
    routages = [("uniform", u_local(0.25)), ("local 70%", u_local(0.7)),
                ("local 100%", u_local(1.0))]
    noms = [n for n, _ in politiques()]
    res = {}
    for nom_r, u in routages:
        for nom in noms:
            bl, ut = repliquer(default_config(u=u), lambda nom=nom: dict(politiques())[nom])
            res[(nom_r, nom)] = (bl, ut)
            noter("load_balancer", nom_r, nom, bl, ut)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    largeur = 0.2
    for k, nom in enumerate(noms):
        xs = [i + (k - 1.5) * (largeur + 0.01) for i in range(len(routages))]
        bl = [res[(r, nom)][0] for r, _ in routages]
        ut = [res[(r, nom)][1] for r, _ in routages]
        ax1.bar(xs, [b[0] * 100 for b in bl], largeur, yerr=[b[1] * 100 for b in bl],
                color=COULEURS[nom], capsize=3, label=nom)
        ax2.bar(xs, [u[0] for u in ut], largeur, yerr=[u[1] for u in ut],
                color=COULEURS[nom], capsize=3, label=nom)
    for ax in (ax1, ax2):
        ax.set_xticks(range(len(routages)))
        ax.set_xticklabels([r for r, _ in routages])
    style_axe(ax1, "Rejection rate", "routing", "rejected flows (%)")
    style_axe(ax2, "Utility obtained", "routing", "utility per second")
    ax1.grid(False, axis="x")
    ax2.grid(False, axis="x")
    ax1.set_ylim(0, 100)
    ax1.legend(frameon=False, loc="upper left", ncol=2)
    fig.suptitle("Effect of the load balancer", fontsize=13, x=0.01, ha="left")
    enregistrer(fig, "4_load_balancer.png")


# ---------------------------------------------------------------- lancement
if __name__ == "__main__":
    print(f"Chaque point = moyenne de {R} réplications, ± = intervalle de confiance à 95 %")
    exp_charge()
    exp_capacite()
    exp_lambda()
    exp_load_balancer()

    os.makedirs(DOSSIER, exist_ok=True)
    with open(os.path.join(DOSSIER, "resultats.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["experiment", "x", "policy", "rejection_rate", "ci_rejection",
                    "utility_per_s", "ci_utility"])
        w.writerows(LIGNES_CSV)
    print(f"\nTous les chiffres sont dans {DOSSIER}/resultats.csv")