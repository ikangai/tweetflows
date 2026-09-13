# Selektive Agentenvermittlung bei unvollständiger Fähigkeitssicht und wechselnder Verfügbarkeit

## Kurzfassung

Die geplante Arbeit untersucht, wann erfahrungsbasierte Empfehlungen zwischen LLM-Agenten die Bearbeitung von Werkzeugaufgaben verbessern. Ausgangspunkt ist eine während der Ausführung entstehende Suche nach geeigneten Spezialisten. Verglichen werden zentrale aktive Suche, intentbasierte Vermittlung und begrenzte mehrstufige Empfehlungen bei identischen Fähigkeiten, Informationszugängen und Gesamtbudgets. Eine gemeinsame Laufzeit kontrolliert Vergabe, Wiederholung und Ergebnisabnahme. Primäre Zielgröße ist der unabhängig geprüfte Aufgabenerfolg innerhalb des Budgets. Der angestrebte Beitrag ist eine reproduzierbare empirische Bestimmung der Bedingungen, unter denen Vermittlung ihre Such-, Kommunikations- und Prüfkosten rechtfertigt. Das Exposé beschreibt eine geplante Studie; es liegen noch keine eigenen Versuchsergebnisse vor.

## 1. Problemstellung und Motivation

Agentendienste können über unterschiedliche Werkzeuge, Datenzugänge und Erfahrungen verfügen. In einem offenen oder organisatorisch verteilten Umfeld ist die Menge geeigneter Ausführender jedoch nicht notwendigerweise vollständig bekannt. Zusätzlich kann sich ihre Verfügbarkeit während einer Aufgabe ändern. Eine fachlich passende Empfehlung kann daher nutzlos sein, wenn der empfohlene Dienst zu spät antwortet oder die benötigte Leistung nicht zuverlässig erbringt.

Tweetflows motiviert die Verbindung von kurzen Auftragsnachrichten, sozialer Vermittlung und während der Arbeit erweiterbaren Abläufen. Die neue Untersuchung übernimmt diese Problemidee und richtet sie auf tatsächlich unterschiedliche Fähigkeiten von LLM-Agenten aus.[^1] Der praktische Zielbereich sind beispielsweise interne Agentendienste verschiedener Teams, deren lokale Werkzeuge und Zuständigkeiten nur teilweise zentral dokumentiert sind.

Für diese Umgebungen soll geklärt werden, ob lokale Erfahrungen die Suche und Auswahl verbessern oder ob eine zentrale Erfassung derselben Informationen günstiger ist. Die zusätzliche Kommunikation wird als Teil der Gesamtkosten erfasst. Ein Vorteil darf weder auf einem größeren Modellbudget noch auf exklusiven Werkzeugrechten oder einer besseren Ausführungsinfrastruktur beruhen.

## 2. Forschungsstand und Abgrenzung

Aufgabenvergabe durch Ankündigung, Angebot und Zuschlag ist durch Contract Net und FIPA etabliert. Referral Networks unterscheiden bereits fachliche Kompetenz von der Fähigkeit, geeignete Dienstleister zu empfehlen. Diese Konzepte bilden die algorithmische Grundlage; ihre Verwendung ist kein eigenständiger Neuheitsanspruch.[^2][^3][^4]

Für LLM-Systeme sind RAPS mit reputationsgestütztem Publish/Subscribe und AgentNet mit dezentraler erfahrungsbasierter Auswahl unmittelbare Bezugspunkte. Beide müssen bei der Wahl der Vergleichsverfahren berücksichtigt werden.[^5][^6] *Usable Agent Discovery* untersucht bereits Verfügbarkeit und Host-Ausfälle in einer Simulationsumgebung. Die vorgeschlagene Studie ergänzt die Frage nach einem auffindbaren Dienst um unabhängig geprüfte, tatsächlich ausgeführte LLM-Werkzeugaufgaben.[^7]

Die Forschung zu Agentenevaluation begründet Kostenkontrolle, einfache Vergleichssysteme und unabhängige Testdaten. Architekturvorteile sind aufgabenabhängig; Prüferrollen können selbst fehlerhafte Entscheidungen treffen.[^8][^9][^10][^11] Eine Forschungslücke wird deshalb in der kontrollierten gemeinsamen Untersuchung von partieller Fähigkeitssicht, zeitlicher Unverfügbarkeit und vollständigem Aufgabenerfolg gesehen. Dies ist eine begrenzte Anschlussfrage innerhalb der geprüften Literatur, keine Behauptung weltweiter Erstmaligkeit.

