"""Figure en pourcentage : le taux d'acceptation (acceptance rate) de chaque stratégie.

À lancer APRÈS  python scenarios.py  (il réutilise les résultats stockés, il ne simule rien) :
    python percentage.py

Calcul (pour chaque stratégie) :
    acceptance rate = flux acceptés / flux arrivés x 100  =  100 % - taux de rejet
    - par scénario : moyenne sur les 10 simulations du scénario
    - global       : moyenne sur toutes les simulations des 4 scénarios
L'intervalle de confiance vient des 10 graines (pour chaque graine : moyenne sur les 4 scénarios).

Résultats :
    figures/percentage.csv     le taux d'acceptation par scénario et global
    figures/8_percentage.png   la figure (en anglais)
"""
import csv
import os
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DOSSIER = "figures"
STRATEGIES = [("UtilityVsCost", "Utility"), ("Efficiency", "Efficiency")]   # (nom dans le CSV, nom affiché)
COULEURS = {"UtilityVsCost": "#1baf7a", "Efficiency": "#eda100"}
T_STUDENT = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447,
             8: 2.365, 9: 2.306, 10: 2.262}


def lire(nom):
    chemin = os.path.join(DOSSIER, nom)
    if not os.path.exists(chemin):
        sys.exit(f"Fichier {chemin} introuvable : lancez d'abord  python scenarios.py")
    with open(chemin, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main():
    runs = lire("scenarios_runs.csv")
    scenarios = list(dict.fromkeys(r["scenario"] for r in runs))
    graines = sorted({r["seed"] for r in runs})
    # taux d'acceptation (en %) de chaque simulation
    acc = {(r["scenario"], r["policy"], r["seed"]): 100 * (1 - float(r["rejection_rate"])) for r in runs}
    rec = {(r["scenario"], r["policy"], r["seed"]): float(r["reward_per_s"]) for r in runs}

    lignes, valeurs = [], {}
    print(f"{'Strategy':12s}" + "".join(f"{s:>16s}" for s in scenarios) + "      ALL scenarios")
    for nom, affiche in STRATEGIES:
        par_scen = [statistics.mean(acc[(s, nom, g)] for g in graines) for s in scenarios]
        par_graine = [statistics.mean(acc[(s, nom, g)] for s in scenarios) for g in graines]
        glob = statistics.mean(par_graine)
        ic = T_STUDENT.get(len(par_graine), 1.96) * statistics.stdev(par_graine) / len(par_graine) ** 0.5
        recompense = statistics.mean(rec[(s, nom, g)] for s in scenarios for g in graines)
        valeurs[nom] = (glob, ic, recompense)
        print(f"{affiche:12s}" + "".join(f"{v:15.1f}%" for v in par_scen) + f"   {glob:6.1f} % ± {ic:.1f}"
              f"   (reward/s moyen = {recompense:.2f})")
        for s, v in zip(scenarios, par_scen):
            lignes.append([affiche, s, f"{v:.2f}", ""])
        lignes.append([affiche, "ALL", f"{glob:.2f}", f"{ic:.2f}"])

    os.makedirs(DOSSIER, exist_ok=True)
    with open(os.path.join(DOSSIER, "percentage.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["strategy", "scenario", "acceptance_rate_percent", "ci95"])
        w.writerows(lignes)

    # ---- figure (en anglais), dans l'esprit du schéma du prof
    fig, ax = plt.subplots(figsize=(6.5, 5))
    xs = range(len(STRATEGIES))
    for x, (nom, affiche) in zip(xs, STRATEGIES):
        pct, ic, _ = valeurs[nom]
        ax.bar(x, pct, 0.55, yerr=ic, capsize=4, color=COULEURS[nom])
        ax.text(x, pct + ic + 1.5, f"{pct:.1f} %", ha="center", va="bottom", fontsize=12)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([a for _, a in STRATEGIES], fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Acceptance rate (%)")
    ax.set_title("Acceptance rate of each strategy over all scenarios\n"
                 "(accepted flows / arrived flows)", fontsize=12, loc="left")
    ax.grid(True, axis="y", color="#dddddd", linewidth=0.8)
    ax.set_axisbelow(True)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    fig.tight_layout()

    chemin = os.path.join(DOSSIER, "8_percentage.png")
    try:
        fig.savefig(chemin, dpi=150)
    except OSError:                    # image bloquée par un autre programme (Windows)
        try:
            os.remove(chemin)
            fig.savefig(chemin, dpi=150)
        except OSError:
            chemin = os.path.join(DOSSIER, "8_percentage_new.png")
            fig.savefig(chemin, dpi=150)
            print("! l'image d'origine est ouverte dans un autre programme : fermez-la")
    plt.close(fig)
    print(f"\nGraphique : {chemin}")
    print(f"Tableau   : {DOSSIER}/percentage.csv")


if __name__ == "__main__":
    main()