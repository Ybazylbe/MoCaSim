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
        self.c = 1013904223
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

    def random(self):
        """
        Vygeneruje jednu realizaci exponenciálního rozdělení.
        Pokud rate <= 0, vrací nekonečno (ochrana proti chybám).
        """
        if self.rate > 0:
            u = self.rng.random()
            return -math.log(1 - u) / self.rate
        # Nekonečná doba – simulace se prakticky zastaví pro tento proces
        return float('inf')


class Constant:
    """
    Deterministické (konstantní) rozdělení – vždy vrací stejnou hodnotu.
    Užitečné pro testování, ladění nebo modelování deterministických systémů (např. D/M/1 fronta).
    Každé volání random() konzumuje jeden výběr z RNG, aby se udržela konzistence
    společné sekvence při sdílení jednoho generátoru s ostatními rozděleními.
    """

    def __init__(self, value, rng, name=""):
        self.value = value
        # Reference na RNG – konzumován při každém random() pro sync sekvence
        self.rng = rng
        self.name = name

    def random(self):
        # Konzumujeme jeden výběr z RNG, aby sdílený generátor
        # postupoval stejně bez ohledu na typ rozdělení v proudu
        self.rng.random()
        return self.value


class Event:
    """
    Základní jednotka diskrétně-událostní simulace.
    Každá událost má čas provedení, typ a libovolné další parametry (předané jako kwargs).
    """

    # Explicitní prioritní řád pro vyřazování při stejném čase.
    # Nižší číslo = vyšší priorita zpracování.
    # Správný řád: nejprve departure (uvolní server), pak routing (směrování),
    # pak renege (kontrola zrušení), pak repair (server back online),
    # nakonec arrival (nový zákazník) a breakdown (porucha).
    _TYPE_PRIORITY = {
        "departure": 0,
        "routing":   1,
        "renege":    2,
        "repair":    3,
        "arrival":   4,
        "breakdown": 5,
    }

    def __init__(self, time, typ, **kwargs):
        self.time = time
        # Řetězec identifikující typ ('arrival', 'departure', 'renege', 'breakdown', 'repair', 'routing')
        self.typ = typ
        # Přidá všechny kwargs jako atributy (např. node, cust_id)
        self.__dict__.update(kwargs)

    def __lt__(self, other):
        """
        Porovnání pro heapq – zajišťuje správné řazení událostí.
        Primárně podle času, sekundárně podle explicitní prioritní mapy typů,
        aby při stejném čase byly zpracovány v správném pořadí.
        """
        return (self.time, self._TYPE_PRIORITY.get(self.typ, 99)) < \
               (other.time, other._TYPE_PRIORITY.get(other.typ, 99))


class Customer:
    """
    Reprezentace jednoho zákazníka procházejícího systémem.
    Uchovává všechny důležité časové body pro výpočet statistik (čekací doba, doba v systému atd.).
    """

    def __init__(self, id, priority, arrival_time):
        self.id = id
        # Číslo priority (nižší = vyšší priorita)
        self.priority = priority
        self.arrival_time = arrival_time
        # Čas zahájení obsluhy (pro výpočet čekací doby)
        self.service_start = None
        # Čas odchodu ze systému (konečný)
        self.departure = None
        self.renege_time = None


