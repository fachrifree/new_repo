import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 1, ssl: { rejectUnauthorized: false } });

const pct = (a,b) => b ? Math.round(((a-b)/b)*1000)/10 : (a ? 100 : 0);
const share = (a,b) => b ? Math.round((a/b)*1000)/10 : 0;

export default async function handler(req,res){
  const days = Math.max(1, Math.min(90, Number(req.query.days || 30)));
  const bucket = days <= 2 ? 'hour' : 'day';
  const client = await pool.connect();
  try {
    const [current, previous, timeline, topics, recent, runs, pulse] = await Promise.all([
      client.query(`SELECT count(*)::int total,
        count(*) FILTER (WHERE sentiment='positive')::int positive,
        count(*) FILTER (WHERE sentiment='neutral')::int neutral,
        count(*) FILTER (WHERE sentiment='negative')::int negative,
        coalesce(round(avg(sentiment_score)*100,1),0)::float sentiment_index,
        coalesce(max(risk_score),0)::int risk_peak
        FROM mentions
        WHERE published_at >= now() - ($1::int * interval '1 day')`, [days]),
      client.query(`SELECT count(*)::int total,
        count(*) FILTER (WHERE sentiment='positive')::int positive,
        count(*) FILTER (WHERE sentiment='neutral')::int neutral,
        count(*) FILTER (WHERE sentiment='negative')::int negative,
        coalesce(round(avg(sentiment_score)*100,1),0)::float sentiment_index,
        coalesce(max(risk_score),0)::int risk_peak
        FROM mentions
        WHERE published_at >= now() - ($1::int * interval '2 day')
          AND published_at < now() - ($1::int * interval '1 day')`, [days]),
      client.query(`SELECT date_trunc('${bucket}',published_at) bucket,
        count(*)::int total,
        count(*) FILTER (WHERE sentiment='positive')::int positive,
        count(*) FILTER (WHERE sentiment='neutral')::int neutral,
        count(*) FILTER (WHERE sentiment='negative')::int negative,
        coalesce(round(avg(sentiment_score)*100,1),0)::float sentiment_index,
        coalesce(max(risk_score),0)::int risk_peak
        FROM mentions
        WHERE published_at >= now() - ($1::int * interval '1 day')
        GROUP BY 1 ORDER BY 1`, [days]),
      client.query(`SELECT topic,
        count(*) FILTER (WHERE published_at >= now() - ($1::int * interval '1 day'))::int current_total,
        count(*) FILTER (WHERE published_at >= now() - ($1::int * interval '2 day')
                           AND published_at < now() - ($1::int * interval '1 day'))::int previous_total,
        count(*) FILTER (WHERE published_at >= now() - ($1::int * interval '1 day')
                           AND sentiment='negative')::int negative,
        coalesce(max(risk_score) FILTER (WHERE published_at >= now() - ($1::int * interval '1 day')),0)::int risk_peak
        FROM mentions
        WHERE published_at >= now() - ($1::int * interval '2 day')
        GROUP BY topic
        ORDER BY current_total DESC
        LIMIT 12`, [days]),
      client.query(`SELECT id,source,url,title,domain,published_at,sentiment,
        sentiment_score::float,topic,risk_score
        FROM mentions
        WHERE published_at >= now() - ($1::int * interval '1 day')
        ORDER BY published_at DESC NULLS LAST LIMIT 20`, [days]),
      client.query(`SELECT id,source,started_at,finished_at,fetched_count,inserted_count,status,error
        FROM collection_runs ORDER BY id DESC LIMIT 12`),
      client.query(`SELECT
        count(*) FILTER (WHERE published_at >= now()-interval '6 hours')::int recent_total,
        count(*) FILTER (WHERE published_at >= now()-interval '48 hours'
                           AND published_at < now()-interval '6 hours')::int baseline_total,
        count(*) FILTER (WHERE published_at >= now()-interval '6 hours'
                           AND sentiment='negative')::int recent_negative,
        count(*) FILTER (WHERE published_at >= now()-interval '48 hours'
                           AND published_at < now()-interval '6 hours'
                           AND sentiment='negative')::int baseline_negative,
        coalesce(max(risk_score) FILTER (WHERE published_at >= now()-interval '6 hours'),0)::int recent_risk
        FROM mentions`)
    ]);

    const c = current.rows[0], p = previous.rows[0], pl = pulse.rows[0];
    const baselinePer6h = Number(pl.baseline_total || 0) / 7;
    const volumeRatio = baselinePer6h ? Number(pl.recent_total || 0) / baselinePer6h : (pl.recent_total ? 1 : 0);
    const recentNegShare = share(Number(pl.recent_negative||0), Number(pl.recent_total||0));
    const baselineNegShare = share(Number(pl.baseline_negative||0), Number(pl.baseline_total||0));
    const anomalyScore = Math.min(100, Math.round(
      Math.max(0, volumeRatio - 1) * 35 +
      Math.max(0, recentNegShare - baselineNegShare) * 0.7 +
      Math.max(0, Number(pl.recent_risk||0) - 40) * 0.5
    ));
    const anomalyLevel = anomalyScore >= 75 ? 'HIGH' : anomalyScore >= 45 ? 'MEDIUM' : 'LOW';

    const enrichedTopics = topics.rows.map(t => ({
      ...t,
      growth_pct: pct(Number(t.current_total||0), Number(t.previous_total||0))
    }));
    const comparison = {
      total_growth_pct: pct(Number(c.total||0), Number(p.total||0)),
      negative_growth_pct: pct(Number(c.negative||0), Number(p.negative||0)),
      sentiment_index_delta: Math.round((Number(c.sentiment_index||0)-Number(p.sentiment_index||0))*10)/10,
      risk_peak_delta: Number(c.risk_peak||0)-Number(p.risk_peak||0)
    };

    res.setHeader('Cache-Control','s-maxage=60, stale-while-revalidate=300');
    return res.status(200).json({
      ok:true, days, bucket,
      summary:c, previous:p, comparison,
      timeline:timeline.rows, topics:enrichedTopics, mentions:recent.rows, runs:runs.rows,
      anomaly:{
        score:anomalyScore, level:anomalyLevel,
        recent_6h:Number(pl.recent_total||0),
        baseline_6h_avg:Math.round(baselinePer6h*10)/10,
        volume_ratio:Math.round(volumeRatio*100)/100,
        recent_negative_share:recentNegShare,
        baseline_negative_share:baselineNegShare,
        risk_peak:Number(pl.recent_risk||0)
      }
    });
  } catch(e) {
    return res.status(500).json({ok:false,error:String(e.message||e)});
  } finally {
    client.release();
  }
}
