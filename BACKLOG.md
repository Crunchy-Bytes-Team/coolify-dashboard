# Allarmi CPU/RAM — implementati

Funzionalità disponibili nella dashboard.

- Soglie configurabili per CPU e memoria, per singolo servizio o server.
- Durata minima configurabile del superamento continuo (esempio: 30 secondi).
- Notifica del browser e suono d'allarme quando il superamento persiste.
- Ripetere notifiche e suono ogni 5 minuti durante lo stesso episodio; riarmare al rientro.
- Non disturbare manuale e fascia giornaliera configurabile, attiva per default dalle 00:00 alle 06:00 nell'ora locale del browser. Avvisi visivi mantenuti, suono e notifiche silenziati; alla fine della fascia segnalare eventuali superamenti ancora attivi.
- Non interpretare campioni assenti o obsoleti come superamenti o rientri.
- Richiedere il permesso delle notifiche e abilitare l'audio con un'azione esplicita nell'interfaccia.
- Chiarire nell'interfaccia che gli avvisi dipendono dal browser aperto e dal dispositivo attivo; eventuale push con browser chiuso richiede una successiva estensione.

Le soglie generali coprono tutti i server (CPU/RAM 80%, 30 secondi); sono disponibili fino a 20 regole specifiche. Per le risorse la RAM è espressa in MiB, non essendo disponibile un limite affidabile per ogni container. Preferenze e promemoria persistono nel browser, con deduplicazione tra schede tramite Web Locks quando disponibili.

Sidebar aggiornata con accordion Server aperto e Progetti chiuso all'avvio. I progetti raggruppano le risorse rilevate su tutti i server.
