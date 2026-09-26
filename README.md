# Netzwerksimplex – was ist ein Pivot, und was kostet er? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-netzwerksimplex-demo.streamlit.app/)**

Stück 19 der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", im Min-Cost-Ast neben [ssp-demo](https://github.com/sebastian-hanisch/ssp-demo) (Successive Shortest Paths), [cycle-canceling-demo](https://github.com/sebastian-hanisch/cycle-canceling-demo) und [cost-scaling-demo](https://github.com/sebastian-hanisch/cost-scaling-demo):
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – den **Netzwerksimplex** – an einem wachsenden Beispiel.
Successive Shortest Paths füllt Wege auf, Cycle-Canceling löscht negative Kreise, Cost Scaling verfeinert Schranken. Der Netzwerksimplex hält immer eine **Basis** – einen **Spannbaum** der Knoten – mit **Potenzialen** (Schattenpreisen) und für jede Kante außerhalb des Baums die **reduzierten Kosten**;
eine verletzte Kante tritt ein, schließt mit dem Baumpfad einen **Kreis**, Fluss wandert um den Kreis, bis eine Kante an ihre Schranke stößt, die tritt aus. Jeder **Pivot** ist ein Cycle-Canceling-Schritt, dessen Kreis von den reduzierten Kosten gewählt wird.
Die Demo lässt Sie Pivot für Pivot zusehen und misst, was er kostet: welche **Preisregel** die eintretende Kante wählt, was **Degeneration** bedeutet, wozu die **starke Zulässigkeit** dient, was das **Big-M** der Startbasis kann und was die Potenziale über **Kapazität** verraten.

