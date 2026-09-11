/* Italian source messages and their English translations. No resource names are translated. */
(function (root) {
  'use strict';
  const translations = {
    'Sentinel · Infrastruttura': 'Sentinel · Infrastructure',
    'Infrastruttura': 'Infrastructure',
    'Vai ai dati': 'Skip to data',
    'Sentinel, panoramica': 'Sentinel overview',
    'Dashboard privata': 'Private dashboard',
    'Lingua': 'Language',
    'Allarmi': 'Alerts',
    'Aggiorna': 'Refresh',
    'Selezione server': 'Server selection',
    'Server': 'Servers',
    'Server monitorati': 'Monitored servers',
    'Caricamento…': 'Loading…',
    'Progetti': 'Projects',
    'Risorse per progetto': 'Resources by project',
    'Sorgente dei dati': 'Data source',
    'CPU e memoria raccolte sui server e conservate dalla dashboard.': 'CPU and memory collected on your servers and stored by the dashboard.',
    'Raccolta e storico': 'Collection and history',
    'Lettura della configurazione…': 'Loading configuration…',
    'La raccolta continua con Docker attivo. Dopo una pausa recupera i campioni ancora disponibili su Sentinel.': 'Collection continues while Docker is running. After a pause, it retrieves samples still available in Sentinel.',
    'Panoramica del server': 'Server overview',
    'Lettura delle informazioni…': 'Loading information…',
    'In attesa': 'Waiting',
    'Allarmi e Non disturbare': 'Alerts and Do not disturb',
    'Allarmi attivi': 'Enable alerts',
    'Suono': 'Sound',
    'Non disturbare adesso': 'Do not disturb now',
    'CPU server (%)': 'Server CPU (%)',
    'RAM server (%)': 'Server RAM (%)',
    'Durata minima (secondi)': 'Minimum duration (seconds)',
    'Non disturbare ogni giorno': 'Daily quiet hours',
    'Dalle': 'From',
    'Alle': 'Until',
    'Ora locale:': 'Local time zone:',
    '. Se CPU o RAM restano sopra soglia, l’avviso si ripete ogni 5 minuti. Durante Non disturbare rimane solo l’avviso visivo; alla fine della fascia viene segnalato un eventuale superamento ancora attivo.': '. If CPU or RAM stays above the threshold, alerts repeat every 5 minutes. Do not disturb keeps visual alerts only; any ongoing threshold violation is reported when quiet hours end.',
    'Salva impostazioni': 'Save settings',
    'Regola per il server o la risorsa selezionata': 'Rule for the selected server or resource',
    'Seleziona una risorsa dalla dashboard.': 'Select a resource in the dashboard.',
    'CPU (%)': 'CPU (%)',
    'RAM (%)': 'RAM (%)',
    'Durata (secondi)': 'Duration (seconds)',
    'Salva regola per questa risorsa': 'Save rule for this resource',
    'Abilita notifiche e audio': 'Enable notifications and audio',
    'Abilita audio': 'Enable audio',
    'Prova avviso': 'Test alert',
    'Per ricevere gli allarmi tieni aperta una scheda della dashboard, anche in background, con il dispositivo acceso. Browser e sistema possono ritardare gli avvisi; con la scheda chiusa o il dispositivo in stop non vengono riprodotti. La raccolta continua finché il server della dashboard è attivo. Le preferenze sono salvate in questo browser.': 'To receive alerts, keep a dashboard tab open, including in the background, with your device awake. Your browser and operating system may delay alerts; they cannot play when the tab is closed or the device is asleep. Collection continues while the dashboard server is running. Preferences are saved in this browser.',
    'Pronto per il primo collegamento': 'Ready for your first connection',
    'La dashboard è attiva. Collega un gateway HTTPS per iniziare a vedere CPU, memoria e applicazioni.': 'The dashboard is running. Connect an HTTPS gateway to start viewing CPU, memory and applications.',
    'I grafici appariranno con i primi campioni reali.': 'Charts will appear when the first real samples arrive.',
    'Andamento delle risorse': 'Resource usage over time',
    'Totale del server': 'Server total',
    'Periodo': 'Period',
    'Ultima ora': 'Last hour',
    'Ultime 6 ore': 'Last 6 hours',
    'Ultime 24 ore': 'Last 24 hours',
    'Ultimi 7 giorni': 'Last 7 days',
    'Ultimi 30 giorni': 'Last 30 days',
    'Ultimi 90 giorni': 'Last 90 days',
    '← Torna al totale del server': '← Back to server total',
    'Nessun campione': 'No samples',
    'In attesa dei dati CPU': 'Waiting for CPU data',
    'Utilizzo CPU nel periodo selezionato': 'CPU usage in the selected period',
    'Memoria': 'Memory',
    'In attesa dei dati RAM': 'Waiting for memory data',
    'Memoria utilizzata nel periodo selezionato': 'Memory usage in the selected period',
    'Le interruzioni nei grafici indicano dati mancanti. La CPU dei container può superare il 100% quando usa più core.': 'Gaps in charts indicate missing data. Container CPU usage can exceed 100% when using multiple cores.',
    'Applicazioni e container': 'Applications and containers',
    'Seleziona una risorsa per consultarne lo storico.': 'Select a resource to view its history.',
    'Cerca una risorsa': 'Search resources',
    'Cerca una risorsa…': 'Search resources…',
    'Ordina le risorse': 'Sort resources',
    'Nome': 'Name',
    'CPU più alta': 'Highest CPU',
    'RAM più alta': 'Highest RAM',
    'Risorsa': 'Resource',
    'Stato dei dati': 'Data status',
    'Ultimo campione': 'Last sample',
    "L'inventario comparirà dopo il collegamento del gateway.": 'The inventory will appear after connecting the gateway.',
    'Solo lettura · Nessun accesso SSH': 'Read only · No SSH access',
    'In attesa di collegamento': 'Waiting for a connection',
    'Aggiornato': 'Up to date',
    'Dati non recenti': 'Stale data',
    'Lettura incompleta': 'Incomplete reading',
    'Dati parziali': 'Partial data',
    '{count} s fa': '{count}s ago',
    '{count} min fa': '{count} min ago',
    'Impossibile leggere i dati.': 'Unable to read data.',
    'Da collegare': 'Not connected',
    'Gateway non raggiungibile': 'Gateway unreachable',
    'In attesa di campioni recenti': 'Waiting for recent samples',
    '⚠ Utilizzo elevato': '⚠ High usage',
    'Soglia di attenzione: CPU o RAM ≥ 80%. ': 'Warning threshold: CPU or RAM ≥ 80%. ',
    'RAM: {used} su {total}.': 'RAM: {used} of {total}.',
    'Percentuale RAM non disponibile: manca la memoria totale.': 'RAM percentage unavailable: total memory is missing.',
    'Nessuna risorsa corrisponde alla ricerca.': 'No resources match your search.',
    'Applicazione': 'Application',
    'Servizio': 'Service',
    'Non in esecuzione': 'Not running',
    'Nessun progetto disponibile.': 'No projects available.',
    'Elenco progetti non disponibile.': 'Project list unavailable.',
    'Ultimo campione · ': 'Last sample · ',
    'Nessun campione in questo periodo': 'No samples in this period',
    'I dati mancanti non vengono rappresentati come zero.': 'Missing data is not shown as zero.',
    '{metric}, andamento nelle ultime {hours} ore': '{metric} usage over the last {hours} hours',
    'Utilizzo CPU': 'CPU usage',
    'Memoria utilizzata': 'Memory usage',
    'Media {average} · Picco {peak} · Solo campioni disponibili': 'Average {average} · Peak {peak} · Available samples only',
    'Sincronizzazione ogni {seconds} secondi. Conservazione: {days} giorni.': 'Sync every {seconds} seconds. Retention: {days} days.',
    'Nessun server configurato': 'No servers configured',
    'Ultimo contatto con il gateway · ': 'Last gateway contact · ',
    'In attesa del primo contatto con il gateway': 'Waiting for the first gateway contact',
    'Server pilota · Gateway HTTPS da collegare': 'Connect an HTTPS gateway to this server',
    ' · storico dei container associati': ' · associated container history',
    'Vista aggiornata alle ': 'View updated at ',
    'La richiesta ha impiegato troppo tempo. Nuovo tentativo automatico.': 'The request timed out. Retrying automatically.',
    'Vista non aggiornata': 'View out of date',
    'Il browser non consente di salvare le preferenze. Mantieni aperta una sola scheda.': 'The browser cannot save preferences. Keep only one tab open.',
    'Notifiche non disponibili su HTTP': 'Notifications are unavailable over HTTP',
    'Notifiche non supportate in questo browser': 'Notifications are not supported in this browser',
    'Notifiche autorizzate': 'Notifications allowed',
    'Notifiche bloccate: consentile nelle impostazioni del browser': 'Notifications blocked: allow them in your browser settings',
    'Notifiche da autorizzare': 'Notification permission required',
    'Audio pronto': 'Audio ready',
    'Audio da abilitare per questa scheda': 'Enable audio for this tab',
    'RAM (MiB utilizzati)': 'RAM (MiB used)',
    '{name} · CPU > {cpu}% o RAM > {memory}{unit} per {seconds} s': '{name} · CPU > {cpu}% or RAM > {memory}{unit} for {seconds}s',
    'Rimuovi': 'Remove',
    'Rimuovi regola ': 'Remove rule ',
    'Tutti i server usano le soglie generali. Aggiungi qui eventuali regole specifiche; per le applicazioni la RAM è espressa in MiB.': 'All servers use the global thresholds. Add specific rules here; application RAM is measured in MiB.',
    'Sentinel · Prova avviso': 'Sentinel · Test alert',
    'Sentinel · Utilizzo elevato': 'Sentinel · High usage',
    'Notifiche attive. Il suono viene riprodotto se abilitato.': 'Notifications are working. Sound plays if enabled.',
    'Altre {count} risorse': '{count} more resources',
    'Disattivati': 'Disabled',
    'Non disturbare attivo': 'Do not disturb on',
    '{count} in corso': '{count} active',
    'Attivi': 'Enabled',
    'Sopra soglia: ': 'Above threshold: ',
    'Allarmi disattivati. ': 'Alerts disabled. ',
    'Non disturbare: notifiche e suono silenziati. ': 'Do not disturb: notifications and sound muted. ',
    'Verifica incompleta: alcuni dati non sono disponibili.': 'Incomplete check: some data is unavailable.',
    'Verifica non disponibile': 'Alert check unavailable',
    'Scegli orari di inizio e fine diversi.': 'Choose different start and end times.',
    'Impostazioni salvate. Promemoria ogni 5 minuti durante il superamento.': 'Settings saved. Reminders repeat every 5 minutes while usage stays above the threshold.',
    'Puoi salvare al massimo 20 regole specifiche.': 'You can save up to 20 specific rules.',
    'Regola salvata per {name}.': 'Rule saved for {name}.',
    'Attiva gli allarmi prima della prova.': 'Enable alerts before testing.',
    'Non disturbare è attivo: prova silenziata.': 'Do not disturb is on: test muted.',
    'Avviso di prova inviato.': 'Test alert sent.',
    'Premi “Abilita notifiche e audio” per preparare gli avvisi.': 'Use the enable button to prepare notifications and audio.',
    'Lingua modificata, ma il browser non consente di salvare la preferenza.': 'Language changed, but the browser could not save your preference.',
    'Il servizio ha restituito un redirect inatteso.': 'The service returned an unexpected redirect.',
    "Risposta troppo grande: ridurre l'intervallo.": 'Response too large: reduce the time range.',
    'Autenticazione del servizio non riuscita.': 'Service authentication failed.',
    'Il servizio metriche non ha risposto correttamente.': 'The metrics service did not respond correctly.',
    'Servizio non raggiungibile o risposta non valida.': 'Service unreachable or invalid response.',
    'Parametro duplicato.': 'Duplicate parameter.',
    'Parametro non consentito.': 'Parameter not allowed.',
    'Risorsa o metrica non valida.': 'Invalid resource or metric.',
    'Intervallo UTC non valido; massimo 6 ore.': 'Invalid UTC range; maximum 6 hours.',
    'Operazione Docker non consentita.': 'Docker operation not allowed.',
    'Sentinel o inventario Docker non disponibili.': 'Sentinel or Docker inventory unavailable.',
    'Inventario Docker non raggiungibile.': 'Docker inventory unreachable.',
    'Rete Sentinel non supportata: verificare la configurazione del pilota.': 'Unsupported Sentinel network: check the server configuration.',
    'Token Sentinel non disponibile.': 'Sentinel token unavailable.',
    'Formato Sentinel non riconosciuto.': 'Unrecognized Sentinel format.',
    "Nessun campione Sentinel valido nell'intervallo.": 'No valid Sentinel samples in this range.',
    'Endpoint del lettore non consentito.': 'Reader endpoint not allowed.',
    'Il lettore interno non ha risposto correttamente.': 'The internal reader did not respond correctly.',
    'Socket del lettore non raggiungibile o risposta non valida.': 'Reader socket unreachable or invalid response.',
    'Formato dei campioni non valido.': 'Invalid sample format.',
    'Inventario non valido.': 'Invalid inventory.',
    'Server non trovato.': 'Server not found.',
    'Intervallo non valido.': 'Invalid time range.',
    'Intervallo o metrica non validi.': 'Invalid time range or metric.',
    'Risorsa non valida.': 'Invalid resource.',
    'Pagina non trovata.': 'Page not found.',
    'Percorso non valido.': 'Invalid path.',
    'Indirizzo della dashboard non autorizzato.': 'Dashboard address not allowed.',
    'Autenticazione richiesta.': 'Authentication required.',
    'Endpoint non disponibile.': 'Endpoint unavailable.',
    'Richiesta non valida.': 'Invalid request.',
    'Errore interno del servizio.': 'Internal service error.',
    'Sono consentite soltanto richieste GET.': 'Only GET requests are allowed.',
    'Destinazione allarme non valida.': 'Invalid alert target.',
    'Soglie o durata non valide.': 'Invalid thresholds or duration.'
  };
  const LANGUAGE_KEY = 'sentinel.language.v1';
  function chooseLanguage(saved, languages = []) {
    if (saved === 'it' || saved === 'en') return saved;
    for (const candidate of languages) {
      const base = String(candidate).toLowerCase().split('-')[0];
      if (base === 'it' || base === 'en') return base;
    }
    return 'en';
  }
  function createI18n(storage, languages) {
    let saved;
    try { saved = storage?.getItem(LANGUAGE_KEY); } catch { /* Storage is optional. */ }
    let language = chooseLanguage(saved, languages);
    return {
      get language() { return language; },
      get locale() { return language === 'it' ? 'it-IT' : 'en-GB'; },
      setLanguage(next, persist = true) {
        if (next !== 'it' && next !== 'en') return false;
        language = next;
        if (persist && !storage) return false;
        try { if (persist) storage.setItem(LANGUAGE_KEY, next); return true; }
        catch { return false; }
      },
      t(message, values = {}) {
        const template = language === 'en' ? translations[message] ?? message : message;
        return template.replace(/\{(\w+)\}/g, (match, key) => Object.hasOwn(values, key) ? String(values[key]) : match);
      },
      source(message) {
        return Object.hasOwn(translations, message) ? message : Object.keys(translations).find(key => translations[key] === message) ?? message;
      },
      error(message) {
        const source = this.source(message);
        return this.t(Object.hasOwn(translations, source) ? source : 'Impossibile leggere i dati.');
      }
    };
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { translations, LANGUAGE_KEY, chooseLanguage, createI18n };
    return;
  }
  let storage;
  try { storage = root.localStorage; } catch { /* Use browser language without persistence. */ }
  const i18n = createI18n(storage, root.navigator.languages || [root.navigator.language]);
  root.SentinelI18n = i18n;
  const textNodes = [], attributes = [];
  const walker = document.createTreeWalker(document.documentElement, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode, source = node.textContent.trim();
    if (source && !node.parentElement.closest('script, style, #language')) {
      textNodes.push({ node, source, prefix: node.textContent.match(/^\s*/)[0], suffix: node.textContent.match(/\s*$/)[0] });
    }
  }
  document.querySelectorAll('[aria-label], [placeholder], [title]').forEach(node => {
    for (const attribute of ['aria-label', 'placeholder', 'title']) {
      if (node.hasAttribute(attribute)) attributes.push({ node, attribute, source: node.getAttribute(attribute) });
    }
  });
  const selector = document.getElementById('language');
  function render() {
    document.documentElement.lang = i18n.language;
    textNodes.forEach(({ node, source, prefix, suffix }) => { if (node.isConnected) node.textContent = prefix + i18n.t(source) + suffix; });
    attributes.forEach(({ node, attribute, source }) => { if (node.isConnected) node.setAttribute(attribute, i18n.t(source)); });
    selector.value = i18n.language;
    root.dispatchEvent(new Event('sentinel-language-change'));
  }
  selector.addEventListener('change', () => {
    const saved = i18n.setLanguage(selector.value);
    render();
    document.getElementById('language-feedback').textContent = saved ? '' : i18n.t('Lingua modificata, ma il browser non consente di salvare la preferenza.');
  });
  root.addEventListener('storage', event => {
    if (event.key === LANGUAGE_KEY || event.key === null) {
      i18n.setLanguage(chooseLanguage(event.newValue, root.navigator.languages), false);
      render();
    }
  });
  render();
})(typeof window !== 'undefined' ? window : globalThis);
