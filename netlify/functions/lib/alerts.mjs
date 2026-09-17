import { env, numEnv } from './config.mjs';

export async function maybeSendTelegram(mentions) {
  const token=env('TELEGRAM_BOT_TOKEN'), chatId=env('TELEGRAM_CHAT_ID');
  if(!token||!chatId) return {sent:false,reason:'telegram-not-configured'};
  const threshold=numEnv('ALERT_RISK_THRESHOLD',78);
  const top=[...mentions].filter(m=>Number(m.risk_score||0)>=threshold).sort((a,b)=>b.risk_score-a.risk_score)[0];
  if(!top) return {sent:false,reason:'no-high-risk-item'};
  const text=[
    '🚨 SENTIMENT COMMAND CENTER',
    `Risk: ${top.risk_score}/100`,
    `Topic: ${top.topic}`,
    `Sentiment: ${String(top.sentiment).toUpperCase()}`,
    `Source: ${top.platform} / ${top.source}`,
    '',
    (top.title||top.content||'').slice(0,500),
    top.url?`\n${top.url}`:''
  ].join('\n');
  const res=await fetch(`https://api.telegram.org/bot${token}/sendMessage`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({chat_id:chatId,text,disable_web_page_preview:true})});
  return {sent:res.ok,status:res.status};
}
