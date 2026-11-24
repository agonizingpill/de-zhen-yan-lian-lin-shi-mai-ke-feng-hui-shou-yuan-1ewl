import {el} from '../dom.js';
import {mixer} from '../audio-api.js';
import {desk,findingStates} from '../audio-state.js';
import {choices,field,run,write} from '../audio-form.js';
import {status,titleBlock} from '../widgets.js';
import {diagnosis,metrics} from '../components/samples.js';

export async function findings(root,role) {
  const edit=el('section',{class:'action'});
  const box=el('section',{class:'ledger'});
  async function load(message) {
    const [clips,items]=await Promise.all([mixer.windows(),mixer.findings()]);
    const active=clips.filter(clip=>clip.purpose==='live');
    const result=el('div',{class:'live-review'});
    const pending=items.filter(item=>item.state==='pending');
    const result2=el('div',{class:'pending-review'});
    if (pending.length) result2.replaceChildren(el('p',{class:'hint'},'补录已使这些诊断失效，需用新证据复判：'),
      ...pending.map(item=>el('code',{},item.code+' · '+item.focus_window)));
    box.replaceChildren(el('h2',{},'邻域局部密度与同频检查'),result2,result,
      ...items.map(item=>el('details',{class:'clip'},el('summary',{},item.code+' · '+item.focus_window+
        ' · '+findingStates[item.state]),diagnosis(item))));
    edit.replaceChildren(el('h2',{},'选择试听窗'),message?status(message,'ok'):null);
    if (!write(role)) {edit.append(status('只读账号可展开已签发现。'));return;}
    edit.append(run('diagnose',[
      choices('window','窗口',active.map(x=>[x.code,x.code+' / '+x.point]),desk.window),
    ],'并行证据诊断',async values=>{
      const focus=active.find(item=>item.code===values.get('window'));
      const job=await mixer.diagnosis({window:focus.code});
      const report=await mixer.wait(job.token,item=>{
        if(item.status==='queued') result.replaceChildren(status('邻域密度计算中'));
      });
      if(report.status!=='ready') throw new Error(report.detail);
      const notes=items.filter(item=>item.focus_window===focus.code);
      const rejudge=notes.find(item=>item.state==='pending');
      const evidence=report.input&&report.input.evidence||[];
      result.replaceChildren(el('h3',{class:'mono'},focus.code),metrics(focus),diagnosis(report.result),
        el('p',{},'参考 '+report.result.reference_windows+' 个窗，正常下限 '+report.result.threshold),
        evidence.length ? el('p',{class:'hint'},'同期证据 '+evidence.join(' · ')) : null,
        run('save-finding',[field('code','发现编号',{placeholder:rejudge?'FD-1124-HUB-R2':'FD-1124-HUB'})],
          rejudge?'复判并重新签发':'签发现',async data=>{
          const item=await mixer.save({code:data.get('code'),token:job.token});
          desk.finding=item.code;
          await load(item.code+' 已签入'+(item.replaces?'，替代 '+item.replaces:'')+'。');
        }));
    }));
  }
  root.replaceChildren(titleBlock('安澜 · 邻域诊断','回授源与同频证据',
    '异常先核对同一时间窗的主峰。迟到补录会改变同期证据，失效的旧结论须用新证据复判。'),
    el('div',{class:'mix invert'},edit,box));
  await load();
}
