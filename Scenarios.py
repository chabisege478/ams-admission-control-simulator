"""Comparaison des politiques sur plusieurs scénarios de placement des applications.

Lancer avec :  python scenarios.py      (environ 3 minutes)

Méthode (pour une comparaison équitable) :
  1. RÉGLAGE   : pour chaque scénario et chaque politique, on teste plusieurs valeurs de son
                 paramètre (T, λ ou η) sur quelques graines, et on garde la meilleure.
  2. ÉVALUATION: avec ce meilleur réglage, on relance sur R_EVAL NOUVELLES graines.
                 Toutes les politiques voient exactement le même trafic (mêmes graines).
  3. COMPARAISON: on calcule la récompense moyenne et son intervalle de confiance à 95 %,
                 on désigne la meilleure politique, et on vérifie que son avance sur la
                 2e n'est pas due au hasard (test apparié sur les mêmes graines).

Résultats :
  figures/scenarios_runs.csv      toutes les récompenses stockées (1 ligne par simulation)
  figures/scenarios_summary.csv   le tableau final (moyenne, IC, meilleur réglage)
  figures/7_scenarios.png         le graphique de comparaison (en anglais)
"""
import csv
import os
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import default_config
from simulator import Simulator
from policies import AlwaysAccept, Threshold, UtilityVsCost, Efficiency

DOSSIER = "figures"
GRAINES_REGLAGE = [100, 101, 102]                 # graines pour choisir le paramètre
GRAINES_EVAL = list(range(2000, 2010))            # 10 AUTRES graines pour comparer
T_STUDENT = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447,
             8: 2.365, 9: 2.306, 10: 2.262}

# ---------------------------------------------------------------- les scénarios
# M = 4 zones et 4 serveurs. Seul le placement des applications change.
SCENARIOS = {
    "S1 Base": {
        "description": "configuration de départ : 3 applications, 1 ou 2 par serveur",
        "apps": {
            "A": {"servers": [0, 1, 3], "classes": [0, 1]},
            "B": {"servers": [0, 2],    "classes": [1, 2, 3]},
            "C": {"servers": [1],       "classes": [0, 3]},
        },
    },
    "S2 Specialized": {
        "description": "1 application par serveur, qui ne s'intéresse qu'à 2 zones",
        "apps": {
            "A": {"servers": [0], "classes": [0, 1]},
            "B": {"servers": [1], "classes": [1, 2]},
            "C": {"servers": [2], "classes": [2, 3]},
            "D": {"servers": [3], "classes": [3, 0]},
        },
    },
    "S3 Shared": {
        "description": "les 4 applications sur tous les serveurs (tout flux est utile)",
        "apps": {
            "A": {"servers": [0, 1, 2, 3], "classes": [0, 1]},
            "B": {"servers": [0, 1, 2, 3], "classes": [1, 2]},
            "C": {"servers": [0, 1, 2, 3], "classes": [2, 3]},
            "D": {"servers": [0, 1, 2, 3], "classes": [3, 0]},
        },
    },
    "S4 Unbalanced": {
        "description": "le serveur 0 héberge tout, les autres une seule application",
        "apps": {
            "A": {"servers": [0, 1, 2, 3], "classes": [0, 1]},
            "B": {"servers": [0],          "classes": [1, 2]},
            "C": {"servers": [0],          "classes": [2, 3]},
            "D": {"servers": [0],          "classes": [3, 0]},
        },
    },
}

# ---------------------------------------------------------------- les politiques et leurs réglages
# Chaque politique : (nom, fonction qui crée la politique, valeurs du paramètre à tester)
POLITIQUES = [
    ("AlwaysAccept",  lambda p: AlwaysAccept(),   [None]),
    ("Threshold",     lambda T: Threshold(T),     [2, 4, 6, 8, 10, 12, 15, 18]),
    ("UtilityVsCost", lambda l: UtilityVsCost(l), [0.5, 1, 2, 4, 8, 16, 32]),
    ("Efficiency",    lambda e: Efficiency(e),    [0.25, 0.5, 1, 2, 4]),
]
COULEURS = {"AlwaysAccept": "#2a78d6", "Threshold": "#eb6834",
            "UtilityVsCost": "#1baf7a", "Efficiency": "#eda100"}


# ---------------------------------------------------------------- outils
def simuler(apps, fabrique, param, graine):
    """Une simulation : retourne (récompense par seconde, taux de rejet)."""
    r = Simulator(default_config(apps=apps, seed=graine), fabrique(param)).run()
    return r["reward_per_s"], r["blocking"]


def ic95(xs):
    """Moyenne et demi-largeur de l'intervalle de confiance à 95 %."""
    m = statistics.mean(xs)
    return m, T_STUDENT.get(len(xs), 1.96) * statistics.stdev(xs) / len(xs) ** 0.5


def regler(apps, fabrique, valeurs):
    """Étape 1 : garde la valeur du paramètre qui donne la meilleure récompense moyenne."""
    if valeurs == [None]:
        return None
    score = {v: statistics.mean(simuler(apps, fabrique, v, g)[0] for g in GRAINES_REGLAGE)
             for v in valeurs}
    return max(score, key=score.get)


