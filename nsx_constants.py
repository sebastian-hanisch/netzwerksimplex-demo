"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Netzwerksimplex: was ist ein Pivot, und was kostet er?"."""

# --- Regler ---------------------------------------------------------------------------------------------------------------------
PLANTS_MIN, PLANTS_MAX, DEFAULT_PLANTS = 2, 8, 3
DCS_MIN, DCS_MAX, DEFAULT_DCS = 2, 8, 4
STORES_MIN, STORES_MAX, DEFAULT_STORES = 4, 30, 12
FLOW_MIN, FLOW_MAX, DEFAULT_FLOW = 10, 100, 100         # Flusswert in Prozent des maximalen Flusses (Schritt 10)
DEFAULT_SEED = 1
SEED_MAX = 2_000_000_000
DENSITY, SPREAD, LOAD = 60, 50, 100                    # feste Netzparameter (wie in den Vorgängern: Lane-Dichte, Streuung der Kapazitäten, Gesamtnachfrage in % der Werkskapazität)

NETS = {
    "distribution": "Distributionsnetz (Werke, Verteilzentren, Filialen)",
    "diamond": "Raute mit Rücknahme (kleines Lehrnetz)",
    "assignment": "Zuordnung 8 × 8 (Einheitskapazität, stark degeneriert)",
}
DEFAULT_NET = "distribution"
FIXED_NETS = ("diamond", "assignment")
ASSIGNMENT_N = 8
PRICING = {"dantzig": "Dantzig (alle Kanten prüfen, größte Verletzung)", "first": "Erste verletzte Kante (zyklisch weitersuchen)", "block": "Blocksuche (Blöcke von etwa Wurzel(m) Kanten)"}
DEFAULT_PRICING = "dantzig"
LEAVING = {"strong": "Stark zulässig (letzte blockierende Kante, Cunningham)", "first": "Erste blockierende Kante"}
DEFAULT_LEAVING = "strong"
BIG_M_PCTS = (2, 5, 10, 25, 100)                         # M in Prozent des sicheren Werts 1 + n mal größte Kosten
DEFAULT_BIG_M = 100

# --- feste Seed-Mengen (dieselben wie in den Flussdemos; unabhängig vom Nutzer-Seed) ---------------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
SIZE_SEEDS = DIST_SEEDS[:5]
SIZES = ((2, 2, 4), (3, 4, 8), (4, 5, 12), (6, 8, 20), (8, 10, 30), (10, 12, 45))     # (Werke, Verteilzentren, Filialen)

COLORS = {"dantzig": "#1f77b4", "first": "#2ca02c", "block": "#ff7f0e", "ssp": "#7f7f7f", "tree": "#111111", "enter": "#2ca02c", "leave": "#d62728", "cycle": "#1f77b4", "upper": "#ff7f0e", "lower": "rgba(150,150,150,0.45)"}
LABELS = {"dantzig": "Dantzig", "first": "Erste verletzte Kante", "block": "Blocksuche", "ssp": "Successive Shortest Paths"}

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net=DEFAULT_NET, plants=DEFAULT_PLANTS, dcs=DEFAULT_DCS, stores=DEFAULT_STORES, flow=DEFAULT_FLOW, pricing=DEFAULT_PRICING, leaving=DEFAULT_LEAVING, big_m=DEFAULT_BIG_M, seed=DEFAULT_SEED)
PRESETS = {
    "🚚 Distributionsnetz": {**_BASE},
    "💎 Raute": {**_BASE, "net": "diamond"},
    "🧩 Zuordnung": {**_BASE, "net": "assignment"},
    "🔀 Erste verletzte Kante": {**_BASE, "pricing": "first"},
    "🧱 Blocksuche": {**_BASE, "pricing": "block"},
    "↩️ Erste Austrittskante": {**_BASE, "pricing": "first", "leaving": "first"},
    "⚠️ Big-M zu klein": {**_BASE, "big_m": 2},
    "🏭 Großes Netz": {**_BASE, "plants": 8, "dcs": 8, "stores": 30, "pricing": "block"},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py belegt (Lehrnetze von Hand, Distributionsnetz über die Seeds der Presets)
PRESET_HELP = {
    "🚚 Distributionsnetz": "3 Werke, 4 Verteilzentren, 12 Filialen: 25 Knoten, 54 Kanten, verlangt sind 78 Einheiten (der größte Fluss). Dantzig braucht 42 Pivots, davon 24 degeneriert, die längste Folge ohne Fortschritt hat 22; die Kosten 1 131 stimmen mit Successive Shortest Paths überein (18 Runden, 1 146 gescannte Kanten), der Netzwerksimplex zählt 3 761 Kantenoperationen. 57 % der Pivots werfen künstliche Kanten der Startbasis hinaus.",
    "💎 Raute": "Vier Knoten, fünf Kanten, zwei Einheiten von S nach T: Kosten 10. Der Netzwerksimplex braucht 5 Pivots (3 davon degeneriert), Successive Shortest Paths 2 Runden (Wege der Kosten 3 und 7; der zweite nimmt A → B zurück). S → A und B → T sind voll: eine weitere Einheit Kapazität auf einer von beiden spart 2.",
    "🧩 Zuordnung": "8 Fahrzeuge, 8 Aufträge, jede Kante Kapazität 1: 18 Knoten, 80 Kanten, Kosten 15. 31 Pivots, 23 davon degeneriert (74 %), die längste Folge hat 9. Ohne die starke Austrittsregel hätte die Basis nach 25 Pivots nicht mehr die starke Zulässigkeit, und es wären 34 Pivots. Successive Shortest Paths braucht 8 Runden, eine je Einheit.",
    "🔀 Erste verletzte Kante": "Die Preissuche hört bei der ersten verletzten Kante auf: 79 statt 42 Pivots, aber nur 1 658 statt 3 761 Kantenoperationen, weil jede Preissuche kurz ist. Kosten 1 131.",
    "🧱 Blocksuche": "Blöcke von etwa Wurzel(m) Kanten, die beste des ersten Blocks mit einer verletzten Kante tritt ein: 55 Pivots und 1 647 Kantenoperationen: bei den Pivots zwischen Dantzig (42) und der ersten verletzten Kante (79), bei den Kantenoperationen mit 1 647 knapp unter der ersten verletzten Kante (1 658) und weit unter Dantzig (3 761).",
    "↩️ Erste Austrittskante": "Erste verletzte Kante als Preisregel und die erste blockierende Kante als Austrittsregel: 75 Pivots, aber nach 62 davon ist die Basis nicht mehr stark zulässig. Kreisen tritt trotzdem nicht auf, und die starke Regel braucht mit 79 sogar mehr Pivots: sie ist eine Garantie, kein Effizienzgewinn.",
    "⚠️ Big-M zu klein": "M = 4 statt 226: der künstliche Weg ist billiger als jede echte Lieferung. Nach 21 Pivots (alle degeneriert) ist die Basis „optimal“, aber 156 Einheiten laufen über künstliche Kanten, die echten Kosten sind 0 und nichts wird geliefert. Die Demo erkennt es am künstlichen Fluss und meldet das Netz als unzulässig.",
    "🏭 Großes Netz": "8 Werke, 8 Verteilzentren, 30 Filialen: 56 Knoten, 238 Kanten, 204 Einheiten. Blocksuche: 213 Pivots, 8 950 Kantenoperationen; Dantzig braucht nur 113 Pivots, aber 34 756 Kantenoperationen, fast das Vierfache; Successive Shortest Paths scannt 12 171 Kanten in 43 Runden.",
}
