function safeDate(v){ const d=new Date(v); return Number.isNaN(+d)?new Date(0):d; }
function pct(n,d){ return d ? (n/d)*100 : 0; }
function round(n,d=1){ const p=10**d; return Math.round(n*p)/p; }

export function filterMentions(rows,{q='',hours=168,source='',sentiment=''}){
  const since=Date.now()-hours*3600_000;
  const needle=q.trim().toLowerCase();
  return rows.filter(m=>{
    if (+safeDate(m.published_at)<since) return false;
    if (source && source!=='all' && m.platform!==source) return false;
    if (sentiment && sentiment!=='all' && m.sentiment!==sentiment) return false;
    if (needle && !`${m.title||''} ${m.content||''} ${m.source||''} ${m.topic||''}`.toLowerCase().includes(needle)) return false;
    return true;
  });
}

export function dashboardData(rows, filters, storageMode='unknown'){
  const mentions=filterMentions(rows,filters);
  const total=mentions.length;
  const pos=mentions.filter(m=>m.sentiment==='positive').length, neg=mentions.filter(m=>m.sentiment==='negative').length, neu=total-pos-neg;
  const avgScore=total?mentions.reduce((s,m)=>s+Number(m.sentiment_score||0),0)/total:0;
  const engagement=mentions.reduce((s,m)=>s+Number(m.engagement||0),0);
  const reach=mentions.reduce((s,m)=>s+Number(m.reach_estimate||0),0);
  const avgRisk=total?mentions.reduce((s,m)=>s+Number(m.risk_score||0),0)/total:0;

  const sourceMap=new Map(), issueMap=new Map();
  for(const m of mentions){
    sourceMap.set(m.platform,(sourceMap.get(m.platform)||0)+1);
    const key=m.topic||'Umum';
    const x=issueMap.get(key)||{topic:key,count:0,negative:0,risk:0,engagement:0};
    x.count++; x.negative+=m.sentiment==='negative'?1:0; x.risk+=Number(m.risk_score||0); x.engagement+=Number(m.engagement||0); issueMap.set(key,x);
  }
  const sources=[...sourceMap.entries()].map(([name,count])=>({name,count,share:round(pct(count,total),1)})).sort((a,b)=>b.count-a.count);
  const issues=[...issueMap.values()].map(x=>({...x,negative_share:round(pct(x.negative,x.count),1),avg_risk:round(x.risk/x.count,1)})).sort((a,b)=>(b.avg_risk*b.count)-(a.avg_risk*a.count)).slice(0,10);

  const bucketMs=filters.hours<=48?3*3600_000:24*3600_000;
  const buckets=new Map();
  for(const m of mentions){
    const t=Math.floor(+safeDate(m.published_at)/bucketMs)*bucketMs;
    const b=buckets.get(t)||{ts:new Date(t).toISOString(),positive:0,neutral:0,negative:0,total:0};
    b[m.sentiment]=(b[m.sentiment]||0)+1; b.total++; buckets.set(t,b);
  }
  const trend=[...buckets.values()].sort((a,b)=>a.ts.localeCompare(b.ts)).slice(-30);

  const now=Date.now(), d1=24*3600_000;
  const cur=mentions.filter(m=>+safeDate(m.published_at)>=now-d1).length;
  const prev=rows.filter(m=>{const t=+safeDate(m.published_at); return t>=now-2*d1 && t<now-d1;}).length;
  const volumeChange=prev?round(((cur-prev)/prev)*100,1):null;

  const alerts=mentions.filter(m=>Number(m.risk_score||0)>=70).sort((a,b)=>Number(b.risk_score)-Number(a.risk_score)).slice(0,8);
  const top=issues[0];
  const executiveBrief=total ? [
    `${total.toLocaleString('id-ID')} mention terpantau pada periode filter dengan sentiment index ${round(avgScore*100,1)}.`,
    `Porsi negatif ${round(pct(neg,total),1)}% dan positif ${round(pct(pos,total),1)}%.`,
    top?`Isu dengan kombinasi risiko dan volume tertinggi: ${top.topic} (${top.count} mention; ${top.negative_share}% negatif).`:'Belum ada isu dominan.',
    volumeChange===null?'Belum cukup data pembanding 24 jam sebelumnya.':`Volume 24 jam terakhir ${volumeChange>=0?'naik':'turun'} ${Math.abs(volumeChange)}% dibanding 24 jam sebelumnya.`
  ] : ['Belum ada data pada filter ini.'];

  return {
    generated_at:new Date().toISOString(), storage_mode:storageMode, filters,
    kpis:{total,positive:pos,neutral:neu,negative:neg,positive_share:round(pct(pos,total),1),negative_share:round(pct(neg,total),1),sentiment_index:round(avgScore*100,1),engagement,reach_estimate:reach,avg_risk:round(avgRisk,1),volume_change_24h:volumeChange},
    trend,sources,issues,alerts,executive_brief:executiveBrief,
    mentions:mentions.sort((a,b)=>safeDate(b.published_at)-safeDate(a.published_at)).slice(0,120)
  };
}
