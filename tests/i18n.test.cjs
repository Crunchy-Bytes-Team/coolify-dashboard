const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {translations,LANGUAGE_KEY,chooseLanguage,createI18n}=require('../dist/i18n.js');

test('language choice prefers a saved supported value, then browser languages',()=>{
  assert.equal(chooseLanguage('it',['en-US']),'it');
  assert.equal(chooseLanguage('en',['it-IT']),'en');
  assert.equal(chooseLanguage('bad',['fr-FR','it-IT']),'it');
  assert.equal(chooseLanguage(null,['en-US','it']),'en');
  assert.equal(chooseLanguage(null,['fr-FR']),'en');
});
test('language persistence is isolated from existing alert preferences',()=>{
  const data=new Map([['sentinel.alerts.settings.v1','{"cpu":95}']]);
  const storage={getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)};
  const i18n=createI18n(storage,['it-IT']);
  assert.equal(i18n.setLanguage('en'),true);
  assert.equal(data.get(LANGUAGE_KEY),'en');
  assert.equal(data.get('sentinel.alerts.settings.v1'),'{"cpu":95}');
  assert.equal(createI18n(storage,['it']).language,'en');
  assert.equal(i18n.setLanguage('fr'),false);
  assert.equal(i18n.language,'en');
});
test('blocked storage still allows switching languages in the current tab',()=>{
  const i18n=createI18n({getItem(){throw Error();},setItem(){throw Error();}},['it']);
  assert.equal(i18n.language,'it');
  assert.equal(i18n.setLanguage('en'),false);
  assert.equal(i18n.t('Nessun campione'),'No samples');
});
test('interpolation preserves resource names and round trips between languages',()=>{
  const i18n=createI18n(null,['en']);
  const name='Server <test> $& {cpu}';
  assert.equal(i18n.t('Regola salvata per {name}.',{name}),'Rule saved for '+name+'.');
  i18n.setLanguage('it');
  assert.equal(i18n.t('Regola salvata per {name}.',{name}),'Regola salvata per '+name+'.');
  assert.equal(i18n.t('custom infrastructure name'),'custom infrastructure name');
});
test('dates and numbers follow the selected locale without changing the time zone',()=>{
  const i18n=createI18n(null,['en']);
  assert.equal(new Intl.NumberFormat(i18n.locale).format(42.5),'42.5');
  i18n.setLanguage('it');
  assert.equal(new Intl.NumberFormat(i18n.locale).format(42.5),'42,5');
});
test('API errors and notification copy are localized, unknown errors have a safe fallback',()=>{
  const i18n=createI18n(null,['en']);
  assert.equal(i18n.error('Autenticazione del servizio non riuscita.'),'Service authentication failed.');
  assert.equal(i18n.error('unrecognized backend response'),'Unable to read data.');
  assert.equal(i18n.t('Sentinel · Utilizzo elevato'),'Sentinel · High usage');
  i18n.setLanguage('it');
  assert.equal(i18n.error('Service authentication failed.'),'Autenticazione del servizio non riuscita.');
});
test('all visible static HTML and accessibility labels have English translations',()=>{
  const html=fs.readFileSync('dist/index.html','utf8');
  const common=new Set(['Sentinel','Coolify Sentinel','CPU','RAM','Italiano','English','↗','—','0']);
  const text=html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/g,'').replace(/<[^>]*>/g,'\n');
  const messages=[...text.split('\n').map(s=>s.trim()).filter(Boolean),
    ...Array.from(html.matchAll(/(?:aria-label|placeholder|title)="([^"]+)"/g),m=>m[1])];
  const missing=messages.filter(s=>!common.has(s)&&!Object.hasOwn(translations,s));
  assert.deepEqual([...new Set(missing)],[]);
});
test('translated templates keep the same interpolation variables',()=>{
  const parameters=s=>[...s.matchAll(/\{(\w+)\}/g)].map(m=>m[1]).sort();
  for(const [it,en] of Object.entries(translations))assert.deepEqual(parameters(en),parameters(it),it);
});
