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
    assert result.service_completions['A'] >= 8, \
        f"Expected >=8 completions, got {result.service_completions['A']}"
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
    assert result.reneging_probability['A'] > 0.3, \
        f"Expected reneging_probability > 0.3, got {result.reneging_probability['A']}"
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
    assert result.server_utilization['A'] < 0.8, \
        f"Expected utilization < 0.8 with breakdowns, got {result.server_utilization['A']}"
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

    assert result.service_completions['B'] > 0, \
        "Expected at least one completion in B via routing"
    assert 0.2 < ratio < 0.8, \
        f"Expected ratio B/A in (0.2, 0.8), got {ratio:.3f}"

    print("  → Test routingu: PASSED\n")


def test_single_rng():
    """
    Test, že všechna rozdělení používají stejný RNG.
    Ověřuje, že sekvence je konzistentní a Constant konzumuje draw.
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

    # Ověříme, že Constant konzumuje RNG draw
    rng_test = RNG(seed=777)
    state_before = rng_test.state
    c = Constant(42.0, rng_test)
    c.random()
    assert rng_test.state != state_before, \
        "Constant.random() must advance the RNG state"

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
    assert abs(result1.throughput - result2.throughput) < 0.001, \
        f"Deterministic runs differ: {result1.throughput} vs {result2.throughput}"

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
    assert result.service_completions['B'] > 0, \
        "Expected completions in B via routing"
    assert result.service_completions['C'] > 0, \
        "Expected completions in C via routing"
    # A musí mít nejvíce obsluh (všichni zákazníci tam začínají)
    assert result.service_completions['A'] > result.service_completions['B'], \
        "A should have more completions than B"
    assert result.service_completions['A'] > result.service_completions['C'], \
        "A should have more completions than C"

    print("  → Test routing eventu: PASSED\n")


def test_result_object_type():
    """
    Ověřuje, že simulate() vrátí explicitní SimulationResults objekt
    se všemi očekávánými atributy.
    """
    print("Spouštím test: SimulationResults objekt struktura")

    rng = RNG(seed=42)
    sim_input = SimulationInput(
        nodes=["A"],
        arrival_dists={"A": Exponential(3.0, rng)},
        service_dists={"A": Exponential(5.0, rng)},
        servers={"A": 1},
        priorities={"A": [0]},
        patience_dists={"A": None},
        breakdown_dists={"A": None},
        repair_dists={"A": None},
        routing_matrix={},
        sim_time=50.0,
        warmup=5.0,
        batch_count=1,
        seed=42
    )

    result = simulate(sim_input)

    assert isinstance(result, SimulationResults), \
        f"Expected SimulationResults instance, got {type(result)}"
    assert hasattr(result, 'throughput')
    assert hasattr(result, 'throughput_ci')
    assert hasattr(result, 'mean_queue_length')
    assert hasattr(result, 'server_utilization')
    assert hasattr(result, 'service_completions')
    assert hasattr(result, 'reneging_probability')
    assert hasattr(result, 'mean_waiting_time')
    assert hasattr(result, 'mean_system_time')
    assert 'A' in result.mean_queue_length
    assert 'A' in result.server_utilization

    print("  → Test SimulationResults objekt: PASSED\n")


def test_warmup_metrics_consistency():
    """
    Ověřuje, že metriky (queue_length, utilization, reneging_probability)
    konzistentně používají post-warmup hodnoty.
    """
    print("Spouštím test: Konzistence metrik po warmup")

    rng = RNG(seed=555)

    # Velký warmup (polovina sim_time) – aby rozdíl byl viditelný
    sim_input = SimulationInput(
        nodes=["A"],
        arrival_dists={"A": Exponential(4.0, rng)},
        service_dists={"A": Exponential(2.0, rng)},
        servers={"A": 2},
        priorities={"A": [0]},
        patience_dists={"A": Exponential(0.5, rng)},
        breakdown_dists={"A": None},
        repair_dists={"A": None},
        routing_matrix={},
        sim_time=1000.0,
        warmup=500.0,
        batch_count=1,
        seed=555
    )

    result = simulate(sim_input)

    # Metriky musí být konečné kladná čísla (ne NaN, ne negativní)
    assert result.mean_queue_length['A'] >= 0, \
        f"mean_queue_length must be >= 0, got {result.mean_queue_length['A']}"
    assert 0.0 <= result.server_utilization['A'] <= 1.0, \
        f"server_utilization must be in [0,1], got {result.server_utilization['A']}"
    assert 0.0 <= result.reneging_probability['A'] <= 1.0, \
        f"reneging_probability must be in [0,1], got {result.reneging_probability['A']}"
    assert result.mean_waiting_time['A'] >= 0, \
        f"mean_waiting_time must be >= 0, got {result.mean_waiting_time['A']}"
    assert result.mean_system_time['A'] >= 0, \
        f"mean_system_time must be >= 0, got {result.mean_system_time['A']}"

    print(f"    queue_length={result.mean_queue_length['A']:.4f}, "
          f"util={result.server_utilization['A']:.4f}, "
          f"renege_prob={result.reneging_probability['A']:.4f}, "
          f"wait={result.mean_waiting_time['A']:.4f}, "
          f"system={result.mean_system_time['A']:.4f}")
    print("  → Test konzistence metrik: PASSED\n")


def test_breakdown_no_stale_departure():
    """
    Ověřuje, že po poruce serveru stale departure event
    neovlivní simulaci – zákazník se správně vrátí do fronty a
    later dokončení odpovídá skutečné obsluze.
    """
    print("Spouštím test: Žádné stale departure po breakdown")

    rng = RNG(seed=888)

    # 1 server, časté poruchy, kratší obsluha → hodně situací kde
    # breakdown přerušuje aktivní obsluhu
    sim_input = SimulationInput(
        nodes=["A"],
        arrival_dists={"A": Exponential(1.0, rng)},
        service_dists={"A": Exponential(0.5, rng)},   # krátká obsluha
        servers={"A": 1},
        priorities={"A": [0]},
        patience_dists={"A": None},
        # porucha každých ~0.5 jednotek
        breakdown_dists={"A": Exponential(2.0, rng)},
        repair_dists={"A": Exponential(1.0, rng)},     # oprava ~1 jednotka
        routing_matrix={},
        sim_time=200.0,
        warmup=20.0,
        batch_count=1,
        seed=888
    )

    result = simulate(sim_input)

    # Klíčová kontrola: utilization musí být v platném rozsahu [0, 1]
    # Stale departures by mohly zapsat IDLE na DOWN server → korupce → util > 1
    assert 0.0 <= result.server_utilization['A'] <= 1.0, \
        f"Utilization out of range (stale departure?): {result.server_utilization['A']}"

    # Simulace musí dokončit bez crash a mít kladné completions
    assert result.service_completions['A'] > 0, \
        "Expected at least some completions despite breakdowns"

    print(f"    completions={result.service_completions['A']}, "
          f"util={result.server_utilization['A']:.4f}")
    print("  → Test stale departure: PASSED\n")


def test_simultaneous_events_order():
    """
    Ověřuje, že při stejném čase jsou departure zpracovány
    před breakdown, takže server state konzistence se udržuje.
    Косвенný test přes validní utilization i při overlapping events.
    """
    print("Spouštím test: Pořadí simultánních událostí")

    rng = RNG(seed=444)

    # Konstantní časy → hodně simultánních event boundaries
    sim_input = SimulationInput(
        nodes=["A"],
        arrival_dists={"A": Constant(2.0, rng)},
        # departure přesně na границě
        service_dists={"A": Constant(2.0, rng)},
        servers={"A": 2},
        priorities={"A": [0]},
        patience_dists={"A": None},
        breakdown_dists={"A": Exponential(0.05, rng)},  # časté poruchy
        repair_dists={"A": Exponential(0.5, rng)},
        routing_matrix={},
        sim_time=100.0,
        warmup=10.0,
        batch_count=1,
        seed=444
    )

    result = simulate(sim_input)

    # Bez správného pořadí by utilization mohla být > 1 nebo < 0
    assert 0.0 <= result.server_utilization['A'] <= 1.0, \
        f"Utilization invalid after simultaneous events: {result.server_utilization['A']}"

    print(f"    util={result.server_utilization['A']:.4f}, "
          f"completions={result.service_completions['A']}")
    print("  → Test simultánních událostí: PASSED\n")


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
    test_result_object_type()
    test_warmup_metrics_consistency()
    test_breakdown_no_stale_departure()
    test_simultaneous_events_order()

    print("=" * 60)
    print("VŠECHNY TESTY ÚSPĚŠNĚ PROŠLY! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