# ---------------------------------------------------------------- programme principal
def main():
    os.makedirs(DOSSIER, exist_ok=True)
    lignes_runs, resume = [], {}

    for nom_s, s in SCENARIOS.items():
        print(f"\n=== {nom_s} : {s['description']} ===")
        recompenses = {}                                   # politique -> liste des récompenses
        for nom_p, fabrique, valeurs in POLITIQUES:
            best = regler(s["apps"], fabrique, valeurs)                         # étape 1
            rec, rej = [], []
            for g in GRAINES_EVAL:                                              # étape 2
                rw, bl = simuler(s["apps"], fabrique, best, g)
                rec.append(rw)
                rej.append(bl)
                lignes_runs.append([nom_s, nom_p, best, g, f"{rw:.4f}", f"{bl:.4f}"])
            recompenses[nom_p] = rec
            m, h = ic95(rec)
            resume[(nom_s, nom_p)] = (best, m, h, statistics.mean(rej))
            reglage = "" if best is None else f"(meilleur paramètre = {best})"
            print(f"   {nom_p:14s} {reglage:28s} récompense = {m:5.2f} ± {h:.2f}"
                  f"   rejet = {statistics.mean(rej):5.1%}")

        # étape 3 : la meilleure, et est-ce que son avance sur la 2e est réelle ?
        classement = sorted(recompenses, key=lambda p: statistics.mean(recompenses[p]), reverse=True)
        p1, p2 = classement[0], classement[1]
        diff = [a - b for a, b in zip(recompenses[p1], recompenses[p2])]   # mêmes graines → apparié
        md, hd = ic95(diff)
        verdict = "écart significatif" if md - hd > 0 else "écart NON significatif (quasi ex aequo)"
        print(f"   → MEILLEURE : {p1}  (avance sur {p2} = {md:.2f} ± {hd:.2f} : {verdict})")
        resume[(nom_s, "_best")] = (p1, p2, md, hd, md - hd > 0)

    # ---- stockage des récompenses
    with open(os.path.join(DOSSIER, "scenarios_runs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["scenario", "policy", "best_parameter", "seed", "reward_per_s", "rejection_rate"])
        w.writerows(lignes_runs)
    with open(os.path.join(DOSSIER, "scenarios_summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["scenario", "policy", "best_parameter", "mean_reward", "ci95", "rejection_rate", "winner"])
        for nom_s in SCENARIOS:
            gagnant = resume[(nom_s, "_best")][0]
            for nom_p, _, _ in POLITIQUES:
                best, m, h, rej = resume[(nom_s, nom_p)]
                w.writerow([nom_s, nom_p, best, f"{m:.4f}", f"{h:.4f}", f"{rej:.4f}",
                            "yes" if nom_p == gagnant else ""])

    # ---- tableau final
    print("\n================ TABLEAU FINAL (récompense par seconde) ================")
    noms_p = [p for p, _, _ in POLITIQUES]
    print(f"{'Scénario':16s}" + "".join(f"{p:>16s}" for p in noms_p) + "   Meilleure")
    for nom_s in SCENARIOS:
        cases = "".join(f"{resume[(nom_s, p)][1]:16.2f}" for p in noms_p)
        p1, _, _, _, signif = resume[(nom_s, "_best")]
        print(f"{nom_s:16s}{cases}   {p1}{'' if signif else ' (ex aequo)'}")

    # ---- graphique (en anglais)
    fig, ax = plt.subplots(figsize=(11, 4.8))
    largeur = 0.2
    for k, nom_p in enumerate(noms_p):
        xs = [i + (k - 1.5) * (largeur + 0.01) for i in range(len(SCENARIOS))]
        ms = [resume[(s, nom_p)][1] for s in SCENARIOS]
        hs = [resume[(s, nom_p)][2] for s in SCENARIOS]
        ax.bar(xs, ms, largeur, yerr=hs, capsize=3, color=COULEURS[nom_p], label=nom_p)
    ax.set_xticks(range(len(SCENARIOS)))
    def etiquette(s):
        p1, p2, _, _, signif = resume[(s, "_best")]
        return f"{s}\n(best: {p1})" if signif else f"{s}\n(tie: {p1} / {p2})"
    ax.set_xticklabels([etiquette(s) for s in SCENARIOS])
    ax.set_ylabel("reward per second")
    ax.set_title("Reward of each policy in each scenario (best parameter of each policy)",
                 fontsize=13, loc="left")
    ax.grid(True, axis="y", color="#dddddd", linewidth=0.8)
    ax.set_axisbelow(True)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    fig.tight_layout()
    fig.savefig(os.path.join(DOSSIER, "7_scenarios.png"), dpi=150)
    plt.close(fig)
    print(f"\nGraphique : {DOSSIER}/7_scenarios.png")
    print(f"Récompenses stockées : {DOSSIER}/scenarios_runs.csv et {DOSSIER}/scenarios_summary.csv")


if __name__ == "__main__":
    main()