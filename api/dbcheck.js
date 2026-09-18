import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({ connectionString: process.env.DATABASE_URL, max:1, ssl:{rejectUnauthorized:false} });

export default async function handler(req,res){
  if(!process.env.DATABASE_URL){
    return res.status(500).json({ok:false,error:'DATABASE_URL_missing'});
  }
  const client = await pool.connect();
  try{
    const r = await client.query(
      "INSERT INTO collection_runs(source,query,status,finished_at,fetched_count,inserted_count) VALUES($1,$2,$3,now(),0,0) RETURNING id,started_at,finished_at,status",
      ['diagnostic','dbcheck','success']
    );
    return res.status(200).json({ok:true,row:r.rows[0]});
  }catch(e){
    return res.status(500).json({ok:false,error:String(e?.message||e)});
  }finally{
    client.release();
  }
}