Als Beitrag werden weder ein neues allgemeines Agentenprotokoll noch ein neuartiger Reputationsbegriff beansprucht. Verpflichtungssemantik, Laufzeitdurchsetzung und dauerhafter Autorisierungszustand besitzen eigene Vorarbeiten. Sie werden für eine gemeinsame Versuchsgrundlage genutzt.[^12][^13][^14]

## 3. Forschungsfragen und Hypothesen

**F1 – Aufgabenerfolg:** Wie verändert erfahrungsbasierte, begrenzte Vermittlung den unabhängig geprüften Erfolg innerhalb eines festen Gesamtbudgets gegenüber zentraler aktiver Suche und intentbasierter Vermittlung?

**F2 – Informations- und Verfügbarkeitsbedingungen:** Wie hängen diese Unterschiede davon ab, ob Fähigkeiten zunächst vollständig oder teilweise sichtbar und die benötigten Agenten stabil oder zeitlich wechselnd verfügbar sind?

**F3 – Ursache eines möglichen Vorteils:** Welchen Anteil haben verwertbare Vermittlungserfahrung und geringerer Suchaufwand, und wie stark wird ein Vorteil durch Fehlvermittlung, Wiederholung und interne Prüfung aufgezehrt?

| Hypothese | Vorab festzulegender Vergleich |
|---|---|
| H1 | Bei partieller Fähigkeitssicht, später sichtbar werdendem Bedarf und zeitlich wechselnder Verfügbarkeit erzielt selektive Vermittlung innerhalb desselben Budgets eine höhere Erfolgsrate als zentrale aktive Suche. |
| H2 | Der relative Vorteil selektiver Vermittlung fällt bei partieller Sicht größer aus als bei vollständiger Sicht. |
| H3 | Verwertbare Vermittlungserfahrung senkt gegenüber permutierten Erfahrungswerten den Aufwand bis zur geeigneten Übernahme. Ob dies den Enderfolg verbessert, wird getrennt gemessen. |

H1 ist der primäre gerichtete Forschungsanspruch. Berichtet wird trotzdem ein zweiseitiges Unsicherheitsintervall, damit auch eine Verschlechterung sichtbar wird. Der Vergleich mit der intentbasierten Variante ist ein vorab definierter sekundärer Kontrast. H2 und H3 benötigen ausreichend Daten für Interaktions- beziehungsweise Ablationsanalysen; andernfalls werden sie ausdrücklich explorativ behandelt. Ein nichtsignifikanter Befund gilt nicht als Nachweis gleicher Leistung.

## 4. Untersuchungsmodell und Prototyp

Ein Agent wird als Kombination aus Basismodell, Werkzeug- oder Datenzugriff und lokalem Beobachtungsverlauf definiert. Im Hauptversuch verwenden alle Agenten dasselbe Basismodell. Ihre Spezialisierung beruht auf kontrolliert unterschiedlichen Zugriffsmöglichkeiten. Ein Pool von zunächst acht Agenten hält den Prototyp überschaubar; andere Poolgrößen gehören in eine spätere Sensitivitätsanalyse.

Eine Aufgabe enthält Ziel, Eingabeversion, zulässige Aktionen, Abnahmekriterien, Kostenbudget und Frist. Neue Teilaufgaben dürfen nur innerhalb dieses Vertrags erzeugt werden. Aufgabenidentität und Ausführungsversuch werden getrennt verwaltet. Nach Ausfall oder Neuvergabe werden veraltete Ergebnisse abgewiesen; mehrere Rechenversuche können dennoch zeitweise parallel bestehen.

Die gemeinsame Laufzeit übernimmt atomare Vergabe, Budgetreservierung, Nachrichtendeduplizierung und die Prüfung aktueller Schreibberechtigung. Diese Regeln gelten für alle Verfahren. Der Kernversuch verwendet eine kontrollierte Sandbox mit vermittelten Seiteneffekten. Aussagen über genau einmalige Wirkungen in beliebigen externen Anwendungen oder vollständige infrastrukturelle Dezentralität werden dadurch nicht begründet.

Die Vermittlungsstrategie speichert fachlichen Erfolg und erfolgreiche Empfehlungen getrennt. Sie bewertet bekannte Kandidaten nach Aufgabenpassung, Erfahrung, Aktualität und erwartetem Suchaufwand. Pro Schritt werden höchstens zwei Kontakte angesprochen; höchstens drei Vermittlungsschritte sind als Ausgangskonfiguration vorgesehen. Beide Grenzen werden im Pilot ausschließlich auf Entwicklungsaufgaben geprüft und anschließend fixiert. Eine erfolglose Suche darf das gemeinsame Budget nicht durch neue Aufgaben- oder Nachrichtenkennungen zurücksetzen.

