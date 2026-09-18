export default async function handler(req,res){
  try{
    const q=String(req.query.q||'"BP Tapera" OR Tapera OR FLPP OR "rumah subsidi" OR "KPR subsidi"').slice(0,500);
    const days=Math.max(1,Math.min(30,Number(req.query.days||7)));
    const u=new URL('https://api.gdeltproject.org/api/v2/doc/doc');
    u.searchParams.set('query',q);u.searchParams.set('mode','artlist');u.searchParams.set('format','json');u.searchParams.set('maxrecords','250');u.searchParams.set('sort','datedesc');u.searchParams.set('timespan',days===1?'24h':days<=7?'7d':'1month');
    const r=await fetch(u,{headers:{'user-agent':'SentimentCommandCenter/1.0'},signal:AbortSignal.timeout(15000)});
    if(!r.ok)return res.status(r.status).json({error:'Upstream GDELT error',status:r.status});
    const data=await r.json();res.setHeader('Cache-Control','s-maxage=240, stale-while-revalidate=600');return res.status(200).json(data);
  }catch(e){return res.status(500).json({error:'collector_failed',message:String(e.message||e)})}
}
