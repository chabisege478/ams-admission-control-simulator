"""Composant 2 : Area Load Balancer."""


class LoadBalancer:
    def __init__(self, u_j, rng):
        self.u_j = u_j              # u_j[i] = proba d'envoyer un flux de l'area j vers le serveur i
        self.rng = rng
        self.targets = list(range(len(u_j)))

    def route(self, flow):
        return self.rng.choices(self.targets, weights=self.u_j)[0]