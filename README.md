# MoCaSim – Simulátor front a sítí front

## Přehled projektu

**MoCaSim** (Modular Queueing and Network Simulator) je kompaktní, ale plnohodnotný simulátor frontových systémů implementovaný v čistém Pythonu. Projekt využívá diskrétně-událostní simulaci (Discrete-Event Simulation, DES) pro modelování složitých systémů obsluhy s podporou prioritních front, poruch serverů, netrpělivých zákazníků (reneging) a probabilistického směrování v síti uzlů.

## Klíčové vlastnosti

### Architektura simulace

- **Diskrétně-událostní přístup**: Všechny změny stavu systému jsou řízeny explicitními událostmi (příchody, odchody, poruchy, opravy, routing) uspořádanými v prioritní frontě podle času
- **Deterministická reprodukovatelnost**: Vlastní implementace pseudonáhodného generátoru (LCG) zajišťuje plnou opakovatelnost výsledků při stejném seedu
- **Konzistentní statistické sběry**: Všechny metriky jsou korektně vypočítány s respektováním warmup periody pomocí metody časových integrálů

### Podporované funkce

#### Pravděpodobnostní rozdělení

- **Exponenciální rozdělení**: Pro mezičasy příchodů a doby obsluhy (M/M/c fronty)
- **Konstantní rozdělení**: Pro deterministické testování (D/M/c fronty)
- **Jednotný generátor**: Všechna rozdělení sdílejí společný RNG pomocí metody `sample()`, což zajišťuje konzistentní sekvenci náhodných čísel

#### Prioritní fronty

- Podpora více tříd priority zákazníků v jednom uzlu
- FIFO pořadí v rámci každé prioritní třídy
- Dynamické přiřazování serverů podle dostupnosti a priority

#### Poruchy a opravy serverů

- Modelování nespolehlivých serverů s exponenciálně rozdělenými časy mezi poruchami
- Automatické přeplánování zákazníků při výpadku serveru
- **Robustní správa událostí**: Implementace chrání před zpracováním zastaralých (stale) departure eventů po poruše serveru

#### Netrpěliví zákazníci (Reneging)

- Zákazníci opouštějí frontu po vypršení trpělivosti
- Exponenciální rozdělení času trpělivosti
- Automatické zrušení renege eventu při zahájení obsluhy

#### Síťové směrování

- Probabilistické směrování mezi uzly po dokončení obsluhy
- **Routing jako samostatná událost**: Explicitní `routing` event v event loopu umožňuje přesnou kontrolu toku zákazníků
- Podpora komplexních topologií sítí front

### Statistické výstupy

Simulátor vrací **strukturovaný objekt `Result`** se všemi klíčovými metrikami:

- **Propustnost systému** (throughput) s intervalem spolehlivosti při batch simulacích
- **Průměrná délka fronty** pro každý uzel
- **Využití serverů** (server utilization) – poměr času, kdy jsou servery aktivně zaneprázdněné
- **Pravděpodobnost renege** – podíl zákazníků, kteří odešli bez obsluhy
- **Průměrná čekací doba** zákazníků ve frontě
- **Počet dokončených obsluh** pro každý uzel

Všechny metriky jsou **konzistentně počítány pouze z post-warmup periody** pro eliminaci tranzietnních efektů.

## Struktura projektu

```
MoCaSim/
├── MoCaSim.py          # Jádro simulátoru (všechny třídy a logika)
├── demo.py             # Demonstrační experimenty s matplotlib vizualizací
├── test_mocasim.py     # Komplexní testovací sada
└── README.md           # Tento soubor
```

## Instalace a spuštění

### Požadavky

- Python 3.7+
- matplotlib (pouze pro demo.py vizualizace)

### Instalace matplotlib

```bash
pip install matplotlib
```

### Spuštění testů

```bash
python test_mocasim.py
```

Testy ověřují všechny klíčové funkce včetně správného pořadí událostí při stejném čase a robustnost proti stale events.

