import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 2, ssl: { rejectUnauthorized: false } });

const POS=['baik','bagus','membantu','berhasil','meningkat','apresiasi','mudah','cepat','terjangkau','positif','dukung','manfaat','efektif','tepat sasaran','lancar','solusi','kemudahan','puas'];
const NEG=['buruk','rusak','bocor','retak','gagal','sulit','lama','lambat','keluhan','kecewa','masalah','mahal','penipuan','fraud','korupsi','mangkrak','tidak layak','ditolak','banjir','komplain','protes','kritik','krisis','viral','parah'];
const TOPICS=[['Kualitas Rumah',['bocor','retak','bangunan','atap','dinding','struktur']],['Kualitas Lingkungan',['drainase','jalan lingkungan','banjir','fasum','fasos']],['Proses Pengajuan',['pengajuan','proses','akad','verifikasi','approval','menunggu','lama']],['Persyaratan',['syarat','persyaratan','dokumen','penghasilan','mbr']],['Harga & Biaya',['harga','biaya','cicilan','uang muka','dp','angsuran']],['Bank Penyalur',['bank','kpr','penyalur','kredit']],['Penyaluran FLPP',['flpp','penyaluran','realisasi','pembiayaan']],['Data & Ketepatan Sasaran',['data','dtsen','tepat sasaran','validasi','integrasi']],['Target Program',['target','program','3 juta rumah','tiga juta rumah']]];

function analyze(text=''){text=String(text).toLowerCase();let p=POS.filter(w=>text.includes(w)).length,n=NEG.filter(w=>text.includes(w)).length,score=(p-n)/Math.max(2,p+n),sentiment=score>.16?'positive':score<-.16?'negative':'neutral',topic='General Conversation',best=0;for(const[t,ws]of TOPICS){let h=ws.filter(w=>text.includes(w)).length;if(h>best){best=h;topic=t}}let crisis=['viral','bocor','rusak','penipuan','fraud','korupsi','gagal','banjir','protes','parah','krisis'].filter(w=>text.includes(w)).length;let risk=Math.min(99,Math.max(5,Math.round(Math.max(0,-score)*60+crisis*8+8)));return{score,sentiment,topic,risk}}
function decodeXml(s=''){return String(s).replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g,'$1').replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;|&apos;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>')}
function tag(block,name){const m=block.match(new RegExp('<'+name+'(?:\\s[^>]*)?>([\\s\\S]*?)<\\/'+name+'>','i'));return m?decodeXml(m[1]).trim():''}
function parseRss(xml){return (String(xml).match(/<item>[\s\S]*?<\/item>/gi)||[]).map((item,i)=>({title:tag(item,'title')||'Untitled',url:tag(item,'link'),domain:tag(item,'source')||'News',published_at:tag(item,'pubDate')?new Date(tag(item,'pubDate')):new Date(),external_id:'rss-'+Date.now()+'-'+i})).filter(x=>x.url&&!Number.isNaN(x.published_at.getTime()))}
async function fetchRss(url,label){const r=await fetch(url,{headers:{'user-agent':'Mozilla/5.0 (compatible; SentimentCommandCenter/3.0)','accept':'application/rss+xml, application/xml, text/xml, */*'},redirect:'follow',signal:AbortSignal.timeout(12000)});const text=await r.text();if(!r.ok)throw new Error(label+' HTTP '+r.status);if(!/<item>[\s\S]*?<\/item>/i.test(text))throw new Error(label+' returned no RSS');return{text,label}}

export const config = { maxDuration: 30 };