Fachliches Scheitern, eine nicht hilfreiche Empfehlung und momentane Unverfügbarkeit erzeugen unterschiedliche Rückmeldungen. Die Hauptstudie startet mit einer für alle Verfahren identischen, auf getrennten Entwicklungsaufgaben gewonnenen Vorgeschichte. Online-Lernen ist zunächst deaktiviert; es wird später als eigener Faktor untersucht. Damit werden unterschiedliche Lerngelegenheiten nicht mit Routingvorteilen verwechselt.

## 5. Experimentelles Design

### 5.1 Aufgaben und Informationsbedingungen

WorkBench ist die bevorzugte Ausgangsumgebung, weil Änderungen des Datenbankzustands eine überprüfbare Zielerreichung erlauben. Falls der Pilot starke Sättigung oder unzureichende Vermittlungsrelevanz zeigt, wird vor der Hauptstudie auf AppWorld gewechselt. Beide Umgebungen gleichzeitig vollständig zu erweitern ist für das erste Paper nicht vorgesehen.[^15][^16]

Ausgewählt werden zwei Aufgabenfamilien: Aufgaben mit vorab erkennbarem Fähigkeitsbedarf und Aufgaben, bei denen ein erster Werkzeugschritt einen zusätzlichen Bedarf offenlegt. Ein Beispiel der zweiten Familie wäre eine Aktualisierung, für die erst nach der Datenabfrage eine notwendige Formatumwandlung erkennbar wird. Die korrekte Umwandlung und die erlaubten Änderungen werden durch den verborgenen Evaluator geprüft. Veränderte Aufgaben werden als Erweiterungen des Ausgangsbenchmarks ausgewiesen.

Alle Verfahren kennen im Vollsichtfall zunächst sämtliche Agentenprofile. Im Fall partieller Sicht kennen sie denselben kleinen Einstiegssatz, als Startwert zwei von acht Profilen. Weitere Profile werden über identische Funktionen zum Abruf bekannter Profile, zur Anfrage erreichbarer Kontakte und zur Prüfung der Verfügbarkeit erschlossen. Kein Verfahren erhält einen kostenlosen vollständigen Index. Eine zentrale Strategie darf eingehende Informationen zentral sammeln und darauf semantische Suche anwenden; alle dafür entstehenden Kommunikations- und Verarbeitungskosten werden erfasst.

Damit werden Entdeckbarkeit und Kenntnis getrennt: Ein noch unbekannter Spezialist kann über erlaubte Kontakte erreichbar sein. Die Kontaktgraphen werden unabhängig vom untersuchten Verfahren erzeugt. Fachlich informative Beziehungen und zufällig permutierte Beziehungen bilden unterschiedliche Diagnosebedingungen. Ein nicht erreichbarer Spezialist ist ein dokumentierter Umgebungsfall und kein vermeidbarer Routingfehler.

Für wechselnde Verfügbarkeit werden vorab erzeugte Ein- und Austrittsereignisse auf einer gemeinsamen Simulationszeit verwendet. Alle Verfahren erhalten pro Aufgabe dieselbe Ereignisfolge, aber keine Vorschau darauf. Zusätzlich wird ein Ausfall direkt nach Vergabe als separater, ereignisbezogener Stresstest durchgeführt. Er wird nicht mit dem exogenen Verfügbarkeitsversuch vermischt. Eine Änderung der Eingabeversion und eine verspätete Ergebnisnachricht gehören in günstige Tests der Laufzeit mit deterministischen Testagenten.

### 5.2 Hauptverfahren und Vergleichsgrenzen

| Verfahren | Rolle im Vergleich |
|---|---|
| Zentrale aktive Suche | Ein Koordinator erweitert den bekannten Kandidatenbestand und wählt daraus einen verfügbaren Spezialisten. Gleiche Worker, Anfangsinformation und Zugriffsrechte wie die anderen Verfahren. |
| Intentbasierte Vermittlung | Dokumentierte RAPS-inspirierte Variante mit Subscriptions aus dem tatsächlich entdeckten Kandidatenbestand und denselben Möglichkeiten zur Kontaktabfrage. |
| Selektive Empfehlungen | Kostenbegrenzte mehrstufige Vermittlung mit getrennten Erfahrungen zu Fach- und Vermittlungserfolg. |

Die intentbasierte Variante ist eine Adaption und darf nicht als originalgetreue RAPS-Replikation bezeichnet werden. Ihre Kandidatenentdeckung darf nicht künstlich deaktiviert sein. Der Adapter und sämtliche Abweichungen werden veröffentlicht. Eine kleine originalgetreue Referenz unter vollständiger Sicht und ein AgentNet-Vergleich werden ergänzt, soweit die jeweilige Implementierung reproduzierbar verfügbar ist. Fehlt diese Grundlage, wird die Reproduktionsgrenze ausdrücklich benannt; ein erfundenes Referenzergebnis ist ausgeschlossen.

