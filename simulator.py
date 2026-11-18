"""Moteur à événements discrets : relie les 5 composants et collecte les mesures."""
import heapq
import itertools
import random

from traffic import TrafficGenerator
from balancer import LoadBalancer
from server import Server
from application import Application


class Simulator:
    def __init__(self, config, policy):
        c = config
        self.M = c["M"]
        self.N = len(c["psi"])                       # nombre de serveurs
        self.horizon, self.warmup = c["horizon"], c["warmup"]
        self.rng = random.Random(c["seed"])
        self.policy = policy

        # --- les composants ---
        self.traffic = TrafficGenerator(c["zeta"], c["mu"], c["bitrate"], self.rng,
                                        c.get("duration_law", "exp"), c.get("sigma", 1.0))
        self.balancers = [LoadBalancer(c["u"][j], self.rng) for j in range(self.M)]
        self.servers = [Server(i, c["psi"][i], c["theta"][i], self.M) for i in range(self.N)]
        self.apps = [Application(name, a["servers"], a["classes"], self.M, **a.get("utility", {}))
                     for name, a in c.get("apps", {}).items()]

        # --- échéancier ---
        self.t = 0.0
        self.queue = []
        self.counter = itertools.count()

        # --- mesures ---
        self.arrivals = [0] * self.M
        self.accepted = [0] * self.M
        self.rejected = [0] * self.M
        self.routed = [0] * self.N
        self.total_reward = 0.0
        self.area_Y = [0.0] * self.N      # intégrale de Yi dans le temps
        self.area_bw = [0.0] * self.N     # intégrale de la bande utilisée
        self.area_X = [0.0] * self.M      # intégrale du nb de flux actifs de classe j
        self.max_Y = [0] * self.N
        self.max_bw = [0.0] * self.N
        self._last_t = 0.0

    # ------------------------------------------------------------------
    def schedule(self, time, kind, data):
        heapq.heappush(self.queue, (time, next(self.counter), kind, data))

    def _accumulate(self, new_t):
        """Ajoute l'état courant x durée écoulée (moyennes temporelles), hors warm-up."""
        start = max(self._last_t, self.warmup)
        if new_t > start:
            dt = new_t - start
            for s in self.servers:
                self.area_Y[s.i] += s.Y * dt
                self.area_bw[s.i] += s.bw * dt
                for j in range(self.M):
                    self.area_X[j] += s.X[j] * dt
        self._last_t = new_t

    def reward(self, flow, server):
        """Récompense de l'éq. (3) : somme des r_d(w) des applis de ce serveur intéressées par j."""
        return sum(app.r(app.w(flow.j, self.servers))
                   for app in self.apps
                   if server.i in app.servers and app.interested(flow.j))

    # ------------------------------------------------------------------
    def on_arrival(self, j):
        flow = self.traffic.new_flow(j, self.t)
        i = self.balancers[j].route(flow)
        server = self.servers[i]
        measuring = self.t >= self.warmup
        if measuring:
            self.arrivals[j] += 1
            self.routed[i] += 1

        if server.has_room(flow) and self.policy.decide(flow, server, self) == 1:
            r = self.reward(flow, server)          # calculée AVANT d'ajouter le flux
            server.add(flow)
            self.schedule(self.t + flow.duration, "DEPARTURE", flow)
            if measuring:
                self.accepted[j] += 1
                self.total_reward += r
            self.max_Y[i] = max(self.max_Y[i], server.Y)
            self.max_bw[i] = max(self.max_bw[i], server.bw)
        elif measuring:
            self.rejected[j] += 1

        self.schedule(self.t + self.traffic.next_interarrival(j), "ARRIVAL", j)

    def on_departure(self, flow):
        self.servers[flow.server].remove(flow)

    # ------------------------------------------------------------------
    def run(self):
        for j in range(self.M):
            self.schedule(self.traffic.next_interarrival(j), "ARRIVAL", j)
        while self.queue:
            time, _, kind, data = heapq.heappop(self.queue)
            if time > self.horizon:
                break
            self._accumulate(time)
            self.t = time
            if kind == "ARRIVAL":
                self.on_arrival(data)
            else:
                self.on_departure(data)
        self._accumulate(self.horizon)
        return self.results()

    def results(self):
        T = self.horizon - self.warmup
        total_arr = sum(self.arrivals)
        return {
            "policy": self.policy.name,
            "arrivals": list(self.arrivals),
            "accepted": list(self.accepted),
            "rejected": list(self.rejected),
            "blocking_per_class": [r / a if a else 0.0 for r, a in zip(self.rejected, self.arrivals)],
            "blocking": sum(self.rejected) / total_arr if total_arr else 0.0,
            "mean_Y": [a / T for a in self.area_Y],
            "mean_bw": [a / T for a in self.area_bw],
            "mean_X_class": [a / T for a in self.area_X],
            "max_Y": list(self.max_Y),
            "max_bw": list(self.max_bw),
            "routed": list(self.routed),
            "reward_per_s": self.total_reward / T,
        }