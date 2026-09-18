import pg from 'pg';
import { analyze, gdDate } from './_lib/analyze.js';
const { Pool } = pg;
const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 1, ssl: { rejectUnauthorized: false } });

export const config = { maxDuration: 30 };

export default async function handler(req,res){
  if (req.method !== 'POST') return res.status(405).json({ok:false,error:'method_not_allowed'});
  const client = await pool.connect();
  let runId = null;
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
    const q = String(body.query || '').slice(0,500);
    const articles = Array.isArray(body.articles) ? body.articles.slice(0,150) : [];
    const rr = await client.query(
      'INSERT INTO collection_runs(source,query,status) VALUES($1,$2,$3) RETURNING id',
      ['browser-gdelt', q, 'running']
    );
    runId = rr.rows[0].id;

    const prepared = articles.map((a,i)=>{
      const x = analyze((a.title||'')+' '+(a.domain||''));
      const p = gdDate(a.seendate);
      return {
        source:'GDELT',
        source_type:'news',
        external_id:'browser-'+runId+'-'+i,
        url:a.url||null,
        title:a.title||'Untitled',
        domain:a.domain||null,
        published_at:p.toISOString(),
        sentiment:x.sentiment,
        sentiment_score:x.score,
        topic:x.topic,
        risk_score:x.risk,
        metadata:{language:a.language||null,sourcecountry:a.sourcecountry||null}
      };
    }).filter(x=>x.url);

    let inserted = 0;
    if (prepared.length) {
      const bulk = await client.query(`
        WITH input AS (
          SELECT * FROM jsonb_to_recordset($1::jsonb) AS x(
            source text, source_type text, external_id text, url text, title text, domain text,
            published_at timestamptz, sentiment text, sentiment_score numeric, topic text,
            risk_score integer, metadata jsonb
          )
        )
        INSERT INTO mentions(source,source_type,external_id,url,title,domain,published_at,sentiment,sentiment_score,topic,risk_score,metadata)
        SELECT source,source_type,external_id,url,title,domain,published_at,sentiment,sentiment_score,topic,risk_score,metadata
        FROM input
        ON CONFLICT(url) DO UPDATE SET
          title=EXCLUDED.title,
          domain=EXCLUDED.domain,
          published_at=EXCLUDED.published_at,
          sentiment=EXCLUDED.sentiment,
          sentiment_score=EXCLUDED.sentiment_score,
          topic=EXCLUDED.topic,
          risk_score=EXCLUDED.risk_score,
          collected_at=now(),
          metadata=EXCLUDED.metadata
        RETURNING (xmax=0) AS inserted
      `, [JSON.stringify(prepared)]);
      inserted = bulk.rows.filter(r=>r.inserted).length;
    }

    await client.query(
      'UPDATE collection_runs SET finished_at=now(),fetched_count=$1,inserted_count=$2,status=$3 WHERE id=$4',
      [prepared.length,inserted,'success',runId]
    );
    return res.status(200).json({ok:true,fetched:prepared.length,inserted,runId});
  } catch (e) {
    if (runId) {
      await client.query(
        'UPDATE collection_runs SET finished_at=now(),status=$1,error=$2 WHERE id=$3',
        ['error',String(e?.message||e),runId]
      ).catch(()=>{});
    }
    return res.status(500).json({ok:false,error:String(e?.message||e)});
  } finally {
    client.release();
  }
}
