import {el} from '../dom.js';
import {feature,findingStates,labels,purpose} from '../audio-state.js';
import {badge} from './badge.js';

export function metrics(clip) {
  return el('div',{class:'sampler','aria-label':'样本声检特征'},Object.entries(feature).flatMap(([key,label])=>
    [el('span',{},label),el('meter',{min:'0',max:'1',value:clip[key],'aria-label':label}),
      el('code',{},clip[key].toFixed(2))]));
}
export function sample(clip) {
  return el('details',{class:'clip'},
    el('summary',{},clip.code+' · '+clip.point+' · '+clip.slot+' / '+clip.frequency+' Hz · '+purpose[clip.purpose]),
    metrics(clip));
}
export function diagnosis(item) {
  return el('div',{class:'note'},el('span',{class:'verdict'},badge(labels,item.category),
    item.state?badge(findingStates,item.state):null),
    el('p',{class:'mono'},'LOF '+item.score.toFixed(4)+' · 邻居 '+item.neighbors),
    el('p',{},item.shared_points.length ? '同期相符麦位 '+item.shared_points.join(' · ') : '没有同期相符的麦位。'),
    item.evidence&&item.evidence.length ? el('p',{class:'hint'},'签发证据 '+item.evidence.join(' · ')) : null,
    item.replaces ? el('p',{class:'hint'},'替代旧结论 '+item.replaces) : null);
}
