"""Composant 5 : Application et fonction d'utilité."""
import math


class Application:
    def __init__(self, name, servers, classes, M, alpha=3.0, beta=2.0, c=0.05):
        self.name = name
        self.servers = servers      # φd : serveurs où l'application est installée
        self.classes = classes      # classes j telles que χj(d) = 1
        self.M = M
        self.alpha, self.beta, self.c = alpha, beta, c

    def interested(self, j):
        """χj(d)."""
        return j in self.classes

    def w(self, j, all_servers):
        """w(j,d) : nb de flux de classe j traités par l'application dans tout le système."""
        return sum(all_servers[i].X[j] for i in self.servers)

    def r(self, w):
        """Utilité marginale r_d(w), non croissante en w (forme du Tableau II de l'article)."""
        return self.alpha * math.exp(-w * self.beta / self.M) + self.c