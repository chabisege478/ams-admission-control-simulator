"""Composant 3 : Server."""


class Server:
    def __init__(self, i, psi, theta, M):
        self.i = i
        self.psi = psi              # ψi : nb max de flux actifs
        self.theta = theta          # θi : bande passante d'accès max
        self.X = [0] * M            # X[j] = nb de flux de classe j actifs sur ce serveur
        self.bw = 0.0               # bande passante utilisée

    @property
    def Y(self):
        """Occupation totale Yi = somme des Xij."""
        return sum(self.X)

    def has_room(self, flow):
        """Les deux contraintes de l'énoncé : calcul (ψi) et accès (θi)."""
        return self.Y < self.psi and self.bw + flow.bitrate <= self.theta + 1e-9

    def add(self, flow):
        self.X[flow.j] += 1
        self.bw += flow.bitrate
        flow.server = self.i

    def remove(self, flow):
        self.X[flow.j] -= 1
        self.bw -= flow.bitrate