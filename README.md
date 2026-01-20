# MoCaSim - Simulátor sítí front

Framework pro diskrétně-událostní simulaci určený k modelování a analýze sítí front s podporou více serverů, priorit, netrpělivosti zákazníků (renege), pravděpodobnostního směrování a poruch serverů.

## Vlastnosti

- **Různé typy front**: Podpora M/M/c, M/D/c a obecných systémů hromadné obsluhy
- **Prioritní fronty**: Zpracování více prioritních tříd v rámci každého uzlu
- **Netrpělivost zákazníků**: Modelování renege chování s nastavitelnými rozděleními trpělivosti
- **Síťové směrování**: Pravděpodobnostní směrování mezi uzly jako samostatné události
- **Spolehlivost serverů**: Plná podpora poruch (breakdown) a oprav (repair) serverů
- **Jednotný generátor**: Všechna rozdělení sdílí jeden RNG pro reprodukovatelnost
- **Dávková simulace**: Spuštění více replikací s intervaly spolehlivosti
- **Statistická analýza**: Výpočet propustnosti, využití, délek front a čekacích dob

## Rychlý start

```python
from MoCaSim import *

# Inicializace jednotného generátoru náhodných čísel
rng = RNG(seed=42)

# Konfigurace simulace
sim_input = SimulationInput(
    nodes=["Server"],
    arrival_dists={"Server": Exponential(5.0, rng)},  # λ = 5 příchodů/časovou jednotku
    service_dists={"Server": Exponential(2.0, rng)},  # μ = 2 obsluhy/časovou jednotku
    servers={"Server": 3},                             # 3 paralelní servery
    priorities={"Server": [0]},                        # Jedna prioritní třída
    patience_dists={"Server": None},                   # Bez renege
    breakdown_dists={"Server": None},                  # Bez poruch
    repair_dists={"Server": None},                     # Bez oprav
    routing_matrix={},                                 # Bez routingu
    sim_time=1000.0,
    warmup=100.0,
    batch_count=5,
    seed=42
)

# Spuštění simulace
result = simulate(sim_input)

# Přístup k výsledkům
print(f"Propustnost: {result.throughput:.3f}")
print(f"Využití serveru: {result.server_utilization['Server']:.3f}")
print(f"Průměrná délka fronty: {result.mean_queue_length['Server']:.3f}")
print(f"Průměrná čekací doba: {result.waiting_time_mean['Server']:.3f}")
```

## Struktura projektu

- **MoCaSim.py** - Jádro simulačního enginu se zpracováním událostí a sběrem statistik
- **demo.py** - Demonstrační experimenty s vizualizacemi v matplotlib
- **test_mocasim.py** - Komplexní testovací sada ověřující klíčovou funkcionalitu

## Klíčové komponenty

### Generování náhodných čísel
- Vlastní RNG založený na LCG pro reprodukovatelné výsledky
- **Jednotný generátor** - všechna rozdělení sdílí jeden RNG objekt
- Podpora exponenciálního a konstantního rozdělení

### Události
- **arrival** - zákazník vstupuje do uzlu
- **departure** - dokončení obsluhy
- **renege** - netrpělivý zákazník odchází
- **breakdown** - server se porouchá
- **repair** - server je opraven
- **routing** - rozhodování o směrování zákazníka

### Sledované statistiky
- Propustnost (obsloužení zákazníci za časovou jednotku)
- Využití serveru (% času zaneprázdněn, respektuje DOWN čas)
- Průměrná délka fronty (časově vážená)
- Průměrná čekací doba (doba ve frontě)
- Pravděpodobnost renege
- Dokončené obsluhy na uzel

## Příklady

### Fronta M/M/1
```python
rng = RNG(seed=12345)

sim_input = SimulationInput(
    nodes=["A"],
    arrival_dists={"A": Exponential(3.0, rng)},
    service_dists={"A": Exponential(4.0, rng)},
    servers={"A": 1},
    priorities={"A": [0]},
    patience_dists={"A": None},
    breakdown_dists={"A": None},
    repair_dists={"A": None},
    routing_matrix={},
    sim_time=5000.0,
    warmup=500.0,
    batch_count=10,
    seed=12345
)
```

### Tandemová fronta se směrováním
```python
rng = RNG(seed=789)

sim_input = SimulationInput(
    nodes=["A", "B"],
    arrival_dists={"A": Exponential(2.0, rng)},
    service_dists={"A": Exponential(5.0, rng), "B": Exponential(5.0, rng)},
    servers={"A": 1, "B": 1},
    priorities={"A": [0], "B": [0]},
    patience_dists={"A": None, "B": None},
    breakdown_dists={"A": None, "B": None},
    repair_dists={"A": None, "B": None},
    routing_matrix={"A": {"B": 0.5}},  # 50% směrováno z A do B (routing event)
    sim_time=100.0,
    warmup=10.0,
    batch_count=5,
    seed=789
)
```

