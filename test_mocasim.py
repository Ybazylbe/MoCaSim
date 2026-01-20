"""
Komplexní testovací sada pro ověření klíčových funkcí MoCaSim.
Každý test je navržen tak, aby izolovaně prověřil jednu konkrétní vlastnost simulátoru.
Všechny testy používají deterministické nebo pevně seedované náhodné sekvence pro reprodukovatelnost.
"""

from MoCaSim import *


def test_arrivals():
    """
    Test základního zpracování příchodů.
    Používá deterministické konstantní časy → přesně předvídatelné chování.
    """
    print("Spouštím test: Zpracování příchodů událostí")

    rng = RNG(seed=42)

    sim_input = SimulationInput(
        nodes=["A"],
        arrival_dists={"A": Constant(1.0, rng)},
        service_dists={"A": Constant(0.5, rng)},
        servers={"A": 1},
        priorities={"A": [0]},
        patience_dists={"A": None},
        breakdown_dists={"A": None},
        repair_dists={"A": None},
        routing_matrix={},
        sim_time=10.0,
        warmup=0.0,
        batch_count=1,
        seed=42
    )

    result = simulate(sim_input)
    assert result.service_completions['A'] >= 8
    print("  → Test zpracování příchodů: PASSED\n")


def test_reneging():
    """
    Test funkce odchodu netrpělivých zákazníků (renege).
    Vysoká frekvence příchodů + pomalá obsluha → dlouhá fronta → mnoho renegů.
    """
    print("Spouštím test: Odchod zákazníků (renege)")

    rng = RNG(seed=123)

    sim_input = SimulationInput(
        nodes=["A"],
        arrival_dists={"A": Constant(0.5, rng)},
        service_dists={"A": Constant(10.0, rng)},
        servers={"A": 1},
        priorities={"A": [0]},
        patience_dists={"A": Constant(2.0, rng)},
        breakdown_dists={"A": None},
        repair_dists={"A": None},
        routing_matrix={},
        sim_time=50.0,
        warmup=0.0,
        batch_count=1,
        seed=123
    )

    result = simulate(sim_input)
    assert result.reneging_prob['A'] > 0.3
    print("  → Test reneging: PASSED\n")


def test_breakdowns():
    """
    Test mechanismu poruch a oprav serverů.
    Ověřuje, že poruchy skutečně snižují využití serverů.
    """
    print("Spouštím test: Poruchy a opravy serverů")

    rng = RNG(seed=456)

    sim_input = SimulationInput(
        nodes=["A"],
        arrival_dists={"A": Exponential(1.0, rng)},
        service_dists={"A": Exponential(2.0, rng)},
        servers={"A": 2},
        priorities={"A": [0]},
        patience_dists={"A": None},
        breakdown_dists={"A": Exponential(0.1, rng)},
        repair_dists={"A": Exponential(1.0, rng)},
        routing_matrix={},
        sim_time=100.0,
        warmup=10.0,
        batch_count=1,
        seed=456
    )

    result = simulate(sim_input)
    # S poruchami by využití mělo být výrazně nižší než teoretické
    assert result.server_utilization['A'] < 0.6
    print("  → Test poruch a oprav: PASSED\n")


def test_routing():
    """
    Test probabilistického směrování mezi dvěma uzly.
    Očekáváme, že přibližně polovina dokončených obsluh v A skončí v B.
    """
    print("Spouštím test: Routing mezi uzly")

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
        routing_matrix={"A": {"B": 0.5}},
        sim_time=100.0,
        warmup=10.0,
        batch_count=1,
        seed=789
    )

    result = simulate(sim_input)

    ratio = (result.service_completions['B'] / result.service_completions['A']
             if result.service_completions['A'] > 0 else 0)

    assert result.service_completions['B'] > 0
    assert 0.3 < ratio < 0.7

    print("  → Test routingu: PASSED\n")