Für einen gezielten Diagnoseteil werden begrenzter Broadcast, zufällige Weiterleitung mit gleichem Kontaktbudget und eine Variante ohne Erfahrungswerte genutzt. Ein Einzelagent mit Zugriff auf die Vereinigungsmenge der Werkzeuge misst, ob die Aufgabe überhaupt von verteilten Ausführenden profitiert. Wo diese Rechtevereinigung eine organisatorische Grenze aufhebt, ist er eine privilegierte Referenz; der faire zentrale Hauptvergleich behält dieselben getrennten Spezialisten.

Alle Hauptverfahren nutzen dasselbe Vergabeprotokoll und dieselbe Abnahme. Eine Contract-Net-Auswahlrunde kann eine ergänzende Vergabekontrolle bilden, falls die Auswahl zwischen mehreren Angeboten selbst relevant wird. Sie wird nicht gleichzeitig mit dem Router gewechselt. Ebenso bleiben erlaubte Parallelität, Modellversion, Workerprompts, Werkzeugzustände und Retry-Grenzen kontrolliert.

### 5.3 Zielgrößen und Kosten

Die primäre Zielgröße ist die Erfolgsrate über alle begonnenen Versuche: Der Endzustand erfüllt die verborgenen Zieltests und enthält keine unzulässigen zusätzlichen Änderungen; Budget und Frist wurden eingehalten. Fehler, Zeitüberschreitungen und erfolglose Suchen bleiben im Nenner. Teilfortschritt wird ergänzend berichtet, ersetzt aber nicht den Primärscore.

Für das Gesamtbudget zählen sämtliche Modellaufrufe zur Suche, Profilbewertung, Vermittlung, Ausführung, internen Prüfung, Wiederholung und Zusammenführung. Werkzeugaufrufe, Embeddings, Initialisierung und Pflege von Profilen werden ebenfalls erfasst. Tatsächliche Eingabe-, Ausgabe- und gegebenenfalls separat ausgewiesene Reasoning-Tokens werden dokumentiert. Das Kostenmodell wird vor dem Hauptlauf festgeschrieben; Preisänderungen werden durch zusätzliche Mengenangaben nachvollziehbar.[^17]

Der verborgene wissenschaftliche Evaluator wird nach dem Lauf eingesetzt und ist keinem Agenten zugänglich. Sein Aufwand wird separat ausgewiesen. Ein betrieblicher Prüfer hingegen darf Hinweise während der Ausführung geben und gehört zum Systembudget. Seine falschen Akzeptanzen und Ablehnungen werden gegen den unabhängigen Evaluator gemessen. Zur Validierung der Tests dienen absichtlich leere, unvollständige und fehlerhafte Ergebnisse sowie manuell geprüfte Kontrollfälle.[^18]

Weitere Zielgrößen sind Zeit und Kosten bis zur geeigneten Übernahme, Anzahl kontaktierter Teilnehmer, wiederholte Arbeit nach Ausfall und fälschlich angenommene veraltete Ergebnisse. Verfahrensinterne Fehlermeldungen und eine kleine verblindet annotierte Stichprobe ergänzen die Diagnose. Protokollinvarianten werden getrennt von der inhaltlichen Qualität ausgewertet.

## 6. Fallzahlplanung und Auswertung

Der Entwicklungspilot umfasst etwa 30–50 unabhängige Aufgabenfamilien. Er dient der Prüfung von Schwierigkeit, Informationsbedingungen, Budgetverbrauch und Testvalidität. Danach werden primärer Kontrast, Mindestgröße eines relevanten Effekts, Budget und Hauptfallzahl festgelegt. Die Daten des Piloten gehen nicht in den bestätigenden Test ein.

Als Planungsumfang werden zunächst ungefähr 200 zurückgehaltene Aufgaben mit drei Verfahren und drei Wiederholungen angesetzt, also 1.800 Hauptläufe bei einem Modell. Diese Hauptläufe konzentrieren sich auf die H1-Bedingung: partielle Sicht, später erkennbarer Bedarf und zeitlich wechselnde Verfügbarkeit. Die Zahl wird nicht nochmals mit allen Informations- und Verfügbarkeitsbedingungen multipliziert.