### Netrpěliví zákazníci
```python
rng = RNG(seed=54321)

sim_input = SimulationInput(
    nodes=["A"],
    arrival_dists={"A": Exponential(5.0, rng)},
    service_dists={"A": Exponential(2.0, rng)},
    servers={"A": 2},
    priorities={"A": [0]},
    patience_dists={"A": Exponential(0.2, rng)},  # Průměrná trpělivost: 5 časových jednotek
    breakdown_dists={"A": None},
    repair_dists={"A": None},
    routing_matrix={},
    sim_time=3000.0,
    warmup=300.0,
    batch_count=5,
    seed=54321
)
```

### Poruchy a opravy serverů
```python
rng = RNG(seed=99999)

sim_input = SimulationInput(
    nodes=["A"],
    arrival_dists={"A": Exponential(2.0, rng)},
    service_dists={"A": Exponential(4.0, rng)},
    servers={"A": 3},
    priorities={"A": [0]},
    patience_dists={"A": None},
    breakdown_dists={"A": Exponential(0.1, rng)},  # Průměrná doba do poruchy: 10 jednotek
    repair_dists={"A": Exponential(0.5, rng)},     # Průměrná doba opravy: 2 jednotky
    routing_matrix={},
    sim_time=1000.0,
    warmup=100.0,
    batch_count=5,
    seed=99999
)
```

## Důležité poznámky

### Jednotný generátor (RNG)
Všechna rozdělení **musí** sdílet stejný RNG objekt pro zajištění:
- Reprodukovatelnosti výsledků
- Konzistentní sekvence náhodných čísel
- Správné fungování batch simulací

```python
# SPRÁVNĚ - jeden RNG pro všechna rozdělení
rng = RNG(seed=42)
arrival = Exponential(2.0, rng)
service = Exponential(3.0, rng)
patience = Exponential(0.5, rng)

# ŠPATNĚ - různé RNG objekty
arrival = Exponential(2.0, RNG(seed=42))
service = Exponential(3.0, RNG(seed=42))  # Nebude fungovat správně!
```

### Routing jako event
Směrování zákazníků mezi uzly je implementováno jako samostatná událost (`routing`), která:
- Odděluje logiku dokončení obsluhy od rozhodování o směrování
- Umožňuje přesnější simulaci časování
- Poskytuje lepší modularitu kódu

### Poruchy serverů
Při poruše serveru (breakdown):
- Server přejde do stavu DOWN
- Pokud obsluhoval zákazníka, ten se vrací do fronty
- Po opravě (repair) se server vrací do stavu IDLE
- Statistiky využití respektují DOWN čas

## Spuštění demonstrací

Demonstrační skript spouští dva experimenty a zobrazuje matplotlib vizualizace:

```bash
python demo.py
```

**Experiment 1**: Vliv počtu serverů na výkonnost systému
**Experiment 2**: Vliv trpělivosti zákazníků na renege chování

## Spuštění testů

Spusťte komplexní testovací sadu pro ověření funkcionality:

```bash
python test_mocasim.py
```

Testy pokrývají:
- Základní zpracování příchodů a obsluh
- Chování renege
- Mechanismus poruch a oprav serverů
- Pravděpodobnostní směrování (včetně routing eventu)
- Jednotný RNG napříč rozděleními
- Deterministické chování při stejném seedu

## Požadavky

- Python 3.6+
- matplotlib (pouze pro demonstrační vizualizace)

## Architektura

### Event Loop
Simulace je řízena prioritní frontou událostí (heapq), která zpracovává:
1. `arrival` - příchod zákazníka do uzlu
2. `departure` - dokončení obsluhy zákazníka
3. `routing` - rozhodnutí kam zákazník pokračuje
4. `renege` - odchod netrpělivého zákazníka
5. `breakdown` - porucha serveru
6. `repair` - oprava serveru

### Statistiky
- **Časové integrály**: Přesné výpočty průměrných hodnot metodou "area under curve"
- **Warmup perioda**: Ignorování začátečního tranzientního chování
- **Batch replikace**: Odhad intervalů spolehlivosti pomocí nezávislých běhů

## Licence

Tento projekt je poskytován tak, jak je, pro vzdělávací a výzkumné účely.