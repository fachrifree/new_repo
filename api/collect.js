import pg from 'pg';
import { analyze, gdDate } from './_lib/analyze.js';
const { Pool } = pg;
const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 1, ssl:{rejectUnauthorized:false} });

export default async function handler(req,res){
  const q=String(req.query.q||'"BP Tapera" OR Tapera OR FLPP OR "rumah subsidi" OR "KPR subsidi"').slice(0,500);
  const days=Math.max(1,Math.min(30,Number(req.query.days||7)));
  const client=await pool.connect();
  let runId=null;
  try{
    const rr=await client.query('INSERT INTO collection_runs(source,query,status) VALUES($1,$2,$3) RETURNING id',['gdelt',q,'running']);
    runId=rr.rows[0].id;
    const u=new URL('https://api.gdeltproject.org/api/v2/doc/doc');
    u.searchParams.set('query',q);u.searchParams.set('mode','artlist');u.searchParams.set('format','json');u.searchParams.set('maxrecords','250');u.searchParams.set('sort','datedesc');u.searchParams.set('timespan',days===1?'24h':days<=7?'7d':'1month');
    const r=await fetch(u,{headers:{'user-agent':'SentimentCommandCenter/1.0'},signal:AbortSignal.timeout(15000)});
    if(!r.ok) throw new Error('GDELT HTTP '+r.status);
    const j=await r.json(); const rows=j.articles||[]; let inserted=0;
    for(const a of rows){
      const x=analyze((a.title||'')+' '+(a.domain||''));
      const pub=gdDate(a.seendate);
      const out=await client.query(`
        INSERT INTO mentions(source,source_type,url,title,domain,published_at,sentiment,sentiment_score,topic,risk_score,metadata)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ON CONFLICT(url) DO UPDATE SET title=EXCLUDED.title,domain=EXCLUDED.domain,published_at=EXCLUDED.published_at,
          sentiment=EXCLUDED.sentiment,sentiment_score=EXCLUDED.sentiment_score,topic=EXCLUDED.topic,risk_score=EXCLUDED.risk_score,
          collected_at=now(),metadata=EXCLUDED.metadata
        RETURNING (xmax=0) AS inserted
      `,['GDELT','news',a.url||null,a.title||'Untitled',a.domain||null,pub,x.sentiment,x.score,x.topic,x.risk,{language:a.language||null,sourcecountry:a.sourcecountry||null}]);
      if(out.rows[0]?.inserted) inserted++;
    }
    await client.query('UPDATE collection_runs SET finished_at=now(),fetched_count=$1,inserted_count=$2,status=$3 WHERE id=$4',[rows.length,inserted,'success',runId]);
    res.setHeader('Cache-Control','no-store');
    return res.status(200).json({ok:true,fetched:rows.length,inserted,runId,articles:rows});
  }catch(e){
    if(runId) await client.query('UPDATE collection_runs SET finished_at=now(),status=$1,error=$2 WHERE id=$3',['error',String(e.message||e),runId]).catch(()=>{});
    return res.status(500).json({ok:false,error:String(e.message||e)});
  }finally{client.release()}
}
