"""Composant 1 : Area Traffic Generator."""
import math


class Flow:
    """Un flux : sa classe j (= son area d'origine), sa durée et son débit."""
    def __init__(self, j, arrival, duration, bitrate):
        self.j = j
        self.arrival = arrival
        self.duration = duration
        self.bitrate = bitrate
        self.server = None          # serveur qui l'héberge, s'il est admis


class TrafficGenerator:
    def __init__(self, zeta, mu, bitrate, rng, duration_law="exp", sigma=1.0):
        self.zeta, self.mu, self.bitrate, self.rng = zeta, mu, bitrate, rng
        self.duration_law, self.sigma = duration_law, sigma

    def next_interarrival(self, j):
        """Temps jusqu'à la prochaine arrivée dans l'area j : exponentielle de taux ζj."""
        return self.rng.expovariate(self.zeta[j])

    def _duration(self, j):
        mean = 1.0 / self.mu[j]
        if self.duration_law == "exp":
            return self.rng.expovariate(self.mu[j])
        if self.duration_law == "lognormal":
            # lognormale de même moyenne 1/μj
            m = math.log(mean) - self.sigma ** 2 / 2
            return self.rng.lognormvariate(m, self.sigma)
        raise ValueError(f"loi inconnue : {self.duration_law}")

    def new_flow(self, j, t):
        return Flow(j, t, self._duration(j), self.bitrate[j])