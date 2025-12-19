# Matematické funkce, především log pro exponenciální rozdělení
import math
# Efektivní oboustranná fronta (deque) – ideální pro FIFO fronty zákazníků (rychlé append a popleft)
from collections import deque
# Prioritní fronta (min-heap) pro řízení událostí podle času – zajišťuje, že vždy zpracujeme nejdřívější událost
from heapq import heappush, heappop


class RNG:
    """
    Pseudonáhodný generátor čísel pomocí lineárního kongruentního generátoru (LCG).
    Tento algoritmus je jednoduchý, rychlý a umožňuje plnou reprodukovatelnost výsledků díky pevnému seedu.
    Parametry (a, c, m) jsou zvoleny tak, aby měly dobré statistické vlastnosti.
    """

    def __init__(self, seed=42):
        # Počáteční hodnota (seed) – určuje celou sekvenci náhodných čísel
        self.state = seed
        # Multiplikátor – ovlivňuje periodu a kvalitu sekvence
        self.a = 1664525
        self.c = 1013904223                      # Inkrement – přidává se v každém kroku
        # Modulus – zajišťuje cyklickost (perioda až 2^32)
        self.m = 2**32

    def random(self):
        """
        Vrátí uniformní náhodné číslo z intervalu [0, 1).
        Algoritmus: X_{n+1} = (a * X_n + c) mod m, pak normalizace dělením modulem.
        """
        self.state = (self.a * self.state + self.c) % self.m
        return self.state / self.m


class Exponential:
    """
    Exponenciální rozdělení – nejběžnější model pro mezičasy příchodů nebo doby obsluhy v teorii front.
    Používá metodu inverzní transformace: pokud U ~ Uniform(0,1), pak X = -ln(1-U)/λ ~ Exp(λ).
    """

    def __init__(self, rate, rng, name=""):
        # Parametr λ (míra) – vyšší λ znamená kratší průměrné časy (průměr = 1/λ)
        self.rate = rate
        # Reference na RNG – zajišťuje konzistentní sekvenci
        self.rng = rng
        # Nepovinný název pro ladění (nepoužívá se v kódu)
        self.name = name

    def sample(self):
        """
        Vygeneruje jednu realizaci exponenciálního rozdělení.
        Pokud rate <= 0, vrací nekonečno (ochrana proti chybám).
        """
        if self.rate > 0:
            return -math.log(1 - self.rng.random()) / self.rate
        # Nekonečná doba – simulace se prakticky zastaví pro tento proces
        return float('inf')


class Constant:
    """
    Deterministické (konstantní) rozdělení – vždy vrací stejnou hodnotu.
    Užitečné pro testování, ladění nebo modelování deterministických systémů (např. D/M/1 fronta).
    """

    def __init__(self, value, rng, name=""):
        self.value = value                       # Pevná hodnota, kterou vždy vrací sample()
        # Reference na RNG (nepoužívá se, ale zachovává rozhraní)
        self.rng = rng
        self.name = name

    def sample(self):
        return self.value                        # Žádná náhoda – vždy přesně tato hodnota


class Event:
    """
    Základní jednotka diskrétně-událostní simulace.
    Každá událost má čas provedení, typ a libovolné další parametry (předané jako kwargs).
    """

    def __init__(self, time, typ, **kwargs):
        self.time = time                         # Simulační čas, kdy má událost nastat
        # Řetězec identifikující typ ('arrival', 'departure', 'renege')
        self.typ = typ
        # Přidá všechny kwargs jako atributy (např. node, cust_id)
        self.__dict__.update(kwargs)

    def __lt__(self, other):
        """
        Porovnání pro heapq – zajišťuje správné řazení událostí.
        Primárně podle času, sekundárně podle typu (aby při stejném čase měly přednost určité typy).
        """
        return (self.time, self.typ) < (other.time, other.typ)


class Customer:
    """
    Reprezentace jednoho zákazníka procházejícího systémem.
    Uchovává všechny důležité časové body pro výpočet statistik (čekací doba, doba v systému atd.).
    """

    def __init__(self, id, priority, arrival_time):
        self.id = id                             # Unikátní identifikátor zákazníka
        # Číslo priority (nižší = vyšší priorita)
        self.priority = priority
        self.arrival_time = arrival_time         # Čas příchodu do aktuálního uzlu
        # Čas zahájení obsluhy (pro výpočet čekací doby)
        self.service_start = None
        # Čas odchodu ze systému (konečný)
        self.departure = None
        self.renege_time = None                  # Čas případného odchodu bez obsluhy