Ein vorab festgelegter Diagnoseteil von beispielsweise 40 Aufgaben erhält zusätzlich die drei anderen Kombinationen aus Sicht und Verfügbarkeit. Drei Verfahren und zwei Wiederholungen ergeben dafür 720 zusätzliche Läufe. Dieser gepaarte Diagnoseteil untersucht H2; er ersetzt keine gesonderte Fallzahlplanung für kleine Interaktionseffekte. Aufgaben mit vorab bekanntem Bedarf und die H3-Ablation werden auf begrenzten, ebenfalls vorab bestimmten Teilmengen geprüft. Alle zusätzlichen Läufe werden separat budgetiert.

Die endgültige Fallzahl folgt einer pilotgestützten Poweranalyse mit gepaarten binären Ergebnissen und Vorlagenkorrelation. Wiederholungen derselben Aufgabe erzeugen keine zusätzlichen unabhängigen Aufgaben. Ist die erforderliche Fallzahl finanziell nicht erreichbar, wird vor dem Hauptlauf der wissenschaftliche Anspruch auf eine Schätzung mit entsprechend breiteren Unsicherheitsintervallen begrenzt. Sekundäre Interaktionen bleiben explorativ; die Schwelle für eine positive Aussage wird nicht nachträglich abgesenkt.

Berichtet werden gepaarte Differenzen der Erfolgsraten mit 95-Prozent-Konfidenzintervallen und Kosten-Erfolgs-Darstellungen. Das Resampling erfolgt auf Aufgaben- beziehungsweise Vorlagenebene. Vorab definierte sekundäre Vergleiche werden nach Holm korrigiert. Ein gemischtes logistisches Modell kann die deskriptive Regimeanalyse ergänzen, wenn genügend unabhängige Aufgabenfamilien vorhanden sind. Eine kleine Replikation des primären Vergleichs mit einem zweiten Modell prüft dessen Robustheit.

## 7. Ressourcen und Arbeitsplan

Die Planung nimmt eine hauptverantwortliche forschende Person mit regelmäßigem methodischem Feedback und Zugriff auf eine Sandbox sowie Modellinferenz an. Die Mittel werden nach dem Pilot kalkuliert. Bei 1.800 Hauptläufen entsprechen rein hypothetische mittlere Laufkosten von 0,25, 1 oder 3 Euro einem Hauptlaufbudget von 450, 1.800 oder 5.400 Euro. Dies sind Rechenszenarien, keine recherchierten Anbieterpreise oder gemessenen Kosten. Pilot, Implementierung, Diagnostik und Replikation kommen hinzu.

| Zeitraum | Arbeitspaket und überprüfbares Ergebnis |
|---|---|
| Wochen 1–2 | Aufgaben auswählen, Informationsmodell und Referenzimplementierungen prüfen; Eingrenzung des Beitrags und ausführbare Ausgangsbaseline. |
| Wochen 3–4 | Gemeinsame Laufzeit, drei Router und Messung integrieren; getestete Übergänge und reproduzierbare Ereignisspuren. |
| Wochen 5–6 | Pilot, Testaudit, Kosten- und Fallzahlplanung; eingefrorene Hauptkonfiguration und dokumentierter Analyseplan. |
| Wochen 7–8 | Hauptversuche und festgelegte Diagnostik; vollständige Ereignis- und Kostenprotokolle. |
| Wochen 9–10 | Statistische Auswertung, Fehleranalyse und begrenzte Modellreplikation. |
| Wochen 11–12 | Manuskript, Reproduktionspaket und erneute Aktualisierung der engsten Vorarbeiten vor Einreichung. |

Der Zeitplan ist ein Arbeitsrahmen und hängt von Reproduzierbarkeit der Vergleichssysteme und nötiger Fallzahl ab. Eine Journalausweitung könnte eine zweite Umgebung oder längerfristiges Online-Lernen hinzufügen. Diese Erweiterungen sind keine Voraussetzung für den ersten, begrenzten Konferenzbeitrag.

## 8. Erwarteter Beitrag und Validitätsgrenzen

Erwartet werden drei wissenschaftliche Ergebnisse: ein explizites Modell des Informationszugangs bei Agentenvermittlung, ein reproduzierbarer Vergleich bekannter Vermittlungsprinzipien unter gemeinsamer Laufzeit und eine empirische Beschreibung ihres Nutzens und ihrer Grenzen. Ein negativer oder nur auf bestimmte Bedingungen begrenzter Befund ist ein zulässiges Ergebnis. Als positive Schlussfolgerung käme ausschließlich die Überlegenheit in den tatsächlich getesteten Bedingungen infrage.

Die größten Risiken sind künstlich hilfreiche Kontaktgraphen, unterschiedlich verteilte Werkzeuginformationen, fehlerhafte Abnahmetests und ein zu schwacher zentraler Vergleich. Dagegen stehen permutierte Graphen, ein protokollierter Informationszugang, Testkontrollen und eine sorgfältig entwickelte zentrale Baseline. Auswahlverzerrungen in Erfahrungsdaten werden durch gemeinsame Vorgeschichte und getrennte Entwicklungs- und Testaufgaben begrenzt.

