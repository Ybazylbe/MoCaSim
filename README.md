# MoCaSim - Simulátor sítí front

Framework pro diskrétně-událostní simulaci určený k modelování a analýze sítí front s podporou více serverů, priorit, netrpělivosti zákazníků (renege) a pravděpodobnostního směrování.

## Vlastnosti

- **Různé typy front**: Podpora M/M/c, M/D/c a obecných systémů hromadné obsluhy
- **Prioritní fronty**: Zpracování více prioritních tříd v rámci každého uzlu
- **Netrpělivost zákazníků**: Modelování renege chování s nastavitelnými rozděleními trpělivosti
- **Síťové směrování**: Pravděpodobnostní směrování mezi uzly pro vícestupňové systémy
- **Spolehlivost serverů**: Framework pro modelování poruch a oprav serverů
- **Dávková simulace**: Spuštění více replikací s intervaly spolehlivosti
- **Statistická analýza**: Výpočet propustnosti, využití, délek front a čekacích dob

## Rychlý start

```python
from MoCaSim import *

# Inicializace generátoru náhodných čísel
rng = RNG(seed=42)

# Konfigurace simulace
sim_input = SimulationInput(
    nodes=["Server"],
    arrival_dists={"Server": Exponential(5.0, rng)},  # λ = 5 příchodů/časovou jednotku
    service_dists={"Server": Exponential(2.0, rng)},  # μ = 2 obsluhy/časovou jednotku
    servers={"Server": 3},                             # 3 paralelní servery
    priorities={"Server": [0]},                        # Jedna prioritní třída
    patience_dists={"Server": None},                   # Bez renege
    breakdown_dists={"Server": None},
    repair_dists={"Server": None},
    routing_matrix={},
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
- Podpora exponenciálního a konstantního rozdělení

### Události
- Události příchodu (zákazník vstupuje do uzlu)
- Události odchodu (dokončení obsluhy)
- Události renege (netrpělivý zákazník odchází)

### Sledované statistiky
- Propustnost (obsloužení zákazníci za časovou jednotku)
- Využití serveru (% času zaneprázdněn)
- Průměrná délka fronty (časově vážená)
- Průměrná čekací doba (doba ve frontě)
- Pravděpodobnost renege
- Dokončené obsluhy na uzel

## Příklady

### Fronta M/M/1
```python
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
sim_input = SimulationInput(
    nodes=["A", "B"],
    arrival_dists={"A": Exponential(2.0, rng)},
    service_dists={"A": Exponential(5.0, rng), "B": Exponential(5.0, rng)},
    servers={"A": 1, "B": 1},
    priorities={"A": [0], "B": [0]},
    patience_dists={"A": None, "B": None},
    breakdown_dists={"A": None, "B": None},
    repair_dists={"A": None, "B": None},
    routing_matrix={"A": {"B": 0.5}},  # 50% směrováno z A do B
    sim_time=100.0,
    warmup=10.0,
    batch_count=5,
    seed=789
)
```

### Netrpěliví zákazníci
```python
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
- Mechanismus poruch serverů
- Pravděpodobnostní směrování

## Požadavky

- Python 3.6+
- matplotlib (pouze pro demonstrační vizualizace)

## Licence

Tento projekt je poskytován tak, jak je, pro vzdělávací a výzkumné účely.