class Server:
    """
    Jednotlivé obslužné místo (server) v uzlu.
    V této verzi podporuje pouze stavy IDLE/BUSY (poruchy nejsou implementovány v handle, ale struktura je připravena).
    """

    def __init__(self, id):
        self.id = id                             # Identifikátor serveru v rámci uzlu
        # Aktuální stav: IDLE, BUSY nebo DOWN (DOWN se nepoužívá v aktuálním kódu)
        self.state = "IDLE"
        self.customer = None                     # ID zákazníka, kterého právě obsluhuje


class Node:
    """
    Uzel (stanice/fronta) v síti – obsahuje více serverů, prioritní fronty a statistické integrály.
    Klíčová třída pro sběr statistik (průměrná délka fronty, využití serverů atd.).
    """

    def __init__(self, name, num_servers, priorities):
        self.name = name
        # Seznam všech serverů v uzlu
        self.servers = [Server(i) for i in range(num_servers)]
        # Slovník front podle priority
        self.queues = {p: deque() for p in priorities}
        # Integrál délky fronty přes čas (pro průměr)
        self.queue_integral = 0.0
        self.last_queue_time = 0.0
        # Kumulativní čas zaneprázdnění každého serveru
        self.busy_time = [0.0] * num_servers
        # Kumulativní čas poruchy (nepoužíváno v této verzi)
        self.down_time = [0.0] * num_servers
        self.last_server_time = [0.0] * num_servers
        # Počet dokončených obsluh
        self.completions = 0
        # Počet zákazníků, kteří odešli bez obsluhy
        self.reneges = 0
        # Seznam čekacích dob (pouze po warmup)
        self.waiting_times = []

    def queue_length(self):
        """Vrátí aktuální celkovou délku všech prioritních front."""
        return sum(len(q) for q in self.queues.values())

    def add(self, cust):
        """Přidá zákazníka do fronty odpovídající jeho prioritě."""
        self.queues[cust.priority].append(cust)

    def next_customer(self):
        """
        Vrátí zákazníka s nejvyšší prioritou (nejnižší číslo priority).
        Prochází priority od nejnižšího čísla (nejvyšší priorita).
        """
        for p in sorted(self.queues):
            if self.queues[p]:
                return self.queues[p].popleft()
        return None

    def idle_server(self):
        """Najde a vrátí první volný (IDLE) server, pokud existuje."""
        for s in self.servers:
            if s.state == "IDLE":
                return s
        return None

    def update_stats(self, t):
        """
        Aktualizuje časové integrály při každé změně stavu (před každou událostí).
        Používá metodu oblastí (area under curve) pro přesný výpočet průměrů.
        """
        dt = t - self.last_queue_time
        self.queue_integral += self.queue_length() * dt
        self.last_queue_time = t

        for i, s in enumerate(self.servers):
            dt_s = t - self.last_server_time[i]
            if s.state == "BUSY":
                self.busy_time[i] += dt_s
            elif s.state == "DOWN":
                # Pro budoucí rozšíření o poruchy
                self.down_time[i] += dt_s
            self.last_server_time[i] = t


