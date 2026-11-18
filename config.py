"""Paramètres du simulateur (notations de Fox et al., Section II)."""
import copy

DEFAULT = {
    "M": 4,                                # nombre d'areas = nombre de classes
    "zeta":    [3.0, 2.5, 3.5, 2.0],       # ζj : taux d'arrivée des flux de l'area j (flux/s) area flow arrival rate
    "mu":      [0.2, 0.1, 0.25, 0.5],      # μj : durée moyenne d'un flux = 1/μj → 5 s, 10 s, 4 s, 2 s
    "bitrate": [1.0, 2.0, 5.0, 1.0],       # débit d'un flux de classe j (Mb/s)
    "duration_law": "exp",                 # "exp" ou "lognormal" (loi générale)
    "sigma": 1.0,                          # écart-type du log si loi lognormale
     "psi":   [20, 25, 30, 15],           # ψi : nb max de flux actifs sur le serveur i
       "theta": [40.0, 50.0, 60.0, 30.0], # θi : capacité d'accès du serveur i (Mb/s)
    # u[j][i] = probabilité que le load balancer de l'area j envoie vers le serveur i
    "u": [[0.25, 0.25, 0.25, 0.25] for _ in range(4)],
    # Applications : serveurs φd où elles sont installées, classes χ(d) qui les intéressent
    "apps": {
        "A": {"servers": [0, 1, 3], "classes": [0, 1]},
        "B": {"servers": [0, 2],    "classes": [1, 2, 3]},
        "C": {"servers": [1],       "classes": [0, 3]},
    },
    "horizon": 5000.0,                     # durée simulée (s)
    "warmup": 500.0,                       # début ignoré dans les mesures (s)
    "seed": 42,
}


def default_config(**overrides):
    """Copie de la config par défaut, avec des paramètres modifiés si besoin."""
    c = copy.deepcopy(DEFAULT)
    c.update(overrides)
    return c