Der Prototyp verwendet synthetische oder rechtmäßig bereitgestellte Sandboxdaten. Es werden keine produktiven Konten verändert und keine reale externe Kommunikation ausgelöst. Menschliche Zusammenarbeit, strategische Täuschung, wirtschaftliche Anreize und umfassende Sicherheitsgarantien bleiben außerhalb der Hauptstudie. Eine spätere Publikation muss ihre Aussagen entsprechend auf die untersuchten Agenten, Aufgaben und Informationsbedingungen begrenzen.

## 9. Geplante Struktur des Papers

Das Manuskript führt zunächst das Problem partieller Fähigkeitssicht anhand einer konkreten Werkzeugaufgabe ein. Es ordnet die Arbeit in Referral Networks, RAPS, AgentNet und Discovery unter wechselnder Verfügbarkeit ein. Danach folgen Informations- und Ausführungsmodell, die drei Auswahlverfahren, Evaluation mit vorab festgelegten Kontrasten, Ergebnisse und Fehleranalyse sowie Grenzen und Reproduzierbarkeit. Code, Konfigurationen, Ereignisspuren und die Zuordnung aller berichteten Zahlen zu Läufen sollen das Paper als begleitendes Forschungsartefakt ergänzen.

## Literatur und Quellen

Quellenstand: 13. September 2026. Die Nummern entsprechen den Fußnoten.

