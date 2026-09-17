const POSITIVE = [
  'bagus','baik','mantap','membantu','mudah','cepat','puas','bermanfaat','terjangkau','layak','sukses','berhasil','apresiasi','senang','lancar','solutif','positif','nyaman','recommended','rekomendasi','terima kasih','terbantu'
];
const NEGATIVE = [
  'buruk','jelek','rusak','bocor','retak','lambat','sulit','gagal','kecewa','mahal','masalah','bermasalah','keluhan','komplain','parah','tidak layak','nggak layak','ga layak','penipuan','tipu','mangkrak','banjir','macet','ribet','ditolak','tolak','korup','pungli','marah','protes','viral','bobrok','ambruk','cacat'
];
const NEGATORS = ['tidak','tak','nggak','ga','gak','bukan','belum','kurang'];
const SARCASM = ['mantap banget','bagus banget','hebat banget','luar biasa','terima kasih banget'];

const TOPICS = [
  ['Kualitas Rumah', ['bocor','retak','rusak','kualitas','bangunan','atap','dinding','struktur','ambruk','cacat']],
  ['Proses Pengajuan', ['pengajuan','proses','verifikasi','antrian','akad','approval','persetujuan','lama','lambat']],
  ['FLPP / Subsidi', ['flpp','subsidi','kpr subsidi','rumah subsidi','mbr','bantuan pembiayaan']],
  ['Bank & Pembiayaan', ['bank','btn','bri','bni','mandiri','bsi','cicilan','angsuran','bunga','kpr','kredit']],
  ['Pengembang', ['pengembang','developer','perumahan','proyek','serah terima']],
  ['Harga & Keterjangkauan', ['harga','mahal','murah','terjangkau','uang muka','dp','angsuran']],
  ['Keterhunian', ['huni','hunian','ditempati','kosong','listrik','air','penghuni']],
  ['Layanan & Informasi', ['layanan','call center','aplikasi','website','informasi','customer service','cs']],
  ['Kebijakan Perumahan', ['kebijakan','aturan','peraturan','program 3 juta rumah','tiga juta rumah','pemerintah']]
];

function countOccurrences(text, needle) {
  if (!needle) return 0;
  let count = 0;
  let pos = 0;
  while ((pos = text.indexOf(needle, pos)) !== -1) {
    count += 1;
    pos += needle.length;
  }
  return count;
}

function contextualScore(text, word, weight) {
  let score = 0;
  let index = text.indexOf(word);
  while (index !== -1) {
    const before = text.slice(Math.max(0, index - 24), index);
    const negated = NEGATORS.some(n => new RegExp(`\\b${n}\\s+$`).test(before));
    score += negated ? -weight : weight;
    index = text.indexOf(word, index + word.length);
  }
  return score;
}

function detectTopic(text) {
  let best = ['Umum', 0];
  for (const [topic, words] of TOPICS) {
    const score = words.reduce((n, word) => n + countOccurrences(text, word), 0);
    if (score > best[1]) best = [topic, score];
  }
  return best[0];
}

function detectEmotion(text, sentiment) {
  if (/marah|kesal|parah|bobrok|pungli|tipu/.test(text)) return 'anger';
  if (/kecewa|sedih|gagal|ditolak|sulit/.test(text)) return 'frustration';
  if (/khawatir|takut|cemas|risiko|ancam/.test(text)) return 'concern';
  if (/senang|puas|mantap|terbantu|apresiasi/.test(text)) return 'satisfaction';
  return sentiment === 'negative' ? 'concern' : sentiment === 'positive' ? 'satisfaction' : 'neutral';
}

function keywords(text) {
  const stop = new Set(['yang','dan','atau','untuk','dengan','dari','pada','ini','itu','ada','jadi','karena','sudah','belum','tidak','rumah','tapera','bp','flpp','kpr']);
  const tokens = text.toLowerCase().replace(/[^a-z0-9\u00C0-\u024F\s-]/g,' ').split(/\s+/).filter(w => w.length > 3 && !stop.has(w));
  const counts = new Map();
  for (const token of tokens) counts.set(token, (counts.get(token) || 0) + 1);
  return [...counts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,6).map(([w])=>w);
}

export function analyzeText(input, engagement = 0, reachEstimate = 0) {
  const text = String(input || '').toLowerCase().replace(/\s+/g,' ').trim();
  let raw = 0;
  for (const word of POSITIVE) raw += contextualScore(text, word, 1);
  for (const word of NEGATIVE) raw += contextualScore(text, word, -1.25);

  const sarcasm = SARCASM.some(p => text.includes(p)) && NEGATIVE.some(n => text.includes(n));
  if (sarcasm) raw -= 2.5;

  const score = Math.max(-1, Math.min(1, raw / 4));
  const sentiment = score > 0.18 ? 'positive' : score < -0.18 ? 'negative' : 'neutral';
  const topic = detectTopic(text);
  const emotion = detectEmotion(text, sentiment);
  const virality = Math.min(100, Math.log10(Math.max(1, engagement) + 1) * 22 + Math.log10(Math.max(1, reachEstimate) + 1) * 8);
  const severity = /pungli|penipuan|tipu|ambruk|banjir|mangkrak|viral|korup|rusak|bocor|retak/.test(text) ? 22 : 0;
  const negativity = sentiment === 'negative' ? 42 * Math.abs(score) : 0;
  const risk = Math.max(0, Math.min(100, 12 + negativity + severity + virality * 0.28));

  return {
    sentiment,
    sentiment_score: Number(score.toFixed(3)),
    emotion,
    topic,
    narrative: topic === 'Umum' ? 'Percakapan umum terkait program/perumahan' : `Percakapan terkait ${topic.toLowerCase()}`,
    keywords: keywords(text),
    virality_score: Number(virality.toFixed(1)),
    risk_score: Number(risk.toFixed(1)),
    sarcasm
  };
}