class SimulationInput:
    """
    Kontejner pro všechny vstupní parametry simulace.
    Používá dynamické přidávání atributů přes __dict__.update pro jednoduchost.
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Simulator:
    """
    Hlavní třída diskrétně-událostní simulace.
    Řídí frontu událostí, zpracovává příchody, odchody a reneging.
    """

    def __init__(self, inp):
        self.inp = inp
        self.rng = RNG(inp.seed)                 # Vlastní RNG s daným seedem
        self.time = 0.0                          # Aktuální simulační čas
        self.events = []                         # Heap pro události
        self.nodes = {}                          # Slovník všech uzlů
        # Slovník všech zákazníků (pro přístup podle ID)
        self.customers = {}
        self.next_id = 0                         # Čítač pro unikátní ID zákazníků
        # Celkový počet zákazníků, kteří opustili systém po warmup
        self.departures = 0
        # Mapování cust_id → renege událost (pro zrušení při zahájení obsluhy)
        self.renege_events = {}

        # Vytvoření všech uzlů podle vstupu
        for n in inp.nodes:
            prio = inp.priorities.get(n, [0])
            self.nodes[n] = Node(n, inp.servers[n], prio)

    def schedule(self, ev):
        """Přidá událost do prioritní fronty."""
        heappush(self.events, ev)

    def schedule_arrival(self, node):
        """
        Naplánuje další příchod do uzlu (rekurzivně – po každém příchodu plánuje další).
        Pokud by další příchod byl po konci simulace, neplánuje se.
        """
        if node in self.inp.arrival_dists:
            t = self.time + self.inp.arrival_dists[node].sample()
            if t < self.inp.sim_time:
                prio = self.inp.priorities.get(node, [0])[0]
                ev = Event(t, "arrival", node=node,
                           cust_id=self.next_id, prio=prio)
                self.schedule(ev)
                self.next_id += 1

    def start_service(self, node_name, cust, server):
        """
        Zahájí obsluhu zákazníka na konkrétním serveru.
        Aktualizuje statistiky, nastaví stav serveru a plánuje departure událost.
        """
        node = self.nodes[node_name]
        node.update_stats(self.time)
        server.state = "BUSY"
        server.customer = cust.id
        cust.service_start = self.time
        # Zruší případnou plánovanou renege událost
        if cust.id in self.renege_events:
            del self.renege_events[cust.id]
        t_end = self.time + self.inp.service_dists[node_name].sample()
        self.schedule(Event(t_end, "departure", node=node_name,
                      cust_id=cust.id, server_id=server.id))

    def handle_arrival(self, ev):
        """Zpracování příchodu zákazníka do uzlu."""
        node = self.nodes[ev.node]
        cust = Customer(ev.cust_id, ev.prio, self.time)
        self.customers[ev.cust_id] = cust
        node.update_stats(self.time)

        server = node.idle_server()
        if server:
            # Okamžitě zahájí obsluhu
            self.start_service(ev.node, cust, server)
        else:
            # Přidá do fronty
            node.add(cust)
            # Pokud je definována trpělivost, plánuje renege
            if ev.node in self.inp.patience_dists and self.inp.patience_dists[ev.node]:
                t_renege = self.time + \
                    self.inp.patience_dists[ev.node].sample()
                r_ev = Event(t_renege, "renege",
                             node=ev.node, cust_id=ev.cust_id)
                self.schedule(r_ev)
                self.renege_events[ev.cust_id] = r_ev

        # Naplánuje další příchod do stejného uzlu
        self.schedule_arrival(ev.node)

    def handle_departure(self, ev):
        """
        Zpracování odchodu zákazníka z uzlu (dokončení obsluhy).
        Uvolní server, případně zahájí obsluhu dalšího zákazníka, zpracuje směrování.
        """
        node = self.nodes[ev.node]
        server = node.servers[ev.server_id]
        cust = self.customers[ev.cust_id]

        node.update_stats(self.time)
        node.completions += 1
        if self.time >= self.inp.warmup:
            node.waiting_times.append(cust.service_start - cust.arrival_time)

        server.state = "IDLE"
        server.customer = None
        node.update_stats(self.time)

        # Zahájí obsluhu dalšího zákazníka, pokud je ve frontě
        next_c = node.next_customer()
        if next_c:
            self.start_service(ev.node, next_c, server)

        # Probabilistické směrování do dalšího uzlu
        if ev.node in self.inp.routing_matrix:
            probs = self.inp.routing_matrix[ev.node]
            u = self.rng.random()
            cum = 0.0
            next_node = None
            for n, p in probs.items():
                cum += p
                if u <= cum:
                    next_node = n
                    break
            if next_node:
                # Zákazník okamžitě "přichází" do dalšího uzlu (čas zůstává stejný)
                prio = self.inp.priorities.get(next_node, [0])[0]
                arr_ev = Event(self.time, "arrival", node=next_node,
                               cust_id=ev.cust_id, prio=prio)
                self.schedule(arr_ev)
                return  # Neodchází ze systému

        # Zákazník opouští systém
        cust.departure = self.time
        if self.time >= self.inp.warmup:
            self.departures += 1

    def handle_renege(self, ev):
        """
        Zpracování odchodu zákazníka bez obsluhy (renege).
        Odstraní zákazníka z fronty, pokud tam stále je (jinak událost ignoruje).
        """
        if ev.cust_id not in self.renege_events:
            return  # Událost již byla zrušena (zákazník začal být obsluhován)
        node = self.nodes[ev.node]
        cust = self.customers[ev.cust_id]

        # Odstranění zákazníka ze správné fronty
        for q in node.queues.values():
            if cust in q:
                q.remove(cust)
                break

        node.update_stats(self.time)
        if self.time >= self.inp.warmup:
            node.reneges += 1
        del self.renege_events[ev.cust_id]

    def run(self):
        """Hlavní smyčka simulace – zpracovává události dokud nejsou vyčerpány nebo nepřekročí sim_time."""
        # Naplánuje první příchody do všech uzlů s externími příchody
        for n in self.inp.nodes:
            self.schedule_arrival(n)

        while self.events:
            ev = heappop(self.events)
            if ev.time > self.inp.sim_time:
                break
            self.time = ev.time

            if ev.typ == "arrival":
                self.handle_arrival(ev)
            elif ev.typ == "departure":
                self.handle_departure(ev)
            elif ev.typ == "renege":
                self.handle_renege(ev)

        # Finální aktualizace statistik na konci simulace
        for node in self.nodes.values():
            node.update_stats(self.time)

    def get_results(self):
        """
        Shromáždí a vrátí všechny klíčové statistiky simulace.
        Používá anonymní třídu pro jednoduchý objekt s atributy.
        """
        eff = self.inp.sim_time - \
            self.inp.warmup  # Efektivní čas měření (bez warmup)
        res = {"throughput": self.departures / eff if eff > 0 else 0.0}

        for n, node in self.nodes.items():
            # Průměrná délka fronty (přes celou simulaci, včetně warmup – běžná praxe)
            res.setdefault("mean_queue_length", {})[
                n] = node.queue_integral / self.inp.sim_time
            # Využití serverů (busy time / celkový dostupný čas)
            res.setdefault("server_utilization", {})[n] = sum(
                node.busy_time) / (len(node.servers) * self.inp.sim_time)
            res.setdefault("service_completions", {})[n] = node.completions
            # Pravděpodobnost renege
            total_served_or_reneged = node.completions + node.reneges
            res.setdefault("reneging_prob", {})[
                n] = node.reneges / total_served_or_reneged if total_served_or_reneged > 0 else 0.0
            # Průměrná čekací doba (pouze po warmup)
            res.setdefault("waiting_time_mean", {})[n] = sum(
                node.waiting_times) / len(node.waiting_times) if node.waiting_times else 0.0

        # Placeholder – reálný CI se počítá při batch simulacích
        res["throughput_ci"] = (0.0, 0.0)
        return type('Result', (), res)()


def simulate(inp):
    """
    Veřejná funkce pro spuštění simulace.
    Podporuje více nezávislých běhů (batches) pro odhad intervalu spolehlivosti propustnosti.
    """
    if inp.batch_count == 1:
        s = Simulator(inp)
        s.run()
        return s.get_results()

    # Více batchů – každý s jiným seedem pro nezávislost
    thru = []
    for b in range(inp.batch_count):
        # Hluboká kopie (dostatečná pro immutable hodnoty)
        new_inp = SimulationInput(**inp.__dict__)
        new_inp.seed = inp.seed + b * 1000         # Odlišný seed pro každý batch
        new_inp.batch_count = 1
        s = Simulator(new_inp)
        s.run()
        thru.append(s.get_results().throughput)

    mean = sum(thru) / len(thru)
    if len(thru) > 1:
        var = sum((x - mean)**2 for x in thru) / (len(thru) - 1)
        err = math.sqrt(var / len(thru))
        # Přibližný 95% CI (t-distribuce pro malé vzorky by byla přesnější)
        margin = 2 * err
        ci = (mean - margin, mean + margin)
    else:
        ci = (mean, mean)

    # Vrátí výsledky posledního běhu, ale s agregovanou propustností a CI
    res = s.get_results()
    res.throughput = mean
    res.throughput_ci = ci
    return res
