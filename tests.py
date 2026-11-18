"""Tests du simulateur. Lancer avec :  python tests.py

Chaque test compare le simulateur à une valeur connue (théorie ou règle évidente).
"""
from config import default_config
from simulator import Simulator
from policies import AlwaysAccept, Threshold, UtilityVsCost, Efficiency
from application import Application

INF = float("inf")


# --------------------------------------------------------------- formules théoriques
def erlang_b(c, a):
    """Probabilité de blocage d'un système à c places avec une charge a = ζ/μ."""
    B = 1.0
    for k in range(1, c + 1):
        B = a * B / (k + a * B)
    return B


def kaufman_roberts(C, loads, sizes):
    """Blocage par classe d'un lien de capacité C partagé par des flux de débits différents."""
    q = [0.0] * (C + 1)
    q[0] = 1.0
    for n in range(1, C + 1):
        q[n] = sum(a * b * q[n - b] for a, b in zip(loads, sizes) if n - b >= 0) / n
    total = sum(q)
    q = [x / total for x in q]
    return [sum(q[C - b + 1:]) for b in sizes]


def one_server_config(zeta, mu, psi, theta, bitrate=1.0, **extra):
    """1 area, 1 serveur, pas d'applications : un système à pertes classique."""
    return default_config(M=1, zeta=[zeta], mu=[mu], bitrate=[bitrate], psi=[psi],
                          theta=[theta], u=[[1.0]], apps={},
                          horizon=20000.0, warmup=1000.0, **extra)


# --------------------------------------------------------------- les tests
def test_conservation():
    """Chaque flux arrivé est soit admis, soit rejeté."""
    r = Simulator(default_config(), AlwaysAccept()).run()
    ok = all(a == acc + rej for a, acc, rej in zip(r["arrivals"], r["accepted"], r["rejected"]))
    return ok, f"arrivés={sum(r['arrivals'])}, admis={sum(r['accepted'])}, rejetés={sum(r['rejected'])}"


def test_capacites_respectees():
    """Yi ne dépasse jamais ψi et la bande ne dépasse jamais θi."""
    c = default_config()
    r = Simulator(c, AlwaysAccept()).run()
    ok = all(y <= p for y, p in zip(r["max_Y"], c["psi"])) and \
         all(b <= t + 1e-9 for b, t in zip(r["max_bw"], c["theta"]))
    return ok, f"max Y={r['max_Y']} (ψ={c['psi']}), max bande={r['max_bw']} (θ={c['theta']})"


def test_mm_infini():
    """Sans limite de capacité, le nb moyen de flux actifs de classe j vaut ζj/μj."""
    c = default_config(psi=[10**9] * 4, theta=[INF] * 4, horizon=20000.0, warmup=1000.0)
    r = Simulator(c, AlwaysAccept()).run()
    theorie = [z / m for z, m in zip(c["zeta"], c["mu"])]
    ok = all(abs(s - t) / t < 0.05 for s, t in zip(r["mean_X_class"], theorie))
    sim = [round(x, 2) for x in r["mean_X_class"]]
    return ok, f"simulé={sim}, théorie={theorie}"


def test_erlang_b():
    """1 serveur, ψ=10, ζ=8, μ=1 : le blocage doit suivre la formule d'Erlang B."""
    r = Simulator(one_server_config(8.0, 1.0, psi=10, theta=INF), AlwaysAccept()).run()
    th = erlang_b(10, 8.0)
    return abs(r["blocking"] - th) < 0.01, f"simulé={r['blocking']:.4f}, Erlang B={th:.4f}"


def test_insensibilite():
    """Même test avec des durées lognormales de même moyenne : le blocage ne change pas."""
    c = one_server_config(8.0, 1.0, psi=10, theta=INF, duration_law="lognormal", sigma=1.0)
    r = Simulator(c, AlwaysAccept()).run()
    th = erlang_b(10, 8.0)
    return abs(r["blocking"] - th) < 0.01, f"simulé (lognormale)={r['blocking']:.4f}, Erlang B={th:.4f}"


