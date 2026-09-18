import pg from 'pg';
import { analyze } from './_lib/analyze.js';

const { Pool } = pg;
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 1,
  ssl: { rejectUnauthorized: false }
});

function decodeXml(s='') {
  return String(s)
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

function tag(block, name) {
  const m = block.match(new RegExp('<' + name + '(?:\\s[^>]*)?>([\\s\\S]*?)<\\/' + name + '>', 'i'));
  return m ? decodeXml(m[1]).trim() : '';
}

function attr(block, name, attrName) {
  const m = block.match(new RegExp('<' + name + '\\s+[^>]*' + attrName + '=["\\']([^"\\']+)["\\'][^>]*>', 'i'));
  return m ? decodeXml(m[1]).trim() : '';
}

function parseGoogleNews(xml) {
  const items = String(xml).match(/<item>[\s\S]*?<\/item>/gi) || [];
  return items.map((item, i) => {
    const title = tag(item, 'title') || 'Untitled';
    const url = tag(item, 'link');
    const published = tag(item, 'pubDate');
    const publisher = tag(item, 'source') || 'Google News';
    const publisherUrl = attr(item, 'source', 'url');
    return {
      external_id: 'gn-' + Date.now() + '-' + i,
      title,
      url,
      domain: publisher,
      source_url: publisherUrl,
      published_at: published ? new Date(published) : new Date()
    };
  }).filter(x => x.url);
}

function toClientArticles(rows) {
  return rows.map(x => ({
    title: x.title,
    url: x.url,
    domain: x.domain || 'Google News',
    seendate: x.published_at
  }));
}

export default async function handler(req, res) {
  const q = String(req.query.q || '"BP Tapera" OR Tapera OR FLPP OR "rumah subsidi" OR "KPR subsidi"').slice(0, 500);
  const days = Math.max(1, Math.min(30, Number(req.query.days || 7)));
  const client = await pool.connect();
  let runId = null;

  try {
    await client.query(`
      UPDATE collection_runs
      SET status='error', finished_at=now(), error='stale run / function interrupted'
      WHERE status='running' AND started_at < now() - interval '2 minutes'
    `);

    const recentRun = await client.query(`
      SELECT id
      FROM collection_runs
      WHERE source='google-news-rss'
        AND query=$1
        AND status='success'
        AND finished_at > now() - interval '2 minutes'
      ORDER BY id DESC LIMIT 1
    `, [q]);

    if (recentRun.rowCount) {
      const cached = await client.query(`
        SELECT title,url,domain,published_at
        FROM mentions
        WHERE published_at >= now() - ($1::int * interval '1 day')
        ORDER BY published_at DESC
        LIMIT 250
      `, [days]);

      res.setHeader('Cache-Control', 'no-store');
      return res.status(200).json({
        ok: true,
        cached: true,
        fetched: cached.rowCount,
        inserted: 0,
        runId: recentRun.rows[0].id,
        articles: toClientArticles(cached.rows)
      });
    }

    const rr = await client.query(
      'INSERT INTO collection_runs(source,query,status) VALUES($1,$2,$3) RETURNING id',
      ['google-news-rss', q, 'running']
    );
    runId = rr.rows[0].id;

    const when = days <= 1 ? '1d' : days <= 7 ? '7d' : '30d';
    const feedUrl = new URL('https://news.google.com/rss/search');
    feedUrl.searchParams.set('q', q + ' when:' + when);
    feedUrl.searchParams.set('hl', 'id');
    feedUrl.searchParams.set('gl', 'ID');
    feedUrl.searchParams.set('ceid', 'ID:id');

    const r = await fetch(feedUrl, {
      headers: {
        'user-agent': 'Mozilla/5.0 SentimentCommandCenter/1.0',
        'accept': 'application/rss+xml, application/xml, text/xml'
      },
      signal: AbortSignal.timeout(12000)
    });
    if (!r.ok) throw new Error('Google News RSS HTTP ' + r.status);

    const xml = await r.text();
    const parsed = parseGoogleNews(xml).slice(0, 250);

    const prepared = parsed.map(a => {
      const x = analyze((a.title || '') + ' ' + (a.domain || ''));
      return {
        source: 'Google News',
        source_type: 'news',
        external_id: a.external_id,
        url: a.url,
        title: a.title,
        domain: a.domain,
        published_at: a.published_at.toISOString(),
        sentiment: x.sentiment,
        sentiment_score: x.score,
        topic: x.topic,
        risk_score: x.risk,
        metadata: {
          aggregator: 'google-news-rss',
          publisher_url: a.source_url || null
        }
      };
    });

    let inserted = 0;

    if (prepared.length) {
      const bulk = await client.query(`
        WITH input AS (
          SELECT *
          FROM jsonb_to_recordset($1::jsonb) AS x(
            source text,
            source_type text,
            external_id text,
            url text,
            title text,
            domain text,
            published_at timestamptz,
            sentiment text,
            sentiment_score numeric,
            topic text,
            risk_score integer,
            metadata jsonb
          )
        )
        INSERT INTO mentions(
          source, source_type, external_id, url, title, domain, published_at,
          sentiment, sentiment_score, topic, risk_score, metadata
        )
        SELECT
          source, source_type, external_id, url, title, domain, published_at,
          sentiment, sentiment_score, topic, risk_score, metadata
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

      inserted = bulk.rows.filter(x => x.inserted).length;
    }

    await client.query(
      'UPDATE collection_runs SET finished_at=now(),fetched_count=$1,inserted_count=$2,status=$3 WHERE id=$4',
      [prepared.length, inserted, 'success', runId]
    );

    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).json({
      ok: true,
      cached: false,
      fetched: prepared.length,
      inserted,
      runId,
      articles: toClientArticles(prepared)
    });

  } catch (e) {
    if (runId) {
      await client.query(
        'UPDATE collection_runs SET finished_at=now(),status=$1,error=$2 WHERE id=$3',
        ['error', String(e?.message || e), runId]
      ).catch(() => {});
    }

    return res.status(500).json({
      ok: false,
      error: String(e?.message || e)
    });
  } finally {
    client.release();
  }
}
