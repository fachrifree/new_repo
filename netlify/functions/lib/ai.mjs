import OpenAI from 'openai';

function cleanJson(text='') {
  const first=text.indexOf('{'), last=text.lastIndexOf('}');
  if(first<0||last<first) throw new Error('AI response was not JSON');
  return JSON.parse(text.slice(first,last+1));
}

export async function aiBrief(payload) {
  try {
    const client=new OpenAI();
    const compact={kpis:payload.kpis,issues:payload.issues?.slice(0,6),sources:payload.sources?.slice(0,6),alerts:payload.alerts?.slice(0,5).map(x=>({title:x.title,platform:x.platform,topic:x.topic,risk_score:x.risk_score,sentiment:x.sentiment}))};
    const response=await client.chat.completions.create({
      model:'gpt-4o-mini', temperature:0.15, max_tokens:600,
      messages:[
        {role:'system',content:'Anda adalah analis media intelligence netral. Ringkas hanya berdasarkan data yang diberikan. Jangan mengarang fakta, motif, afiliasi politik, atau dampak yang tidak ada di data. Bedakan sinyal data dan interpretasi. Jawab JSON object dengan keys headline, summary, developments (array maks 4), risks (array maks 3), watch_next (array maks 3). Bahasa Indonesia profesional.'},
        {role:'user',content:JSON.stringify(compact)}
      ]
    });
    return {ok:true,model:'gpt-4o-mini',...cleanJson(response.choices?.[0]?.message?.content||'')};
  } catch(error) {
    return {ok:false,error:String(error?.message||error),headline:'AI brief belum aktif',summary:'Dashboard tetap menggunakan ringkasan statistik berbasis data. Aktifkan Netlify AI Gateway untuk ringkasan kontekstual.',developments:payload.executive_brief||[],risks:(payload.issues||[]).slice(0,3).map(x=>`${x.topic}: avg risk ${x.avg_risk}`),watch_next:['Pantau perubahan volume 24 jam','Pantau isu dengan negative share tertinggi','Pantau mention berisiko tinggi']};
  }
}