def test_kaufman_roberts():
    """2 classes de débits 1 et 2 Mb/s sur un lien θ=20 : comparer à Kaufman-Roberts."""
    c = default_config(M=2, zeta=[8.0, 4.0], mu=[1.0, 1.0], bitrate=[1.0, 2.0],
                       psi=[10**9], theta=[20.0], u=[[1.0], [1.0]], apps={},
                       horizon=20000.0, warmup=1000.0)
    r = Simulator(c, AlwaysAccept()).run()
    th = kaufman_roberts(20, [8.0, 4.0], [1, 2])
    ok = all(abs(s - t) < 0.01 for s, t in zip(r["blocking_per_class"], th))
    sim = [round(x, 4) for x in r["blocking_per_class"]]
    return ok, f"simulé={sim}, théorie={[round(x, 4) for x in th]}"


def test_load_balancer():
    """Les flux sont répartis entre serveurs selon les probabilités u."""
    u = [0.5, 0.3, 0.2]
    c = default_config(M=1, zeta=[5.0], mu=[1.0], bitrate=[1.0], psi=[10**9] * 3,
                       theta=[INF] * 3, u=[u], apps={}, horizon=10000.0, warmup=0.0)
    r = Simulator(c, AlwaysAccept()).run()
    frac = [x / sum(r["routed"]) for x in r["routed"]]
    ok = all(abs(f - p) < 0.01 for f, p in zip(frac, u))
    return ok, f"répartition={[round(f, 3) for f in frac]}, attendu={u}"


def test_seuil():
    """Avec la politique Threshold(T), l'occupation ne dépasse jamais T."""
    r = Simulator(default_config(), Threshold(12)).run()
    return all(y <= 12 for y in r["max_Y"]), f"max Y={r['max_Y']} (T=12)"


def test_utilite_decroissante():
    """r_d(w) ne doit jamais augmenter quand w augmente."""
    app = Application("A", [0], [0], M=4)
    vals = [app.r(w) for w in range(50)]
    ok = all(a >= b for a, b in zip(vals, vals[1:]))
    return ok, f"r(0)={vals[0]:.3f}, r(5)={vals[5]:.3f}, r(20)={vals[20]:.3f}"


def test_reproductible():
    """Même graine : mêmes résultats. Graine différente : résultats différents."""
    r1 = Simulator(default_config(seed=1), UtilityVsCost(1.0)).run()
    r2 = Simulator(default_config(seed=1), UtilityVsCost(1.0)).run()
    r3 = Simulator(default_config(seed=2), UtilityVsCost(1.0)).run()
    return r1 == r2 and r1 != r3, "graine 1 = graine 1, graine 1 ≠ graine 2"


def test_quatre_politiques():
    """Les 4 politiques : conservation des flux et capacités ψ, θ toujours respectées."""
    c = default_config()
    noms = []
    for p in [AlwaysAccept(), Threshold(15), UtilityVsCost(1.0), Efficiency(0.5)]:
        r = Simulator(c, p).run()
        ok = all(a == acc + rej for a, acc, rej in zip(r["arrivals"], r["accepted"], r["rejected"])) \
             and all(y <= ps for y, ps in zip(r["max_Y"], c["psi"])) \
             and all(b <= t + 1e-9 for b, t in zip(r["max_bw"], c["theta"]))
        if not ok:
            return False, f"problème avec {p.name}"
        noms.append(p.name)
    return True, "OK pour " + ", ".join(noms)


TESTS = [test_conservation, test_capacites_respectees, test_mm_infini, test_erlang_b,
         test_insensibilite, test_kaufman_roberts, test_load_balancer, test_seuil,
         test_utilite_decroissante, test_reproductible, test_quatre_politiques]

if __name__ == "__main__":
    nb_ok = 0
    for t in TESTS:
        ok, msg = t()
        nb_ok += ok
        print(f"[{'OK ' if ok else 'ÉCHEC'}] {t.__name__:28s} {msg}")
    print(f"\n{nb_ok}/{len(TESTS)} tests réussis")