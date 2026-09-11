const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('dist/app.js','utf8').split('// ALARM CORE START')[1].split('// ALARM CORE END')[0];
const core=vm.runInNewContext(source+';({quietNow,alertDue})',{Date});
const defaults={enabled:true,manual:false,schedule:true,start:'00:00',end:'06:00'};
const at=(hour,minute=0)=>new Date(2026,8,11,hour,minute);
test('default quiet hours include midnight and exclude 06:00',()=>{
  assert.equal(core.quietNow(defaults,at(0)),true);
  assert.equal(core.quietNow(defaults,at(5,59)),true);
  assert.equal(core.quietNow(defaults,at(6)),false);
  assert.equal(core.quietNow(defaults,at(23,59)),false);
});
test('overnight, daytime and manual quiet hours',()=>{
  const overnight={...defaults,start:'22:00',end:'07:00'};
  for(const h of [22,23,0,6])assert.equal(core.quietNow(overnight,at(h)),true);
  for(const h of [7,12,21])assert.equal(core.quietNow(overnight,at(h)),false);
  assert.equal(core.quietNow({...defaults,start:'12:00',end:'14:00'},at(13)),true);
  assert.equal(core.quietNow({...defaults,manual:true,schedule:false},at(12)),true);
  assert.equal(core.quietNow({...defaults,schedule:false},at(1)),false);
});
test('repeat every five minutes, never for unknown or recovered targets',()=>{
  const now=+at(12),target={state:'active'};
  assert.equal(core.alertDue(target,undefined,defaults,now),true);
  assert.equal(core.alertDue(target,now-299999,defaults,now),false);
  assert.equal(core.alertDue(target,now-300000,defaults,now),true);
  for(const state of ['unknown','pending','normal'])assert.equal(core.alertDue({state},undefined,defaults,now),false);
  assert.equal(core.alertDue(target,undefined,{...defaults,enabled:false},now),false);
});
test('quiet hours suppress overdue reminders; one reminder is due at the end',()=>{
  const target={state:'active'},last=+at(0)-600000;
  assert.equal(core.alertDue(target,last,defaults,+at(5,59)),false);
  assert.equal(core.alertDue(target,last,defaults,+at(6)),true);
  assert.equal(core.alertDue(target,+at(6),defaults,+at(6,1)),false);
  const persisted=JSON.parse(JSON.stringify({last:+at(6)}));
  assert.equal(core.alertDue(target,persisted.last,defaults,+at(6,5)),true);
});
function deliveryFixture(settings) {
  const app=fs.readFileSync('dist/app.js','utf8');
  const delivery=app.slice(app.indexOf('function soundAlarm()'),app.indexOf('async function pollAlarms()'));
  const counts={notifications:0,tones:0};
  class Notification {static permission='granted';constructor(){counts.notifications++;}}
  const audioContext={state:'running',currentTime:0,destination:{},
    createOscillator:()=>({frequency:{},connect(){},start(){counts.tones++;},stop(){}}),
    createGain:()=>({gain:{setValueAtTime(){},linearRampToValueAtTime(){}},connect(){}})};
  const fn=vm.runInNewContext(source+delivery+';deliverAlarm',{
    Date,alarmSettings:{...defaults,schedule:false,sound:true,...settings},audioContext,Notification,window:{Notification}});
  return {counts,send:()=>fn([{name:'Test host'}])};
}
test('delivery sends a notification and three audio tones when allowed',()=>{
  const fixture=deliveryFixture({});assert.equal(fixture.send(),true);
  assert.deepEqual(fixture.counts,{notifications:1,tones:3});
});
test('manual quiet mode and disabled alarms suppress both delivery channels',()=>{
  for(const settings of [{manual:true},{enabled:false}]) {
    const fixture=deliveryFixture(settings);assert.equal(fixture.send(),false);
    assert.deepEqual(fixture.counts,{notifications:0,tones:0});
  }
});
test('sound preference leaves native notifications available',()=>{
  const fixture=deliveryFixture({sound:false});assert.equal(fixture.send(),true);
  assert.deepEqual(fixture.counts,{notifications:1,tones:0});
});