class Server:
    """
    Jednotlivé obslužné místo (server) v uzlu.
    Podporuje stavy IDLE/BUSY/DOWN pro modelování poruch.
    """

    def __init__(self, id):
        self.id = id
        # Aktuální stav: IDLE, BUSY nebo DOWN
        self.state = "IDLE"
        self.customer = None


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
        # Integrál délky fronty přes čas – akumuluje se POUZE po warmup
        self.queue_integral = 0.0
        self.last_queue_time = 0.0
        # Kumulativní čas zaneprázdnění každého serveru – POUZE po warmup
        self.busy_time = [0.0] * num_servers
        # Kumulativní čas poruchy – POUZE po warmup
        self.down_time = [0.0] * num_servers
        self.last_server_time = [0.0] * num_servers
        # Celkový počet dokončených obsluh (od začátku, pro ladění)
        self.completions = 0
        # Počet dokončených obsluh po warmup (pro konzistentní metriky)
        self.completions_post_warmup = 0
        # Počet zákazníků, kteří odešli bez obsluhy (po warmup)
        self.reneges = 0
        # Seznam čekacích dob (pouze po warmup)
        self.waiting_times = []
        # Seznam dob v systému (pouze po warmup)
        self.system_times = []
        # Vlaj: zda warmup proběhl (nastaveno Simulatorom)
        self._warmup_done = False

    def queue_length(self):
        """Vrátí aktuální celkovou délku všech prioritních front."""
        return sum(len(q) for q in self.queues.values())

    def add(self, cust):
        """Přidá zákazníka do fronty odpovídající jeho prioritě."""
        self.queues[cust.priority].append(cust)

    def next_customer(self):
        """
        Vrátí zákazníka s nejvyšší prioritou (nejnížší číslo priority).
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

    def reset_stats_at_warmup(self, t):
        """
        Reset statistických integrálů v okamžiku warmup.
        Po tomto bodě se queue_integral, busy_time a down_time akumulují
        pouze přes efektivní (post-warmup) periodu simulace.
        """
        # Nejprve aktualizujeme integrály do bodu warmup (aby last_*_time bylo správné)
        # ale pak vyresetujeme akumulátory na nulu
        self.queue_integral = 0.0
        self.last_queue_time = t

        for i in range(len(self.servers)):
            self.busy_time[i] = 0.0
            self.down_time[i] = 0.0
            self.last_server_time[i] = t

        self._warmup_done = True

    def update_stats(self, t):
        """
        Aktualizuje časové integrály při každé změně stavu (před každou událostí).
        Používá metodu oblastí (area under curve) pro přesný výpočet průměrů.
        Akumulace probíhá pouze po warmup (zajištěno reset_stats_at_warmup).
        """
        dt = t - self.last_queue_time
        if self._warmup_done:
            self.queue_integral += self.queue_length() * dt
        self.last_queue_time = t

        for i, s in enumerate(self.servers):
            dt_s = t - self.last_server_time[i]
            if self._warmup_done:
                if s.state == "BUSY":
                    self.busy_time[i] += dt_s
                elif s.state == "DOWN":
                    self.down_time[i] += dt_s
            self.last_server_time[i] = t


class SimulationResults:
    """
    Objekt výsledků simulace se všemi klíčovými metrikami.
    Všechny atributy jsou definované v __init__ s výchozími hodnotami.
    """

    def __init__(self):
        # Celková propustnost systému (zákazníci/čas)
        self.throughput = 0.0
        # Interval spolehlivosti propustnosti (dolní, horní)
        self.throughput_ci = (0.0, 0.0)
        # Průměrná délka fronty pro každý uzel {node_name: float}
        self.mean_queue_length = {}
        # Využití serverů pro každý uzel {node_name: float}
        self.server_utilization = {}
        # Počet dokončených obsluh pro každý uzel {node_name: int}
        self.service_completions = {}
        # Pravděpodobnost renege pro každý uzel {node_name: float}
        self.reneging_probability = {}
        # Průměrná čekací doba pro každý uzel {node_name: float}
        self.mean_waiting_time = {}
        # Průměrná doba v systému pro každý uzel {node_name: float}
        self.mean_system_time = {}

    def __repr__(self):
        return (f"SimulationResults(throughput={self.throughput:.4f}, "
                f"ci={self.throughput_ci})")


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
    Řídí frontu událostí, zpracovává příchody, odchody, reneging, poruchy a routing.
    """

    def __init__(self, inp):
        self.inp = inp
        self.rng = RNG(inp.seed)
        self.time = 0.0
        self.events = []
        self.nodes = {}
        # Slovník všech zákazníků (pro přístup podle ID)
        self.customers = {}
        self.next_id = 0
        # Celkový počet zákazníků, kteří opustili systém po warmup
        self.departures = 0
        # Mapování cust_id → renege událost (pro zrušení při zahájení obsluhy)
        self.renege_events = {}

        # Množina aktivních departure eventů – klíč (node, server_id).
        # Při breakdown se příslušná entry vymazá; departure event se pak
        # při zpracování pozná jako stale a přeskočí se.
        self.active_departures = {}  # (node, server_id) → cust_id

        # Vlaj pro jednorázový reset statistik v okamžiku warmup
        self._warmup_reset_done = False

        # Vytvoření všech uzlů podle vstupu
        for n in inp.nodes:
            prio = inp.priorities.get(n, [0])
            self.nodes[n] = Node(n, inp.servers[n], prio)

    def schedule(self, ev):
        """Přidá událost do prioritní fronty."""
        heappush(self.events, ev)

    def _check_warmup_reset(self):
        """
        Jednorázový reset statistik v okamžiku warmup.
        Voláno na začátku každého cyklu hlavní smyčky.
        """
        if not self._warmup_reset_done and self.time >= self.inp.warmup:
            for node in self.nodes.values():
                node.update_stats(self.time)   # zavřeme integrály do warmup
                node.reset_stats_at_warmup(self.time)
            self._warmup_reset_done = True

    def schedule_arrival(self, node):
        """
        Naplánuje další příchod do uzlu (rekurzivně – po každém příchodu plánuje další).
        Pokud by další příchod byl po konci simulace, neplánuje se.
        """
        if node in self.inp.arrival_dists:
            t = self.time + self.inp.arrival_dists[node].random()
            if t < self.inp.sim_time:
                prio = self.inp.priorities.get(node, [0])[0]
                ev = Event(t, "arrival", node=node,
                           cust_id=self.next_id, prio=prio)
                self.schedule(ev)
                self.next_id += 1

    def schedule_breakdown(self, node_name, server_id):
        """Naplánuje další poruchu serveru."""
        if node_name in self.inp.breakdown_dists and self.inp.breakdown_dists[node_name]:
            t = self.time + self.inp.breakdown_dists[node_name].random()
            if t < self.inp.sim_time:
                ev = Event(t, "breakdown", node=node_name, server_id=server_id)
                self.schedule(ev)

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

        # Registrujeme aktivní departure pro tento server
        self.active_departures[(node_name, server.id)] = cust.id

        t_end = self.time + self.inp.service_dists[node_name].random()
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
                    self.inp.patience_dists[ev.node].random()
                r_ev = Event(t_renege, "renege",
                             node=ev.node, cust_id=ev.cust_id)
                self.schedule(r_ev)
                self.renege_events[ev.cust_id] = r_ev

        # Naplánuje další příchod do stejného uzlu
        self.schedule_arrival(ev.node)

    def handle_departure(self, ev):
        """
        Zpracování odchodu zákazníka z uzlu (dokončení obsluhy).
        Uvolní server, případně zahájí obsluhu dalšího zákazníka, plánuje routing event.
        """
        # Validace – ověříme, že departure je stále aktivní.
        # Může být stale, pokud server mezitím dostal breakdown (ten vymazal
        # entry z active_departures). V tom případě event jednoduše přeskočíme.
        key = (ev.node, ev.server_id)
        if key not in self.active_departures or self.active_departures[key] != ev.cust_id:
            return  # stale departure – ignorujeme

        node = self.nodes[ev.node]
        server = node.servers[ev.server_id]
        cust = self.customers[ev.cust_id]

        node.update_stats(self.time)
        node.completions += 1
        if self.time >= self.inp.warmup:
            node.completions_post_warmup += 1
            node.waiting_times.append(cust.service_start - cust.arrival_time)
            node.system_times.append(self.time - cust.arrival_time)

        # Vymazáme aktivní departure záznam
        del self.active_departures[key]

        server.state = "IDLE"
        server.customer = None
        node.update_stats(self.time)

        # Zahájí obsluhu dalšího zákazníka, pokud je ve frontě
        next_c = node.next_customer()
        if next_c:
            self.start_service(ev.node, next_c, server)

        # Probabilistické směrování - vytvoří routing event
        if ev.node in self.inp.routing_matrix:
            routing_ev = Event(self.time, "routing",
                               node=ev.node, cust_id=ev.cust_id)
            self.schedule(routing_ev)
        else:
            # Zákazník opouští systém
            cust.departure = self.time
            if self.time >= self.inp.warmup:
                self.departures += 1

    def handle_routing(self, ev):
        """
        Zpracování routing události - rozhoduje kam zákazník pokračuje.
        """
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
            # Zákazník pokračuje do dalšího uzlu
            prio = self.inp.priorities.get(next_node, [0])[0]
            arr_ev = Event(self.time, "arrival", node=next_node,
                           cust_id=ev.cust_id, prio=prio)
            self.schedule(arr_ev)
        else:
            # Zákazník opouští systém
            cust = self.customers[ev.cust_id]
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

    def handle_breakdown(self, ev):
        """
        Zpracování poruchy serveru.
        Server přejde do stavu DOWN, pokud obsluhoval zákazníka, ten se vrací do fronty.
        Stale departure event pro tento server je invalidován přes active_departures.
        """
        node = self.nodes[ev.node]
        server = node.servers[ev.server_id]

        node.update_stats(self.time)

        # Pokud server obsluhoval zákazníka, vrátí ho do fronty
        if server.state == "BUSY" and server.customer is not None:
            cust = self.customers[server.customer]
            # Resetujeme service_start – zákazník bude obsluhován znovu od nového začátku
            cust.service_start = None
            node.add(cust)

            # Invalidujeme aktivní departure pro tento server.
            # Příslušný departure event zůstane v heap, ale při zpracování
            # bude pozán jako stale a přeskočen (viz handle_departure).
            key = (ev.node, ev.server_id)
            if key in self.active_departures:
                del self.active_departures[key]

            server.customer = None

        server.state = "DOWN"
        node.update_stats(self.time)

        # Naplánuje opravu
        if self.inp.repair_dists[ev.node]:
            t_repair = self.time + self.inp.repair_dists[ev.node].random()
            if t_repair < self.inp.sim_time:
                repair_ev = Event(t_repair, "repair",
                                  node=ev.node, server_id=ev.server_id)
                self.schedule(repair_ev)

    def handle_repair(self, ev):
        """
        Zpracování opravy serveru.
        Server se vrací do stavu IDLE a může začít obsluhovat zákazníka z fronty.
        """
        node = self.nodes[ev.node]
        server = node.servers[ev.server_id]

        node.update_stats(self.time)
        server.state = "IDLE"
        node.update_stats(self.time)

        # Pokud je ve frontě zákazník, zahájí obsluhu
        next_c = node.next_customer()
        if next_c:
            self.start_service(ev.node, next_c, server)

        # Naplánuje další poruchu
        self.schedule_breakdown(ev.node, ev.server_id)

    def run(self):
        """Hlavní smyčka simulace – zpracovává události dokud nejsou vyčerpány nebo nepřekročí sim_time."""
        # Naplánuje první příchody do všech uzlů s externími příchody
        for n in self.inp.nodes:
            self.schedule_arrival(n)

        # Naplánuje první poruchy pro všechny servery
        for n in self.inp.nodes:
            if n in self.inp.breakdown_dists and self.inp.breakdown_dists[n]:
                for server_id in range(len(self.nodes[n].servers)):
                    self.schedule_breakdown(n, server_id)

        while self.events:
            ev = heappop(self.events)
            if ev.time > self.inp.sim_time:
                break
            self.time = ev.time

            # Jednorázový reset statistik při dosažení warmup
            self._check_warmup_reset()

            if ev.typ == "arrival":
                self.handle_arrival(ev)
            elif ev.typ == "departure":
                self.handle_departure(ev)
            elif ev.typ == "renege":
                self.handle_renege(ev)
            elif ev.typ == "breakdown":
                self.handle_breakdown(ev)
            elif ev.typ == "repair":
                self.handle_repair(ev)
            elif ev.typ == "routing":
                self.handle_routing(ev)

        # Finální aktualizace statistik na konci simulace
        for node in self.nodes.values():
            node.update_stats(self.time)

    def get_results(self):
        """
        Shromáždí a vrátí všechny klíčové statistiky simulace.
        Vrátí explicitní SimulationResults objekt.
        Metriky konzistentně používají post-warmup hodnoty.
        """
        eff = self.inp.sim_time - self.inp.warmup

        res = SimulationResults()
        res.throughput = self.departures / eff if eff > 0 else 0.0

        for n, node in self.nodes.items():
            # Průměrná délka fronty – integrál / efektivní doba (post-warmup)
            res.mean_queue_length[n] = node.queue_integral / \
                eff if eff > 0 else 0.0

            # Využití serverů – busy_time / dostupný čas (oboje post-warmup)
            available_time = len(node.servers) * eff - sum(node.down_time)
            res.server_utilization[n] = (
                sum(node.busy_time) /
                available_time if available_time > 0 else 0.0
            )

            # Celkový počet obsluh (od začátku – pro ladění / informaci)
            res.service_completions[n] = node.completions

            # Pravděpodobnost renege – konzistentně post-warmup countery
            total_post_warmup = node.completions_post_warmup + node.reneges
            res.reneging_probability[n] = (
                node.reneges / total_post_warmup if total_post_warmup > 0 else 0.0
            )

            # Průměrná čekací doba (pouze po warmup)
            res.mean_waiting_time[n] = (
                sum(node.waiting_times) / len(node.waiting_times)
                if node.waiting_times else 0.0
            )

            # Průměrná doba v systému (pouze po warmup)
            res.mean_system_time[n] = (
                sum(node.system_times) / len(node.system_times)
                if node.system_times else 0.0
            )

        return res


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
    last_res = None
    for b in range(inp.batch_count):
        new_inp = SimulationInput(**inp.__dict__)
        new_inp.seed = inp.seed + b * 1000
        new_inp.batch_count = 1
        s = Simulator(new_inp)
        s.run()
        last_res = s.get_results()
        thru.append(last_res.throughput)

    mean = sum(thru) / len(thru)
    if len(thru) > 1:
        var = sum((x - mean)**2 for x in thru) / (len(thru) - 1)
        err = math.sqrt(var / len(thru))
        margin = 2 * err
        ci = (mean - margin, mean + margin)
    else:
        ci = (mean, mean)

    # Vracáme výsledky poslední batch, přepíšeme throughput a CI
    last_res.throughput = mean
    last_res.throughput_ci = ci
    return last_res