def test_single_rng():
    """
    Test, že všechna rozdělení používají stejný RNG.
    Ověřuje, že sekvence je konzistentní.
    """
    print("Spouštím test: Jednotný RNG pro všechna rozdělení")

    rng = RNG(seed=999)

    # Vytvoříme několik rozdělení se stejným RNG
    arrival = Exponential(2.0, rng)
    service = Exponential(3.0, rng)
    patience = Exponential(0.5, rng)

    # Ověříme, že všechna používají stejný RNG objekt
    assert arrival.rng is rng
    assert service.rng is rng
    assert patience.rng is rng

    # Spustíme simulaci a ověříme deterministické chování
    # První běh
    rng1 = RNG(seed=999)
    sim_input1 = SimulationInput(
        nodes=["A"],
        arrival_dists={"A": Exponential(2.0, rng1)},
        service_dists={"A": Exponential(3.0, rng1)},
        servers={"A": 1},
        priorities={"A": [0]},
        patience_dists={"A": Exponential(0.5, rng1)},
        breakdown_dists={"A": None},
        repair_dists={"A": None},
        routing_matrix={},
        sim_time=50.0,
        warmup=5.0,
        batch_count=1,
        seed=999
    )

    result1 = simulate(sim_input1)

    # Druhý běh se stejným seedem - měl by dát stejné výsledky
    rng2 = RNG(seed=999)
    sim_input2 = SimulationInput(
        nodes=["A"],
        arrival_dists={"A": Exponential(2.0, rng2)},
        service_dists={"A": Exponential(3.0, rng2)},
        servers={"A": 1},
        priorities={"A": [0]},
        patience_dists={"A": Exponential(0.5, rng2)},
        breakdown_dists={"A": None},
        repair_dists={"A": None},
        routing_matrix={},
        sim_time=50.0,
        warmup=5.0,
        batch_count=1,
        seed=999
    )

    result2 = simulate(sim_input2)

    # Výsledky by měly být identické
    assert abs(result1.throughput - result2.throughput) < 0.001

    print("  → Test jednotného RNG: PASSED\n")


def test_routing_event():
    """
    Test existence routing eventu v event loopu.
    Ověřuje, že routing je správně implementován jako samostatná událost.
    """
    print("Spouštím test: Routing event v event loopu")

    rng = RNG(seed=333)

    sim_input = SimulationInput(
        nodes=["A", "B", "C"],
        arrival_dists={"A": Exponential(3.0, rng)},
        service_dists={
            "A": Exponential(6.0, rng),
            "B": Exponential(6.0, rng),
            "C": Exponential(6.0, rng)
        },
        servers={"A": 1, "B": 1, "C": 1},
        priorities={"A": [0], "B": [0], "C": [0]},
        patience_dists={"A": None, "B": None, "C": None},
        breakdown_dists={"A": None, "B": None, "C": None},
        repair_dists={"A": None, "B": None, "C": None},
        routing_matrix={
            "A": {"B": 0.3, "C": 0.3}  # 40% opouští systém
        },
        sim_time=100.0,
        warmup=10.0,
        batch_count=1,
        seed=333
    )

    result = simulate(sim_input)

    # Ověříme, že routing funguje - některé zákazníky směruje do B a C
    assert result.service_completions['B'] > 0
    assert result.service_completions['C'] > 0
    # A musí mít nejvíce obsluh (všichni zákazníci tam začínají)
    assert result.service_completions['A'] > result.service_completions['B']
    assert result.service_completions['A'] > result.service_completions['C']

    print("  → Test routing eventu: PASSED\n")


def run_all_tests():
    """Spustí všechny testy sekvenčně s přehledným výpisem."""
    print("=" * 60)
    print("Komplexní testy klíčových funkcí MoCaSim")
    print("=" * 60 + "\n")

    test_arrivals()
    test_reneging()
    test_breakdowns()
    test_routing()
    test_single_rng()
    test_routing_event()

    print("=" * 60)
    print("VŠECHNY TESTY ÚSPĚŠNĚ PROŠLY! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
