"""Exemple d'utilisation : compare les 4 politiques sur le scénario par défaut.
Lancer avec :  python main.py
"""
from config import default_config
from simulator import Simulator
from policies import AlwaysAccept, Threshold, UtilityVsCost, Efficiency

policies = [AlwaysAccept(), Threshold(15), UtilityVsCost(1.0), Efficiency(0.5)]

print(f"{'Politique':24s} {'Blocage':>8s} {'Utilité/s':>10s}  Occupation moyenne Yi   Bande moyenne (Mb/s)")
for p in policies:
    r = Simulator(default_config(), p).run()
    Y = " ".join(f"{y:5.1f}" for y in r["mean_Y"])
    bw = " ".join(f"{b:5.1f}" for b in r["mean_bw"])
    print(f"{r['policy']:24s} {r['blocking']:8.1%} {r['reward_per_s']:10.2f}  {Y}   {bw}")