Die Fall-Demo [network-flow-demo](https://github.com/sebastian-hanisch/network-flow-demo) („Distributionsnetzwerk-Optimierung“) wendet einen eigenen Netzwerksimplex auf ein Distributionsnetz mit Lagerhaltung an (FCFS-Baseline, OR-Tools als Gegenprobe); hier geht es um den Löser selbst. Vehikel: dasselbe Distributionsnetz wie in Stück 4 bis 6 (Werke → Verteilzentren → Filialen), dazu zwei Lehrnetze (Raute mit Rücknahme, Zuordnung mit Einheitskapazität).

**Einordnung in die Reihe (die Kanten des Graphen):** gleiches Modell wie Stück 4 bis 6, neuer Löser (wie Stück 17 zu 16). Kind von Successive Shortest Paths (Gegenprobe und Vergleichsaufwand) und Cycle-Canceling (jeder Pivot löscht einen Fundamentalzyklus); Nachbar von Cost Scaling; die Potenziale sind dieselben Schattenpreise wie in Stück 4.
```
edmonds-karp-demo → dinic-demo → push-relabel-demo (Max-Flow)                            [gebaut]
ssp-demo (Kosten, Potenziale) → cycle-canceling-demo → cost-scaling-demo                 [gebaut]
                                 └─ netzwerksimplex-demo (Basis, Pivot, Schattenpreise)   [dieses Stück]
network-flow-demo (Fall-Demo: derselbe Löser im Distributionsnetz)                       [gebaut]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: Lehrnetze von Hand, Beispielnetze über ihre Seeds, Verteilungen über 40 feste Netze (Seeds ab 100000, dieselben wie in den Flussdemos; die Größenreihe über 5 Netze je Größe). Standard: 3 Werke, 4 Verteilzentren, 12 Filialen (25 Knoten, 54 Kanten), Seed 1, verlangt der größte Fluss (78 Einheiten), Dantzig-Preisregel, starke Austrittsregel.
Alles ist ganzzahlig und deterministisch (eigener Zufallsstrom): Pivotzahlen, Aufwand und Kosten sind auf allen Plattformen dieselben. Aufwand zählt in **Kantenoperationen** (in der Preissuche geprüfte Kanten, Schritte um den Kreis, aktualisierte Knoten des abgetrennten Teilbaums), nie in Sekunden. Die Kopien aus den Vorgängern sind bewacht (`tests/test_copies.py`).

**Der Löser ist richtig.** Über alle Preis- und Austrittsregeln, auf 8 Netzen und mit Teilflusswerten liefert der Netzwerksimplex dieselben Kosten wie Successive Shortest Paths (Standard: 1 131 in 42 Pivots gegen 18 Runden), auf einem Netz auch wie `networkx`; die Optimalitätsbedingung wird unabhängig geprüft.
Nach **jedem** Pivot baut der Test den Baum aus dem Trace neu auf: er spannt alle Knoten, die Potenziale stimmen, der Fluss ist zulässig, und die Kosten sind um genau |c′|·θ gefallen (Kreisschritt); der Fluss bleibt ganzzahlig.

**Degeneration ist der Normalfall.** Im Standardnetz haben 24 von 42 Pivots den Schritt 0, die längste Folge ohne Fortschritt hat 22; über 40 Netze sind es im Mittel 60 % (Dantzig), 53 % (erste verletzte Kante), 57 % (Blocksuche), die längste Folge im Mittel 21,7 / 29,9 / 20,1 (höchstens 23 / 35 / 27). In der Zuordnung 8 × 8 (Einheitskapazität) sind es 23 von 31 (74 %), die längste Folge hat 9. Der Baum wechselt, der Fluss nicht.
**Mehr als die Hälfte der Pivots ist Big-M-Start:** im Mittel über 40 Netze werfen **58 %** der Pivots eine künstliche Kante der Startbasis hinaus (57 % im Standardnetz).

**Die Preisregel ändert den Aufwand, nicht die Kosten – und die Blocksuche gewinnt hier nicht.** Standardnetz: Dantzig 42 Pivots und 3 761 Kantenoperationen, erste verletzte Kante 79 Pivots und **1 658**, Blocksuche 55 Pivots und 1 647. Über 40 Netze (Median): Pivots 42 / 64,5 / 53, Aufwand 3 738 / **1 309** / 1 494; den kleinsten Aufwand hat die erste verletzte Kante in **35 von 40** Netzen, die Blocksuche in 5, Dantzig in keinem.
Dantzig braucht die wenigsten Pivots, prüft aber jedes Mal alle Kanten (im Mittel 90 % des Aufwands sind Preissuche). Im großen Netz (8 Werke, 8 Verteilzentren, 30 Filialen, 56 Knoten, 238 Kanten): Dantzig 113 Pivots und 34 756 Kantenoperationen, Blocksuche 213 und 8 950 (Dantzig fast das Vierfache), erste verletzte Kante 281 und 8 686.

**Aufwand gegen Netzgröße und Successive Shortest Paths.** Mittel über 5 Netze je Größe (12 / 21 / 28 / 44 / 60 / 81 Knoten): Pivots Dantzig 13,2 / 33,8 / 50,2 / 82,2 / 120,4 / 172 (1,6 bis 2,1 je Knoten, leicht steigend), erste verletzte Kante 16 / 52 / 80 / 188 / 307 / 477, Blocksuche 13,8 / 44,4 / 69 / 143 / 240 / 368.
Aufwand der Blocksuche 287 / 1 130 / 2 085 / 5 760 / 11 796 / 21 648 Kantenoperationen gegen 52 / 655 / 1 666 / 6 325 / 16 875 / 36 022 gescannte Kanten bei Successive Shortest Paths (3 / 13 / 21 / 34 / 51 / 67 Runden): **bei kleinen Netzen ist Successive Shortest Paths billiger** (bei 12 Knoten der Netzwerksimplex das 5,5-Fache), ab etwa 44 Knoten kehrt es sich um (bei 81 Knoten 0,60-fach).
Die Einheiten sind verschieden (Kantenoperationen gegen gescannte Kanten); die Reihenfolge, nicht die Faktoren, ist die Aussage.

**Starke Zulässigkeit: eine Garantie, kein Effizienzgewinn.** Mit der Austrittsregel „letzte blockierende Kante in Kreisrichtung ab dem Scheitelpunkt“ (Cunningham) ist die Basis nach **jedem** Pivot stark zulässig (in allen Tests 0 Verletzungen); mit „erste blockierende Kante“ nicht: im Mittel über 40 Netze in 9 / 59 / 43 Pivots (Dantzig / erste / Blocksuche), im Preset „Erste Austrittskante“ in 62 von 75 Pivots.
**Gekreist wurde trotzdem nie:** in keinem der 40 Netze und keiner Preisregel erreicht die erste Austrittskante die Iterationsgrenze. Sie braucht im Mittel 42,1 / 72,8 / 57,4 Pivots gegen 41,9 / 65,0 / 54,0 mit der starken Regel (mehr Pivots in 12 / 32 / 31 Netzen, weniger in 3 / 8 / 7), im Standardnetz mit der ersten verletzten Kante sogar 75 gegen 79. Die Zuordnung 8 × 8: 34 Pivots und 25 ohne starke Zulässigkeit gegen 31 mit.

**Big-M zu klein täuscht ein Optimum vor.** Der sichere Wert ist 1 + n mal größte Kosten (226 im Standardnetz). Bei 2 % davon (M = 4) ist der künstliche Weg billiger als jede echte Lieferung: nach 21 Pivots (alle degeneriert) ist die Basis „optimal“, aber 156 Einheiten laufen über künstliche Kanten, die echten Kosten sind 0 – die Demo erkennt es am künstlichen Fluss. Über 40 Netze ist bei 2 / 5 / 10 % des sicheren Werts in **0 / 21 / 40** Netzen eine zulässige Lösung erreicht.

**Schattenpreise.** Eine volle Kante hat reduzierte Kosten c′ < 0: eine Einheit mehr Kapazität senkt die Kosten um höchstens |c′|. Standardnetz: die größten Werte 14 / 13 / 12 / 11 (F5 → T, F9 → T, F8 → T, DC 1 → F12), alle 8 größten stimmen mit dem Nachrechnen (Kapazität + 1) genau überein. Über 40 Netze: bei **525 von 558** vollen Kanten (94 %) genau, sonst liegt die Ersparnis darunter (die Basis ändert sich, der Schattenpreis gilt nur in einem Bereich); in der Zuordnung z. B. spart die Kante A7 → T rechnerisch 5, nach dem Nachrechnen 1.
**Raute von Hand:** zwei Einheiten S → T kosten 10 (5 Pivots, 3 degeneriert; Successive Shortest Paths 2 Runden mit den Kosten 3 und 7, der zweite nimmt A → B zurück); S → A und B → T sind voll und würden je Einheit Kapazität 2 sparen.

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Bau standen sechs Vermutungen im Plan. Gemessen:

- **„Die Pivotzahl wächst nahezu linear bis n^1,5“ – für Dantzig bestätigt (etwa linear), für die anderen Regeln nicht:** die erste verletzte Kante wächst stärker (5,9 Pivots je Knoten bei 81 Knoten gegen 1,4 bei 12), die Blocksuche dazwischen.
- **„Dantzig hat die wenigsten Pivots, aber den größten Preisaufwand; die Blocksuche gewinnt den Gesamtaufwand“ – halb widerlegt:** Dantzig verliert wie erwartet den Aufwand (in keinem der 40 Netze der billigste), aber **nicht an die Blocksuche, sondern an die erste verletzte Kante** (35 von 40 gegen 5); auch im großen Netz und in allen sechs Größen liegt sie vorn oder gleichauf. Die Blocksuche ist im Netzwerksimplex-Ruf der Standard (LEMON); auf diesen Netzen gewinnt die einfachste Regel, weil die Preissuche den Aufwand dominiert.
- **„Degeneration ist selten auf dem Distributionsnetz, häufig in der Zuordnung“ – widerlegt:** auch das Distributionsnetz hat 53 bis 60 % degenerierte Pivots (Zuordnung 74 %); der Grund liegt vor allem im Big-M-Start (58 % der Pivots werfen künstliche Kanten hinaus, die den Fluss nicht ändern).
- **„Ohne starke Zulässigkeit kreist der Löser oder stagniert“ – widerlegt:** nie die Iterationsgrenze erreicht; die Regel hält die Basis stark zulässig, spart aber keine Pivots (im Mittel etwa 11 % weniger Pivots gegenüber „erste Austrittskante“ bei der ersten verletzten Kante, 6 % bei der Blocksuche, praktisch keine bei Dantzig). Der Beweis, dass ohne sie Kreisen möglich ist, ist Theorie (Cunningham 1976); auf diesen Netzen zeigt sich kein Fall.
- **„Der Schattenpreis stimmt beim Nachrechnen mit +1 Kapazität“ – in 94 % der Fälle, sonst nicht:** der Wert gilt nur, solange die Basis optimal bleibt.
- **„Jeder Pivot senkt die Kosten um |c′|·θ exakt“ und „ganzzahlig“ – bestätigt** (in jedem Pivot getestet).
- **Abweichung vom Plan:** die Blockgröße ist kein Regler (fest Wurzel der Kantenzahl); die Zuordnung ist auf 8 × 8 festgelegt.

## Was die Demo zeigt

- **Pivot für Pivot:** Regler und Abspielen; Karte mit der Basis vor dem Pivot (Baumkanten, volle und leere Kanten, Potenziale), eintretende Kante grün, austretende rot gestrichelt, Kreis blau; Kostenverlauf mit den degenerierten Pivots; die verletzten Kanten vor dem Pivot.
- **Preisregeln im Vergleich:** Pivots und Aufwand nach Preissuche, Kreis und Update.
- **Degeneration:** Anteil, längste Folge, Austrittsregeln gegeneinander mit der Zahl der Pivots ohne starke Zulässigkeit.
- **Schattenpreise:** die größten Werte einer weiteren Einheit Kapazität mit Nachrechnen.
- **Experimente (auf Abruf):** Aufwand gegen Netzgröße mit Successive Shortest Paths; 40 Netze (Pivots, Aufwand, Degeneration, Austrittsregel, Big-M-Schwelle).
- **Wo die Annahmen enden:** eine Ware, ganzzahlig, Baum ohne Thread-Index, Aufwandseinheit, Big-M als Start, ein generiertes Netz.

## Modell und Verfahren

- **Modell:** Min-Cost-Flow $\min\sum c_ex_e$ mit Bilanz $b_v$ ($b_S=F$, $b_T=-F$) und $0\le x_e\le u_e$.
- **Basis:** Spannbaum (mit künstlicher Wurzel), Potenziale $\pi_v=\pi_u+c_{uv}$ auf Baumkanten, reduzierte Kosten $\bar c_{uv}=c_{uv}+\pi_u-\pi_v$; optimal, wenn $\bar c\ge0$ an der unteren und $\bar c\le0$ an der oberen Schranke.
- **Pivot:** eintretende Kante (Preisregel: Dantzig, erste verletzte, Blocksuche), Kreis mit dem Baumpfad, Schritt $\theta$, austretende blockierende Kante (stark zulässig: die letzte in Kreisrichtung ab dem Scheitelpunkt), Kosten $-|\bar c|\,\theta$; nur der abgetrennte Teilbaum bekommt neue Tiefen und Potenziale.
- **Start:** künstliche Wurzel und künstliche Kanten mit Kosten $M$ (Big-M); $M$ zu klein lässt künstlichen Fluss übrig.

## Ehrliche Grenzen

- **Eine Ware:** mit mehreren Gütern gibt es keine Baumbasis (siehe Mehrgüterfluss); Bündel-Simplex nur erwähnt.
- **Ganzzahlige Daten:** der Fluss bleibt ganzzahlig; mit gebrochenen Daten rechnet die Fall-Demo mit Toleranz.
- **Baum ohne Thread-Index:** Tiefen und Elternzeiger genügen; industrielle Implementierungen halten Thread und Nachfolger für schnellere Updates.
- **Aufwand in Kantenoperationen:** eine Zählung, keine Uhr; gleiche Gewichte für Preissuche, Kreis und Update.
- **Big-M als Start:** Zwei-Phasen-Methode und Startbasis aus einem Vorlösungsfluss sind nur erwähnt.
- **Synthetische Daten:** ein geschichtetes Distributionsnetz mit erzeugten Kapazitäten und Kosten, keine Fremddaten.

## Bewusst nicht umgesetzt

- Thread-Index, Zwei-Phasen-Start, Vorlösungs-Startbasis, Skalierung und Präprozessing, Bündel-Simplex für Mehrgüterfluss, stetige Kosten.

## Dateien

```
app.py                  Oberfläche (Streamlit)
nsx_scenario.py         Distributionsnetz, Lehrnetze, Zufallsgenerator (Kopie aus ssp-demo)
nsx_edmonds_karp.py     Restgraph-Grundlagen und Max-Flow (Kopie aus ssp-demo)
nsx_ssp.py              Successive Shortest Paths (Kopie aus ssp-demo, Gegenprobe)
nsx_simplex.py          Basis, Preisregeln, Pivot, Trace, Zertifikat
nsx_evaluation.py       Analyse, Preisregeln, Austrittsregeln, Schattenpreise, Größen, Verteilungen
nsx_visualization.py    Plotly-Abbildungen
nsx_presets.py          Permalink, Presets, Zufalls-Seed
nsx_constants.py        Konstanten, Regler-Grenzen, feste Seed-Mengen, Preset-Texte
tests/                  Kopien, Kern, Auswertung, Presets, Behauptungen, App, Regler-Zustand
```

## Lokal starten

```bash
python -m venv venv
venv/Scripts/pip install -r requirements.txt
venv/Scripts/streamlit run app.py
```

## Tests ausführen

```bash
venv/Scripts/pip install -r requirements-dev.txt
venv/Scripts/python -m pytest tests/ -v
```

Gebaut mit Streamlit und Plotly; der Kern ist reines Python (Tests vergleichen zusätzlich mit `networkx`).