### Spuštění demonstrace

```bash
python demo.py
```

Demonstrace provede dva experimenty a zobrazí interaktivní grafy:
1. Vliv počtu serverů na výkonnost (M/M/c systém)
2. Vliv trpělivosti zákazníků (renege analýza)

## Příklad použití

```python
from MoCaSim import *

# Inicializace generátoru náhodných čísel
rng = RNG(seed=42)

# Definice vstupních parametrů
sim_input = SimulationInput(
    nodes=["A", "B"],
    arrival_dists={"A": Exponential(5.0, rng)},  # 5 zákazníků/čas do uzlu A
    service_dists={
        "A": Exponential(8.0, rng),  # průměrná doba obsluhy 1/8
        "B": Exponential(10.0, rng)
    },
    servers={"A": 2, "B": 1},  # 2 servery v A, 1 server v B
    priorities={"A": [0], "B": [0]},
    patience_dists={"A": Exponential(0.2, rng), "B": None},  # renege pouze v A
    breakdown_dists={"A": Exponential(0.05, rng), "B": None},  # poruchy v A
    repair_dists={"A": Exponential(1.0, rng), "B": None},
    routing_matrix={"A": {"B": 0.6}},  # 60% z A → B, 40% opouští systém
    sim_time=1000.0,
    warmup=100.0,
    batch_count=10,  # 10 nezávislých běhů pro CI
    seed=42
)

# Spuštění simulace
result = simulate(sim_input)

# Výpis výsledků
print(f"Propustnost: {result.throughput:.3f} ± {(result.throughput_ci[1] - result.throughput_ci[0])/2:.3f}")
print(f"Využití serverů v A: {result.server_utilization['A']:.3f}")
print(f"Pravděpodobnost renege v A: {result.reneging_prob['A']:.3f}")
print(f"Průměrná délka fronty v B: {result.mean_queue_length['B']:.3f}")
```

## Technické detaily implementace

### Správa událostí při stejném čase

Simulátor používá **explicitní prioritní mapu** pro typy událostí:

```python
_TYPE_PRIORITY = {
    "departure": 0,   # Nejvyšší priorita
    "routing": 1,
    "renege": 2,
    "repair": 3,
    "arrival": 4,
    "breakdown": 5    # Nejnižší priorita
}
```

Tím je zajištěno, že při stejném simulačním čase jsou události zpracovány v konzistentním pořadí, což eliminuje race conditions.

### Ochrana proti stale events

Při poruše serveru během obsluhy:

1. Zákazník je vrácen do fronty
2. Aktivní departure event je **označen jako neplatný** v registru `active_departures`
3. Při pozdějším zpracování departure eventu je ověřena platnost – stale eventy jsou tiše přeskočeny
4. Server state konzistence je zachována

### Warmup perioda

- První část simulace (`warmup`) slouží k ustálení systému
- Statistické integrály (`queue_integral`, `busy_time`, `down_time`) jsou **resetovány na nulu** v okamžiku konce warmup
- Všechny metriky v `Result` objektu odrážejí pouze post-warmup chování

### Společný generátor náhodných čísel

- Všechna pravděpodobnostní rozdělení používají **metodu `sample()`** pro generování hodnot
- Sdílený RNG objekt zajišťuje konzistentní sekvenci napříč všemi rozděleními
- I deterministické `Constant` rozdělení konzumuje draw z RNG pro zachování synchronizace sekvence

## Testování

Testovací sada (`test_mocasim.py`) obsahuje 10 izolovaných testů pokrývajících:

- ✓ Základní zpracování příchodů a odchodů
- ✓ Funkci renege mechanismu
- ✓ Poruchy a opravy serverů
- ✓ Probabilistické směrování
- ✓ Konzistenci společného RNG a metody `sample()`
- ✓ Routing jako samostatnou událost v event loopu
- ✓ Strukturu objektu `Result`
- ✓ Konzistenci metrik po warmup periodě
- ✓ Robustnost proti stale departure events
- ✓ Správné pořadí simultánních událostí