1. Martin Treiber, Daniel Schall, Schahram Dustdar und Christian Scherling (2011). [Tweetflows – Flexible Workflows with Twitter](https://dsg.tuwien.ac.at/team/dschall/papers/2011_tweetflows.pdf). PESOS ’11, S. 1–7. **Status:** Veröffentlichter Workshopbeitrag. Originalfassung als Autoren-PDF.

2. Reid G. Smith (1980). [The Contract Net Protocol: High-Level Communication and Control in a Distributed Problem Solver](https://cse-robotics.engr.tamu.edu/dshell/cs631/papers/smith80contract.pdf). IEEE Transactions on Computers, C-29(12), 1104–1113. **Status:** Begutachteter Zeitschriftenartikel. Originalartikel in universitärer Kopie.

3. Foundation for Intelligent Physical Agents, TC Communication (2002). [FIPA Contract Net Interaction Protocol Specification](https://www.eecis.udel.edu/~decker/courses/886f04/pubs/FIPA-ips.pdf#page=24). SC00029H, Standardstatus 3. Dezember 2002. **Status:** Normative Spezifikation. Originaltext in universitärer Sammelkopie; FIPA-Originalhost beim Abruf nicht zuverlässig erreichbar. Originaladresse: [Quellenlink](https://www.fipa.org/specs/fipa00029/SC00029H.html)

4. Pınar Yolum und Munindar P. Singh (2005). [Engineering Self-Organizing Referral Networks for Trustworthy Service Selection](https://www.csc2.ncsu.edu/faculty/mpsingh/papers/mas/tsmc-05-yolum-singh.pdf). IEEE Transactions on Systems, Man, and Cybernetics – Part A, 35(3), 396–407; DOI 10.1109/TSMCA.2005.846401. **Status:** Begutachteter Zeitschriftenartikel. Autorenfassung; frühere Fassungen nicht separat gezählt.

5. Rui Li, Zeyu Zhang, Xiaohe Bo, Quanyu Dai, Chaozhuo Li, Feng Wen und Xu Chen (2026). [Towards Adaptive, Scalable, and Robust Coordination of LLM Agents: A Dynamic Ad-Hoc Networking Perspective](https://arxiv.org/html/2602.08009v1). arXiv:2602.08009v1, 8. Februar 2026. **Status:** Preprint; Konferenzannahme nicht unabhängig bestätigt. RAPS ist der Name des beschriebenen Verfahrens.

6. Yingxuan Yang, Huacan Chai, Shuai Shao, Yuanyi Song, Siyuan Qi, Renting Rui und Weinan Zhang (2025). [AgentNet: Decentralized Evolutionary Coordination for LLM-based Multi-Agent Systems](https://proceedings.neurips.cc/paper_files/paper/2025/file/9a379c1b05793d1c42dc832269834515-Paper-Conference.pdf). NeurIPS 2025. **Status:** Begutachteter Konferenzbeitrag. Finale Proceedings-Fassung; Preprint arXiv:2504.00587.

7. Patrizio Dazzi, Emanuele Carlini, Matteo Mordacchini und Saul Urso (2026). [Usable Agent Discovery for Decentralized AI Systems](https://arxiv.org/html/2604.23080v1). arXiv:2604.23080v1, 25. April 2026. **Status:** Preprint. Ereignisbasierte Simulation; keine Messung realer LLM-Arbeitsartefakte.

8. Yubin Kim, Ken Gu, Chanwoo Park et al. (2026). [Towards a Science of Scaling Agent Systems](https://arxiv.org/html/2512.08296v3). arXiv:2512.08296v3, 8. April 2026; Erstfassung Dezember 2025. **Status:** Preprint. Ausschließlich v3 für die Zahlen 260 Konfigurationen und sechs Benchmarks. Ältere Fassungen nicht mit dieser Version vermischt.

9. Jiamu Zhang, Lingxi Zhang, Pengjun Lu, Qiyue Zhang, Yu-Neng Chuang, Zhengchen Li, Shuai Xu, Vipin Chaudhary und Hanjie Chen (2026). [Rethinking the Evaluation of Efficiency Methods for Multi-Agent Systems](https://arxiv.org/html/2609.05933v1). arXiv:2609.05933v1, 5. September 2026. **Status:** Preprint; genannter EMNLP-Status nicht unabhängig bestätigt. Sehr junge Quelle. Verlinkter Code wurde nicht ausgeführt.

10. Yubin Kim, Chanwoo Park, Taehan Kim, Eugene Park, Samuel Schmidgall, Salman Rahman, Chunjong Park, Cynthia Breazeal, Xin Liu, Hamid Palangi, Hae Won Park und Daniel McDuff (2026). [TeamBench: Evaluating Agent Coordination under Enforced Role Separation](https://arxiv.org/html/2605.07073v1). arXiv:2605.07073v1, 8. Mai 2026. **Status:** Preprint. Die Aussagen beziehen sich auf den berichteten Versuchsaufbau, nicht auf beliebige Prüferrollen.

11. Sayash Kapoor, Benedikt Stroebl, Zachary S. Siegel, Nitya Nadgir und Arvind Narayanan (2025). [AI Agents That Matter](https://arxiv.org/html/2407.01502v1). Transactions on Machine Learning Research; Erstpreprint 2024. **Status:** Begutachteter Zeitschriftenartikel. Technische Aussagen aus Erstfassung. Publikationsstatus durch Autorenrepository bestätigt: [Quellenlink](https://github.com/benediktstroebl/agent-evals)

12. Thomas C. King, Akın Günay, Amit K. Chopra und Munindar P. Singh (2017). [Tosca: Operationalizing Commitments Over Information Protocols](https://www.csc2.ncsu.edu/faculty/mpsingh/papers/mas/IJCAI-17-Tosca.pdf). IJCAI 2017. **Status:** Begutachteter Konferenzbeitrag. Autorenfassung; ergänzende Metadaten unter arXiv:1708.03209.

13. Jinghan Xu, Longze Fan, Zeyuan Wang, Xinjin Li und Hankai Liu (2026). [Beyond Single-Use Tokens: Durable Authorization State for Replay-Resistant LLM Agent Actions](https://arxiv.org/html/2608.01710v1). arXiv:2608.01710v1, 3. August 2026. **Status:** Preprint. Bedingungen für dauerhaften Zustand und idempotente Zielsysteme beachten.

14. Haoyu Wang, Christopher M. Poskitt und Jun Sun (2026). [AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents](https://cposkitt.github.io/files/publications/agentspec_llm_enforcement_icse26.pdf). ICSE 2026; DOI 10.1145/3744916.3764546. **Status:** Begutachteter Konferenzbeitrag. Autorenfassung mit ACM-Zitation; Erstpreprint März 2025.

15. Olly Styles, Sam Miller, Patricio Cerda-Mardini, Tanaya Guha, Victor Sanchez und Bertie Vidgen (2024). [WorkBench: a Benchmark Dataset for Agents in a Realistic Workplace Setting](https://arxiv.org/html/2405.00823v2). COLM 2024; arXiv:2405.00823v2. **Status:** Begutachteter Konferenzbeitrag. Konferenzfassung: [Quellenlink](https://openreview.net/pdf/963b3b65da703ab1c625cafe9bd50924ffbcb284.pdf)

16. Harsh Trivedi, Tushar Khot, Mareike Hartmann, Ruskin Manku, Vinty Dong, Edward Li, Shashank Gupta, Ashish Sabharwal und Niranjan Balasubramanian (2024). [AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents](https://aclanthology.org/2024.acl-long.850/). ACL 2024. **Status:** Begutachteter Konferenzbeitrag. Ergänzend gelesene Autorenfassung: [Quellenlink](https://arxiv.org/html/2407.18901v1)

17. Dat Tran und Douwe Kiela (2026). [Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets](https://arxiv.org/html/2604.02460v2). arXiv:2604.02460v2, 11. April 2026. **Status:** Preprint. Textbasiertes Multi-Hop-Reasoning; keine universelle Aussage über Werkzeugagenten.

18. Yuxuan Zhu, Tengjun Jin, Yada Pruksachatkun et al. (2025). [Establishing Best Practices in Building Rigorous Agentic Benchmarks](https://papers.nips.cc/paper_files/paper/2025/hash/f316275b44ee2de533102913828a8107-Abstract-Datasets_and_Benchmarks_Track.html). NeurIPS 2025, Datasets and Benchmarks Track; DOI 10.52202/085713-5547. **Status:** Begutachteter Konferenzbeitrag. Preprintfassung arXiv:2507.02825v5 (7. August 2025) trägt den Titel mit „for Building“; Proceedings-Titel mit „in Building“. Technische Aussagen anhand der Autorenfassung geprüft.


## Fußnoten

[^1]: Treiber et al. (2011), Abschnitte 3–7. [Originalquelle](https://dsg.tuwien.ac.at/team/dschall/papers/2011_tweetflows.pdf).

[^2]: Smith (1980), Abschnitte II–IV. [Originalquelle](https://cse-robotics.engr.tamu.edu/dshell/cs631/papers/smith80contract.pdf).

[^3]: FIPA (2002), Abschnitte 1.1–1.2; Sammel-PDF ab Seite 24. [Originalquelle](https://www.eecis.udel.edu/~decker/courses/886f04/pubs/FIPA-ips.pdf#page=24).

[^4]: Yolum und Singh (2005), Abschnitte II–V. [Originalquelle](https://www.csc2.ncsu.edu/faculty/mpsingh/papers/mas/tsmc-05-yolum-singh.pdf).

[^5]: Li et al. (2026), RAPS, Abschnitte 4.2–4.4, 5.3–5.4; Anhang C. [Originalquelle](https://arxiv.org/html/2602.08009v1).

[^6]: Yang et al. (2025), AgentNet, Abschnitte 3.2–3.4, 4.3; Anhang E. [Originalquelle](https://proceedings.neurips.cc/paper_files/paper/2025/file/9a379c1b05793d1c42dc832269834515-Paper-Conference.pdf).

[^7]: Dazzi et al. (2026), Usable Agent Discovery, Abschnitte 3–5.3. [Originalquelle](https://arxiv.org/html/2604.23080v1).

[^8]: Kim et al. (2026), Scaling, Abschnitte 4.5–5; Metadaten der Version 3. [Originalquelle](https://arxiv.org/html/2512.08296v3).

[^9]: Zhang et al. (2026), Effizienzevaluation, Abschnitte 2–4. [Originalquelle](https://arxiv.org/html/2609.05933v1).

[^10]: Kim et al. (2026), TeamBench, Benchmarkdesign, Verifier-Ergebnisse und Ablation. [Originalquelle](https://arxiv.org/html/2605.07073v1).

[^11]: Kapoor et al. (2025), Kostenkontrolle, Holdouts und Reproduzierbarkeit. [Originalquelle](https://arxiv.org/html/2407.01502v1).

[^12]: King et al. (2017), Einleitung und Protokollsynthese. [Originalquelle](https://www.csc2.ncsu.edu/faculty/mpsingh/papers/mas/IJCAI-17-Tosca.pdf).

[^13]: Xu et al. (2026), CapLease, Autorisierungsmodell und Vergleich mit Server Ledger. [Originalquelle](https://arxiv.org/html/2608.01710v1).

[^14]: Wang et al. (2026), AgentSpec, Laufzeitregeln und Evaluation. [Originalquelle](https://cposkitt.github.io/files/publications/agentspec_llm_enforcement_icse26.pdf).

[^15]: Styles et al. (2024), WorkBench, Aufgaben, Werkzeuge und zustandsbasierte Bewertung. [Originalquelle](https://arxiv.org/html/2405.00823v2).

[^16]: Trivedi et al. (2024), AppWorld, Umgebungs- und Evaluationsdesign. [Originalquelle](https://aclanthology.org/2024.acl-long.850/).

[^17]: Tran und Kiela (2026), Budgetkontrolle, Experimente und Einschränkungen. [Originalquelle](https://arxiv.org/html/2604.02460v2).

[^18]: Zhu et al. (2025), ABC, Agentic Benchmark Checklist und Evaluationsvalidität. [Originalquelle](https://papers.nips.cc/paper_files/paper/2025/hash/f316275b44ee2de533102913828a8107-Abstract-Datasets_and_Benchmarks_Track.html).
