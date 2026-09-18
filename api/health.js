export default function handler(req,res){return res.status(200).json({ok:true,service:'sentiment-command-center',dbConfigured:Boolean(process.env.DATABASE_URL),timestamp:new Date().toISOString()})}
