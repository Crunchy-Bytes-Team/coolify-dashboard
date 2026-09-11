# Sentinel Dashboard

[![Licenza MIT](https://img.shields.io/badge/licenza-MIT-397459)](LICENSE)
![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB)
![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED)

**CPU, memoria e storico della tua infrastruttura Coolify, in un'unica dashboard.**

Controlla più server, individua le applicazioni che consumano risorse e configura
allarmi per i superamenti prolungati. La dashboard legge i dati già raccolti da
Coolify Sentinel attraverso gateway HTTPS e conserva lo storico in SQLite.

Si esegue con Docker Compose su una workstation o un server privato. Il collector
continua a lavorare a browser chiuso; Python usa soltanto la libreria standard e
il frontend non richiede un processo di build. L'interfaccia è in italiano, con
tema chiaro/scuro, navigazione da tastiera e stati leggibili anche senza colori.

**[Avvio rapido](#avvio-rapido)** · **[Collegare i server](#collegare-un-server-coolify)** ·
**[Deploy su server](#installare-la-dashboard-su-un-server-privato)** ·
**[Allarmi](#allarmi)** · **[Risoluzione problemi](#risoluzione-dei-problemi)** ·
**[Contribuire](#sviluppo-e-verifiche)**

## Funzionalità

| | Cosa offre |
| --- | --- |
| **Panoramica** | CPU e RAM percentuali per server, evidenziazione dei consumi elevati e timestamp dei campioni. |
| **Dettaglio** | Grafici per server e risorsa, inventario applicazioni e navigazione per progetto. |
| **Storico** | Campioni recenti e aggregati di lungo periodo in SQLite, con recupero delle interruzioni. |
| **Allarmi** | Soglie e durata configurabili, avvisi visivi, suono, notifiche browser e Non disturbare. |
| **Raccolta** | Gateway HTTPS autenticato per ogni server, senza SSH dal collector. |
| **Dati trasparenti** | Stati aggiornato, obsoleto e non disponibile; i dati mancanti restano interruzioni nei grafici. |

## Avvio rapido

Richiede **Docker con Docker Compose**. Dopo aver scaricato o clonato il progetto,
eseguire questi comandi dalla sua directory, solo per una prima installazione:

```sh
mkdir -p secrets
cp config/servers.example.json config/servers.json
cp secrets/dashboard.env.example secrets/dashboard.env
chmod 600 secrets/dashboard.env
docker compose up -d --build
```

Aprire http://localhost:3090. Il server di esempio è disabilitato: abilitarlo solo
dopo aver configurato il gateway e il relativo token. L'esempio non contiene dati
simulati nella dashboard.

Per iniziare a ricevere dati occorre almeno un server Linux gestito da Coolify con
Sentinel e la raccolta delle metriche attivi. Non occorre installare Python o Node.js
sulla workstation per eseguire la versione Docker.

La porta locale è limitata a `127.0.0.1`. Il volume Docker `metrics-data` conserva
SQLite quando il container viene ricreato. `docker compose stop dashboard` arresta
la raccolta senza eliminare i dati; evitare `docker compose down -v` per mantenerli.

## Collegare un server Coolify

1. Verificare che Sentinel e la raccolta delle metriche siano attivi sul server Linux.
2. Creare una risorsa Docker Compose in Coolify, nel server e progetto desiderati.
3. Incollare `deploy/coolify-gateway-portable.yaml` e assegnare **solo a
   metrics-gateway** un dominio HTTPS, con porta interna `8080`.
4. Coolify genera `SERVICE_PASSWORD_64_READER` e `SERVICE_PASSWORD_64_GATEWAY`.
   Copiare il valore del secondo in `secrets/dashboard.env`, usando una variabile
   distinta per ciascun server, per esempio `METRICS_GATEWAY_SERVER_01`.
5. Aggiungere una voce a `config/servers.json`: un `id` stabile e univoco, il nome
   desiderato, `url` dell'origine HTTPS, `token_env` con il nome della variabile e
   `enabled: true`. Il token non va scritto nel JSON.
6. Impostare `sentinel_retention_days` secondo lo storico disponibile sul server.
7. Eseguire `docker compose up -d --force-recreate` per caricare configurazione e
   credenziali. Verificare inventario e timestamp, oltre agli healthcheck.

Esempio di `config/servers.json` per un gateway già configurato:

```json
{
  "poll_seconds": 30,
  "retention_days": 90,
  "servers": [
    {
      "id": "server-01",
      "name": "Example server",
      "enabled": true,
      "url": "https://metrics.example.com",
      "token_env": "METRICS_GATEWAY_SERVER_01",
      "sentinel_retention_days": 7
    }
  ]
}
```

In `secrets/dashboard.env` aggiungere `METRICS_GATEWAY_SERVER_01` con il valore
generato in Coolify. Per collegare altri server aggiungere una voce JSON e una
variabile per ciascun gateway. Gli URL negli esempi sono fittizi.

| Impostazione | Significato |
| --- | --- |
| `id` | Identità locale stabile del server: mantenerla per conservare l'associazione allo storico. |
| `url` | Origine HTTPS del gateway, senza percorsi, query o credenziali nell'URL. |
| `token_env` | Nome della variabile d'ambiente contenente il token del gateway. |
| `poll_seconds` | Intervallo desiderato di raccolta, minimo 15 secondi. |
| `retention_days` | Conservazione locale degli aggregati, da 7 a 365 giorni. |
| `sentinel_retention_days` | Storico disponibile alla sorgente, fino a 7 giorni. |

Il gateway richiede HTTPS con certificato valido. Per una CA privata è disponibile
`ca_file`, riferito a un certificato montato nel container, per esempio sotto
`/run/secrets`. I redirect non vengono seguiti e la verifica TLS resta attiva.

Il template portabile incorpora il codice Python come variabile di configurazione
non segreta, evitando dipendenze dai permessi dei file generati da Coolify.
`deploy/coolify-gateway.yaml` è una variante che usa l'estensione Coolify
`volumes.content`: non è un Compose da avviare direttamente su una workstation.
Questa variante richiede `METRICS_GATEWAY_TOKEN` e `METRICS_READER_TOKEN`, distinti;
non usa `configs.content`, incompatibile con alcune modalità di avvio in sola lettura.

## Installare la dashboard su un server privato

`deploy/coolify-dashboard.yaml` è un esempio per una risorsa Compose gestita da
Coolify. Preparare sull'host le directory sotto `/var/coolify/coolify-dashboard`:

| Directory | Contenuto | Mount |
| --- | --- | --- |
| `app` | `service.py`, `alerts.py`, `dist/` e `gateway.yaml` | `/app`, sola lettura |
| `config` | `servers.json` reale | `/config`, sola lettura |
| `secrets` | `dashboard.env` ed eventuali CA | `/run/secrets`, sola lettura |
| `data` | SQLite, WAL e SHM | `/data`, scrivibile |

Per `app/gateway.yaml` usare `deploy/coolify-gateway.yaml`. Trasferire i file con
un canale privato e dare all'utente del container, UID/GID `10001:10001`, accesso
ai file montati. Limitare i permessi di dati e segreti; il file `.env` viene letto
da Docker Compose sull'host. Per migrare uno storico attivo usare l'API SQLite
`backup`, evitando di copiare soltanto il database mentre esistono scritture WAL.

Sostituire `dashboard.example.com` in `DASHBOARD_ALLOWED_HOSTS` e configurare il
dominio nella risorsa Coolify, indicando la porta interna `3090`. La dashboard
non pubblica direttamente una porta host: la raggiunge il proxy Coolify.
Per aggiornare il codice trasferire solo i file di `app` e riavviare la risorsa,
senza sovrascrivere `data`.

La dashboard **non include un login**. Mantenerla dietro una rete privata/VPN o un
proxy con autenticazione. Il controllo Host limita i nomi ammessi e non sostituisce
l'autenticazione. Di default sono ammessi solo localhost e 127.0.0.1; i nomi
aggiuntivi si configurano esplicitamente in `DASHBOARD_ALLOWED_HOSTS`.

## Architettura e confini di accesso

```mermaid
flowchart LR
    Browser[Browser] --> Dashboard[Dashboard e collector]
    Dashboard --> SQLite[(SQLite persistente)]
    Dashboard -->|HTTPS e token gateway| Proxy[Proxy Coolify]
    subgraph Server[Ogni server monitorato]
        Proxy --> Gateway[metrics-gateway]
        Gateway -->|Socket Unix e token lettore| Reader[sentinel-reader]
        Reader -->|Inventario| Docker[API Docker]
        Reader -->|CPU e RAM| Sentinel[Coolify Sentinel]
    end
```

Il lettore usa la rete host Linux e ascolta solo sul socket Unix condiviso. Il
gateway non monta il socket Docker. Le sole API autenticate sono
`GET /v1/inventory` e `GET /v1/history`; `/health` riporta lo stato del processo.
Non sono esposti endpoint di deploy, esecuzione comandi o proxy generico.

Il lettore monta il socket Docker: **il mount `:ro` non rende l'API Docker di sola
lettura**. Il codice permette solo due GET specifiche, ma il processo rimane un
componente fidato: una sua compromissione potrebbe dare accesso al daemon.
Credenziali e variabili d'ambiente non vengono restituite al browser.

## Storico e interpretazione dei dati

- Polling predefinito ogni 30 secondi, con quattro richieste concorrenti per server.
  Un ciclo lento può durare più dell'intervallo; gli altri server procedono in modo
  indipendente. Il recupero storico usa due worker e blocchi di un'ora.
- Campioni originali per sette giorni; aggregati di cinque minuti fino al periodo
  configurato, 90 giorni per default. Media, minimo, massimo e conteggio sono conservati.
- Il recupero è limitato allo storico ancora presente in Sentinel, al massimo sette
  giorni. Il browser può essere chiuso durante la raccolta; il collector deve restare attivo.
- La CPU del server è percentuale dell'host; quella di un container può superare
  il 100% quando usa più core. La RAM delle risorse è espressa in MiB/GiB.
- Le etichette Coolify associano le sorgenti alle applicazioni. I redeploy con
  identità stabile conservano lo storico; le repliche vengono aggregate. Sorgenti
  che condividono la stessa chiave Sentinel non possono essere distinte a valle.
- Inventario e disponibilità delle metriche sono separati. I servizi senza
  campioni restano senza dati; campioni mancanti non vengono convertiti in zero.
- Un container creato e rimosso interamente durante un'interruzione della raccolta
  può non essere identificabile. Build server, Swarm e reti Sentinel personalizzate
  richiedono una verifica specifica.
- Timestamp UTC, visualizzati nel fuso del browser. SQLite usa WAL e
  `synchronous=NORMAL`: un'interruzione di alimentazione può perdere gli ultimi
  campioni locali, recuperabili finché sono presenti in Sentinel.

## Allarmi

Da **Allarmi** impostare soglie CPU/RAM e durata minima: per default 80% per
30 secondi sui server. Sono disponibili fino a 20 regole specifiche; per le
applicazioni la soglia RAM è in MiB. Gli avvisi si ripetono ogni cinque minuti.

Non disturbare è attivo per default dalle 00:00 alle 06:00 nel fuso del browser,
con fascia modificabile e interruttore manuale. Mantiene gli avvisi visivi e silenzia
notifiche e audio. Dati mancanti o obsoleti sospendono la valutazione.

Premere **Abilita notifiche e audio** dopo aver aperto la pagina. Le notifiche
native richiedono un contesto sicuro (HTTPS o localhost) e il permesso del browser;
su un dominio HTTP rimangono gli avvisi visivi e il suono. Non si tratta di Web Push:
serve una scheda aperta e un dispositivo attivo, e i timer in background possono
subire ritardi. Preferenze e cadenza sono salvate per browser e origine; cambiare
dominio non le trasferisce automaticamente.

| Valore predefinito | Comportamento |
| --- | --- |
| CPU / RAM server: **80%** | Attenzione immediata nella sidebar; gli allarmi valutano anche la durata. |
| Durata: **30 secondi** | Il superamento deve persistere nei campioni disponibili. |
| Ripetizione: **5 minuti** | Un nuovo avviso mentre il superamento continua. |
| Non disturbare: **00:00–06:00** | Silenzia audio e notifiche, mantenendo gli avvisi visivi. |

## Risoluzione dei problemi

| Sintomo | Controlli utili |
| --- | --- |
| Nessun server configurato | Verificare `config/servers.json` ed `enabled: true`; il server di esempio parte disabilitato. |
| Gateway non raggiungibile | Controllare DNS, rete, dominio HTTPS e certificato; per una CA privata configurare `ca_file`. |
| Autenticazione fallita | Il valore deve essere la password **gateway**, non quella del lettore o di Sentinel. Ricreare il container dopo aver cambiato l'env. |
| Server visibile, applicazione senza dati | Sentinel potrebbe non raccogliere campioni per quella risorsa; l'inventario Docker non garantisce la copertura delle metriche. |
| Campioni obsoleti dopo un'interruzione | Lasciare al collector il tempo di recuperare lo storico; gli intervalli già eliminati da Sentinel non sono recuperabili. |
| Dashboard rifiutata sul dominio privato | Controllare `DASHBOARD_ALLOWED_HOSTS` e la porta interna 3090 configurata nel proxy. |
| Audio assente | Abilitare l'audio nella scheda corrente, verificare Non disturbare e mantenere il dispositivo attivo. |
| Notifiche browser assenti | Verificare contesto sicuro, autorizzazione del browser e Non disturbare. Su un dominio HTTP non sono disponibili. |

Per controllare il processo locale: `docker compose ps` e `docker compose logs --tail=100 dashboard`.
Prima di condividere log o schermate, rimuovere nomi delle
risorse, domini e altri dettagli della propria infrastruttura.

## Sviluppo e verifiche

Per eseguire i test servono Python 3.13, Node.js e OpenSSL. Docker Compose è
necessario solo per le verifiche dei template.

```sh
python3 -m unittest discover -s tests -v
node --check dist/app.js
node --test tests/alert-core.test.cjs
docker compose config --quiet
python3 deploy/check-compose.py
```

I test usano fixture e certificati temporanei e non contattano server di produzione.
`deploy/gateway-service.py` contiene le funzioni condivise con `service.py`, con
un avvio limitato ai ruoli reader/gateway. I test confrontano le definizioni Python
e i sorgenti incorporati nei due template gateway: mantenerli sincronizzati.

Le modifiche al collector dovrebbero mantenere separati raccolta corrente e recupero
storico. Per frontend e allarmi preservare gli stati dei dati mancanti, l'accessibilità
e il comportamento di Non disturbare. Descrivere nelle proposte di modifica il
problema risolto e le verifiche eseguite, usando esempi fittizi.

## File privati e pubblicazione

`.gitignore` esclude configurazione reale, credenziali, database, archivi e la
directory `private/`, riservata a configurazioni e resoconti operativi locali.
Gli esempi contengono solo nomi e valori fittizi. Non condividere uno ZIP dell'intera
directory di lavoro: le esclusioni Git non si applicano agli archivi creati manualmente.
Controllare i file effettivamente inclusi e la cronologia prima di pubblicare.

## Licenza

Distribuito con [licenza MIT](LICENSE). Il progetto è indipendente e non è un
prodotto ufficiale di Coolify. Le licenze dei componenti esterni restano applicabili
ai rispettivi progetti.

## Riferimenti

- [API Sentinel](https://github.com/coollabsio/sentinel/blob/main/API.md)
- [Avvio Sentinel in Coolify](https://github.com/coollabsio/coolify/blob/v4.x/app/Actions/Server/StartSentinel.php)
- [Documentazione Coolify](https://coolify.io/docs)
- [Rete host Docker](https://docs.docker.com/engine/network/drivers/host/)
