"""Composant 4 : Admission Control.

Toute politique hérite de AdmissionPolicy et implémente decide().
Le moteur impose de toute façon les contraintes ψi et θi.

Les 4 politiques du projet :
  1. AlwaysAccept  : référence (et validation du simulateur)
  2. Threshold     : critère « occupation du serveur » (baseline de l'article)
  3. UtilityVsCost : critères « utilité » + « charge du lien » (inspirée de l'éq. 9 de l'article)
  4. Efficiency    : utilité rapportée par Mb/s de bande passante consommée
"""


class AdmissionPolicy:
    name = "abstraite"

    def decide(self, flow, server, sim):
        """Retourne 1 pour admettre le flux, 0 pour le rejeter."""
        raise NotImplementedError


class AlwaysAccept(AdmissionPolicy):
    """Admet tant qu'il reste de la place."""
    name = "AlwaysAccept"

    def decide(self, flow, server, sim):
        return 1


class Threshold(AdmissionPolicy):
    """Admet si l'occupation Yi est sous un seuil T (baseline « naive » de l'article)."""
    def __init__(self, T):
        self.T = T
        self.name = f"Threshold(T={T})"

    def decide(self, flow, server, sim):
        return int(server.Y < self.T)


class UtilityVsCost(AdmissionPolicy):
    """Admet si l'utilité du flux dépasse λ x la charge du lien d'accès après admission."""
    def __init__(self, lam):
        self.lam = lam
        self.name = f"UtilityVsCost(λ={lam})"

    def decide(self, flow, server, sim):
        gain = sim.reward(flow, server)                        # ce que le flux rapporte
        cost = (server.bw + flow.bitrate) / server.theta       # part du lien occupée (0 à 1)
        return int(gain - self.lam * cost > 0)


class Efficiency(AdmissionPolicy):
    """Admet si l'efficience du flux (utilité rapportée par Mb/s consommé) atteint un seuil η."""
    def __init__(self, eta):
        self.eta = eta
        self.name = f"Efficiency(η={eta})"

    def decide(self, flow, server, sim):
        efficience = sim.reward(flow, server) / flow.bitrate   # utilité ÷ débit
        return int(efficience >= self.eta)