Všechny testy používají **pevné seedy** pro deterministické ověření výsledků.

## Demonstrace

`demo.py` obsahuje dva rozsáhlé experimenty:

### Experiment 1: Vliv počtu serverů

- Variace 1–6 serverů při konstantní intenzitě příchodů
- Analýza průchodnosti, využití, délky fronty a čekací doby
- Identifikace optimální konfigurace

### Experiment 2: Vliv trpělivosti zákazníků

- Různé úrovně trpělivosti (od velmi nízké po nekonečnou)
- Kvantifikace trade-offu mezi ztrátou zákazníků a délkou fronty
- Vizualizace pomocí multi-axis grafu

Grafy jsou zobrazeny pomocí **matplotlib** a nabízejí interaktivní prohlížení.

## Architektuta tříd

### Základní komponenty

- **`RNG`**: Lineární kongruentní generátor pro pseudonáhodná čísla
- **`Exponential`**, **`Constant`**: Pravděpodobnostní rozdělení s metodou `sample()`
- **`Event`**: Reprezentace události s časem, typem a parametry
- **`Customer`**: Zákazník procházející systémem s časovými značkami
- **`Server`**: Obslužné místo se stavy IDLE/BUSY/DOWN
- **`Node`**: Uzel sítě obsahující servery, fronty a statistiky
- **`Result`**: Strukturovaný objekt výsledků simulace
- **`SimulationInput`**: Kontejner vstupních parametrů
- **`Simulator`**: Hlavní třída řídící event loop a simulaci

### Typy událostí

1. **`arrival`**: Příchod zákazníka do uzlu
2. **`departure`**: Dokončení obsluhy a uvolnění serveru
3. **`routing`**: Rozhodnutí o směrování po dokončení obsluhy
4. **`renege`**: Odchod netrpělivého zákazníka z fronty
5. **`breakdown`**: Porucha serveru
6. **`repair`**: Oprava a restart serveru

## Výhody implementace

### Korektnost

- Explicitní správa stavů serverů (IDLE/BUSY/DOWN)
- Validace aktivity departure eventů před zpracováním
- Konzistentní akumulace statistik pouze po warmup

### Reprodukovatelnost

- Deterministický LCG generátor s kontrolovatelným seedem
- Jednotná sekvence náhodných čísel napříč všemi rozděleními
- Fixní pořadí zpracování simultánních událostí

### Čitelnost

- Plně komentovaný kód v češtině
- Jasná separace odpovědností mezi třídami
- Strukturované výsledky přes dedikovaný `Result` objekt

### Rozšiřitelnost

- Snadné přidání nových typů událostí
- Modulární architektura umožňující nová rozdělení
- Flexibilní topologie sítí front

## Omezení a budoucí rozšíření

### Aktuální omezení

- Pouze exponenciální a konstantní rozdělení (lze snadno rozšířit)
- Statická topologie sítě (uzly se nevytváří/neruší dynamicky)
- Jednoduchá prioritní logika (bez preemption)

### Možná rozšíření

- Normální, uniformní, gamma a další rozdělení
- Batch arrivals (skupinové příchody)
- Balking (odmítnutí vstupu při plné frontě)
- Preemptive priority
- Dynamická konfigurace sítě
- Grafická vizualizace průběhu simulace v reálném čase

## Autor a licence

Projekt je vytvořen pro akademické a výukové účely. Kód je plně komentován v češtině pro snadnější pochopení implementace diskrétně-událostní simulace.

---

**Poznámka**: Simulátor je navržen s důrazem na **korektnost, reprodukovatelnost a čitelnost kódu**. Všechny implementační detaily (sdílený RNG s metodou `sample()`, explicitní `Result` objekt, warmup reset, event ordering při stejném čase, stale event handling při poruchách, routing jako samostatná událost) jsou pečlivě ošetřeny a ověřeny komplexní testovací sadou.
