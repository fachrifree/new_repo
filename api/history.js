import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({ connectionString: process.env.DATABASE_URL, max:1, ssl:{rejectUnauthorized:false} });
export default async function handler(req,res){
  const days=Math.max(1,Math.min(90,Number(req.query.days||30)));
  const client=await pool.connect();
  try{
    const [summary,timeline,topics,runs] = await Promise.all([
      client.query(`SELECT count(*)::int total,
        count(*) FILTER(WHERE sentiment='positive')::int positive,
        count(*) FILTER(WHERE sentiment='neutral')::int neutral,
        count(*) FILTER(WHERE sentiment='negative')::int negative,
        coalesce(round(avg(sentiment_score)*100,1),0) sentiment_index,
        coalesce(max(risk_score),0)::int risk_peak
        FROM mentions WHERE published_at>=now()-($1||' days')::interval`,[days]),
      client.query(`SELECT date_trunc('day',published_at)::date day,count(*)::int total,
        count(*) FILTER(WHERE sentiment='positive')::int positive,
        count(*) FILTER(WHERE sentiment='neutral')::int neutral,
        count(*) FILTER(WHERE sentiment='negative')::int negative
        FROM mentions WHERE published_at>=now()-($1||' days')::interval GROUP BY 1 ORDER BY 1`,[days]),
      client.query(`SELECT topic,count(*)::int total,count(*) FILTER(WHERE sentiment='negative')::int negative,max(risk_score)::int risk_peak
        FROM mentions WHERE published_at>=now()-($1||' days')::interval GROUP BY topic ORDER BY total DESC LIMIT 12`,[days]),
      client.query(`SELECT id,source,started_at,finished_at,fetched_count,inserted_count,status,error FROM collection_runs ORDER BY id DESC LIMIT 10`)
    ]);
    res.setHeader('Cache-Control','s-maxage=60, stale-while-revalidate=300');
    return res.status(200).json({ok:true,days,summary:summary.rows[0],timeline:timeline.rows,topics:topics.rows,runs:runs.rows});
  }catch(e){return res.status(500).json({ok:false,error:String(e.message||e)})}finally{client.release()}
}
