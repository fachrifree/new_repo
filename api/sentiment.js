export const config = { maxDuration: 30 };

const NEON_FN = 'https://br-lucky-king-b3liquce-sentimentapi.compute.c-4.ap-southeast-1.aws.neon.tech/';

export default async function handler(req, res) {
  try {
    const u = new URL(NEON_FN);
    for (const [k, v] of Object.entries(req.query || {})) {
      if (Array.isArray(v)) v.forEach(x => u.searchParams.append(k, String(x)));
      else if (v != null) u.searchParams.set(k, String(v));
    }

    const upstream = await fetch(u, {
      method: 'GET',
      headers: {
        'accept': 'application/json',
        'user-agent': 'SentimentCommandCenter-VercelProxy/1.0'
      },
      signal: AbortSignal.timeout(20000)
    });

    const text = await upstream.text();
    res.statusCode = upstream.status;
    res.setHeader('content-type', upstream.headers.get('content-type') || 'application/json; charset=utf-8');
    res.setHeader('cache-control', 'no-store');
    return res.end(text);
  } catch (e) {
    return res.status(502).json({ ok:false, error:'neon_proxy_failed', message:String(e?.message || e) });
  }
}