export default async function handler(req,res){
  const action=String(req.query.action||'health');
  if(!process.env.DATABASE_URL)return res.status(500).json({ok:false,error:'DATABASE_URL_missing'});
  if(action==='health'){
    try{const {rows}=await pool.query("select now() now,(select count(*)::int from mentions) mentions,(select count(*)::int from collection_runs) runs");return res.status(200).json({ok:true,...rows[0]})}
    catch(e){return res.status(500).json({ok:false,error:String(e?.message||e)})}
  }
  if(action==='history'){
    const days=Math.max(1,Math.min(90,Number(req.query.days||30)));
    const client=await pool.connect();
    try{
      const [summary,timeline,topics,recent,runs]=await Promise.all([
        client.query("select count(*)::int total,count(*) filter(where sentiment='positive')::int positive,count(*) filter(where sentiment='neutral')::int neutral,count(*) filter(where sentiment='negative')::int negative,coalesce(round(avg(sentiment_score)*100,1),0)::float sentiment_index,coalesce(max(risk_score),0)::int risk_peak from mentions where published_at>=now()-($1::int*interval '1 day')",[days]),
        client.query("select date_trunc('day',published_at) bucket,count(*)::int total,count(*) filter(where sentiment='positive')::int positive,count(*) filter(where sentiment='neutral')::int neutral,count(*) filter(where sentiment='negative')::int negative from mentions where published_at>=now()-($1::int*interval '1 day') group by 1 order by 1",[days]),
        client.query("select topic,count(*)::int current_total,count(*) filter(where sentiment='negative')::int negative,coalesce(max(risk_score),0)::int risk_peak from mentions where published_at>=now()-($1::int*interval '1 day') group by topic order by current_total desc limit 12",[days]),
        client.query("select id,source,url,title,domain,published_at,sentiment,sentiment_score::float,topic,risk_score from mentions where published_at>=now()-($1::int*interval '1 day') order by published_at desc nulls last limit 20",[days]),
        client.query("select id,source,started_at,finished_at,fetched_count,inserted_count,status,error from collection_runs order by id desc limit 12")
      ]);
      return res.status(200).json({ok:true,days,summary:summary.rows[0],timeline:timeline.rows,topics:topics.rows,mentions:recent.rows,runs:runs.rows,comparison:{total_growth_pct:0,negative_growth_pct:0,sentiment_index_delta:0,risk_peak_delta:0},anomaly:{score:0,level:'LOW',recent_6h:0,baseline_6h_avg:0,volume_ratio:0,recent_negative_share:0,baseline_negative_share:0,risk_peak:Number(summary.rows[0].risk_peak||0)}});
    }catch(e){return res.status(500).json({ok:false,error:String(e?.message||e)})}finally{client.release()}
  }
  if(action!=='collect')return res.status(400).json({ok:false,error:'unknown_action'});

  const q=String(req.query.q||'"BP Tapera" OR Tapera OR FLPP OR "rumah subsidi" OR "KPR subsidi"').slice(0,500);
  const days=Math.max(1,Math.min(30,Number(req.query.days||7)));
  const client=await pool.connect();let runId=null;
  try{
    const rr=await client.query("insert into collection_runs(source,query,status) values($1,$2,'running') returning id",['vercel-news-rss',q]);runId=rr.rows[0].id;
    const when=days<=1?'1d':days<=7?'7d':'30d';
    const g=new URL('https://news.google.com/rss/search');g.searchParams.set('q',q+' when:'+when);g.searchParams.set('hl','id');g.searchParams.set('gl','ID');g.searchParams.set('ceid','ID:id');
    const b=new URL('https://www.bing.com/news/search');b.searchParams.set('q',q);b.searchParams.set('format','rss');b.searchParams.set('setlang','id-ID');
    let result;
    try{result=await Promise.any([fetchRss(g,'Google News'),fetchRss(b,'Bing News')])}
    catch(e){const msg='all_sources_failed: '+String(e?.message||e);await client.query("update collection_runs set finished_at=now(),status='error',error=$1 where id=$2",[msg,runId]);return res.status(502).json({ok:false,runId,error:msg})}
    const parsed=parseRss(result.text).slice(0,150);
    const prepared=parsed.map((a,i)=>{const x=analyze((a.title||'')+' '+(a.domain||''));return{source:result.label,source_type:'news',external_id:a.external_id,url:a.url,title:a.title,domain:a.domain,published_at:a.published_at.toISOString(),sentiment:x.sentiment,sentiment_score:x.score,topic:x.topic,risk_score:x.risk,metadata:{aggregator:result.label}}});
    let inserted=0;
    if(prepared.length){
      const bulk=await client.query(`with input as (select * from jsonb_to_recordset($1::jsonb) as x(source text,source_type text,external_id text,url text,title text,domain text,published_at timestamptz,sentiment text,sentiment_score numeric,topic text,risk_score integer,metadata jsonb)) insert into mentions(source,source_type,external_id,url,title,domain,published_at,sentiment,sentiment_score,topic,risk_score,metadata) select source,source_type,external_id,url,title,domain,published_at,sentiment,sentiment_score,topic,risk_score,metadata from input on conflict(url) do update set title=excluded.title,domain=excluded.domain,published_at=excluded.published_at,sentiment=excluded.sentiment,sentiment_score=excluded.sentiment_score,topic=excluded.topic,risk_score=excluded.risk_score,collected_at=now(),metadata=excluded.metadata returning (xmax=0) inserted`,[JSON.stringify(prepared)]);
      inserted=bulk.rows.filter(x=>x.inserted).length;
    }
    await client.query("update collection_runs set finished_at=now(),fetched_count=$1,inserted_count=$2,status='success' where id=$3",[prepared.length,inserted,runId]);
    return res.status(200).json({ok:true,runId,provider:result.label,fetched:prepared.length,inserted,articles:prepared.map(x=>({title:x.title,url:x.url,domain:x.domain,seendate:x.published_at,sentiment:x.sentiment,score:Number(x.sentiment_score),topic:x.topic,risk:x.risk_score}))});
  }catch(e){if(runId)await client.query("update collection_runs set finished_at=now(),status='error',error=$1 where id=$2",[String(e?.message||e),runId]).catch(()=>{});return res.status(500).json({ok:false,runId,error:String(e?.message||e)})}finally{client.release()}
}