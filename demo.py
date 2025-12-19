"""
Demonstrační experiment a vizualizace pro MoCaSim s grafy přes matplotlib
"""

from MoCaSim import *
import math
import matplotlib.pyplot as plt


def experiment_server_count():
    """Experiment: Vliv počtu serverů na výkonnost systému"""
    print("=" * 70)
    print("EXPERIMENT: Vliv počtu serverů na výkonnost")
    print("=" * 70)
    print()

    arrival_rate = 5.0
    service_rate = 2.0
    server_counts = [1, 2, 3, 4, 5, 6]

    results = []

    for num_servers in server_counts:
        print(f"Probíhá simulace s {num_servers} server(y)...")

        rng = RNG(seed=12345)

        sim_input = SimulationInput(
            nodes=["A"],
            arrival_dists={"A": Exponential(arrival_rate, rng)},
            service_dists={"A": Exponential(service_rate, rng)},
            servers={"A": num_servers},
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

        result = simulate(sim_input)

        results.append({
            'servers': num_servers,
            'throughput': result.throughput,
            'throughput_low': result.throughput_ci[0],
            'throughput_high': result.throughput_ci[1],
            'utilization': result.server_utilization['A'],
            'mean_queue': result.mean_queue_length['A'],
            'mean_wait': result.waiting_time_mean['A']
        })

    print()
    print("=" * 70)
    print("VÝSLEDKY")
    print("=" * 70)
    print()
    print(f"{'Servery':<10} {'Propustnost':<15} {'Využití':<15} {'Prům. fronta':<15} {'Prům. čekání':<15}")
    print("-" * 70)

    for r in results:
        ci_width = (r['throughput_high'] - r['throughput_low']) / 2
        throughput_str = f"{r['throughput']:.3f}±{ci_width:.3f}"
        print(f"{r['servers']:<10} {throughput_str:<15} {r['utilization']:<15.4f} "
              f"{r['mean_queue']:<15.4f} {r['mean_wait']:<15.4f}")

    print()
    print("=" * 70)
    print("ANALÝZA")
    print("=" * 70)
    print()

    rho = arrival_rate / service_rate
    print(f"Intenzita provozu na server (ρ): {rho:.3f}")
    print(f"Minimální počet serverů pro stabilitu: {math.ceil(rho)}")
    print()

    min_wait = min(results, key=lambda x: x['mean_wait'])
    print(f"Konfigurace s minimální čekací dobou:")
    print(f"  Servery: {min_wait['servers']}")
    print(f"  Prům. čekání: {min_wait['mean_wait']:.4f}")
    print(f"  Využití: {min_wait['utilization']:.4f}")

    return results


def experiment_reneging_impact():
    """Experiment: Vliv trpělivosti zákazníků na výkonnost"""
    print("\n" + "=" * 70)
    print("EXPERIMENT: Vliv trpělivosti zákazníků na výkonnost (renege)")
    print("=" * 70)
    print()

    patience_levels = [
        ("Bez renege", None),
        ("Vysoká (prům. 10)", 10.0),
        ("Střední (prům. 5)", 5.0),
        ("Nízká (prům. 2)", 2.0),
        ("Velmi nízká (prům. 1)", 1.0)
    ]

    results = []

    for label, patience_mean in patience_levels:
        print(f"Probíhá simulace: {label}...")

        rng = RNG(seed=54321)

        patience_dist = None if patience_mean is None else Exponential(
            1.0 / patience_mean, rng)

        sim_input = SimulationInput(
            nodes=["A"],
            arrival_dists={"A": Exponential(5.0, rng)},
            service_dists={"A": Exponential(2.0, rng)},
            servers={"A": 2},
            priorities={"A": [0]},
            patience_dists={"A": patience_dist},
            breakdown_dists={"A": None},
            repair_dists={"A": None},
            routing_matrix={},
            sim_time=3000.0,
            warmup=300.0,
            batch_count=5,
            seed=54321
        )

        result = simulate(sim_input)

        results.append({
            'label': label,
            'reneging_prob': result.reneging_prob['A'],
            'throughput': result.throughput,
            'mean_queue': result.mean_queue_length['A']
        })

    print()
    print("=" * 70)
    print("VÝSLEDKY")
    print("=" * 70)
    print()
    print(f"{'Trpělivost':<30} {'Pravd. renege':<18} {'Propustnost':<15} {'Prům. fronta':<15}")
    print("-" * 70)

    for r in results:
        print(
            f"{r['label']:<30} {r['reneging_prob']:<18.4f} {r['throughput']:<15.4f} {r['mean_queue']:<15.4f}")

    print()
    print("=" * 70)
    print("ANALÝZA")
    print("=" * 70)
    print()
    print("- Nižší trpělivost → vyšší pravděpodobnost odchodu")
    print("- Vyšší renege → kratší fronty, ale nižší propustnost")
    print("- Důležitá rovnováha mezi čekací dobou a ztrátou zákazníků")

    return results


def create_matplotlib_visualization(server_results, renege_results):
    """Vytvoří profesionální grafy pomocí matplotlib – pouze zobrazení, bez ukládání na disk"""

    # === Graf 1: Vliv počtu serverů ===
    plt.figure(figsize=(12, 8))

    servers = [r['servers'] for r in server_results]
    throughput = [r['throughput'] for r in server_results]
    throughput_low = [r['throughput_low'] for r in server_results]
    throughput_high = [r['throughput_high'] for r in server_results]
    queue = [r['mean_queue'] for r in server_results]
    wait = [r['mean_wait'] for r in server_results]
    util = [r['utilization'] for r in server_results]

    ax1 = plt.subplot(2, 2, 1)
    ax1.errorbar(servers, throughput,
                 yerr=[[throughput[i] - throughput_low[i] for i in range(len(servers))],
                       [throughput_high[i] - throughput[i] for i in range(len(servers))]],
                 fmt='o-', capsize=5, label='Propustnost')
    ax1.set_xlabel('Počet serverů')
    ax1.set_ylabel('Propustnost')
    ax1.set_title('Propustnost systému')
    ax1.grid(True, alpha=0.3)

    ax2 = plt.subplot(2, 2, 2)
    ax2.plot(servers, util, 's-', color='green', label='Využití serverů')
    ax2.set_xlabel('Počet serverů')
    ax2.set_ylabel('Využití')
    ax2.set_title('Využití serverů')
    ax2.grid(True, alpha=0.3)

    ax3 = plt.subplot(2, 2, 3)
    ax3.plot(servers, queue, 'd-', color='red', label='Prům. délka fronty')
    ax3.set_xlabel('Počet serverů')
    ax3.set_ylabel('Průměrná délka fronty')
    ax3.set_title('Délka fronty')
    ax3.grid(True, alpha=0.3)

    ax4 = plt.subplot(2, 2, 4)
    ax4.plot(servers, wait, '^-', color='orange', label='Prům. čekací doba')
    ax4.set_xlabel('Počet serverů')
    ax4.set_ylabel('Průměrná čekací doba')
    ax4.set_title('Čekací doba')
    ax4.grid(True, alpha=0.3)

    plt.suptitle(
        'Vliv počtu serverů na výkonnost systému (M/M/c)', fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()  # Pouze zobrazení, bez ukládání

    # === Graf 2: Vliv trpělivosti (renege) ===
    plt.figure(figsize=(10, 6))

    labels = [r['label'] for r in renege_results]
    renege_prob = [r['reneging_prob'] for r in renege_results]
    throughput_r = [r['throughput'] for r in renege_results]
    queue_r = [r['mean_queue'] for r in renege_results]

    x = range(len(labels))

    ax1 = plt.subplot(1, 1, 1)
    color1 = 'tab:blue'
    color2 = 'tab:red'
    color3 = 'tab:green'

    ln1 = ax1.plot(x, throughput_r, 'o-', color=color1, label='Propustnost')
    ax1.set_xlabel('Úroveň trpělivosti')
    ax1.set_ylabel('Propustnost', color=color1)
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=15, ha='right')

    ax2 = ax1.twinx()
    ln2 = ax2.plot(x, renege_prob, 's--', color=color2,
                   label='Pravděpodobnost renege')
    ax2.set_ylabel('Pravděpodobnost renege', color=color2)
    ax2.tick_params(axis='y', labelcolor=color2)

    ax3 = ax1.twinx()
    ax3.spines['right'].set_position(('outward', 60))
    ln3 = ax3.plot(x, queue_r, 'd-.', color=color3, label='Prům. délka fronty')
    ax3.set_ylabel('Prům. délka fronty', color=color3)
    ax3.tick_params(axis='y', labelcolor=color3)

    lns = ln1 + ln2 + ln3
    labs = [l.get_label() for l in lns]
    ax1.legend(lns, labs, loc='upper left')

    plt.title('Vliv trpělivosti zákazníků na výkonnost systému')
    plt.tight_layout()
    plt.show()  # Pouze zobrazení, bez ukládání


def main():
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "MoCaSim Demonstrace s matplotlib grafy" + " " * 16 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    server_results = experiment_server_count()
    renege_results = experiment_reneging_impact()

    print("\n\nVytvářím a zobrazuji grafy pomocí matplotlib...")
    create_matplotlib_visualization(server_results, renege_results)

    print("\nGrafy byly zobrazeny na obrazovce.")
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "Demonstrace dokončena" + " " * 26 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")


if __name__ == "__main__":
    main()
