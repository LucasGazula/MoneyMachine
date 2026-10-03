export type Data = Record<string, any>;
export type Translate = (key: string) => string;

export const mediaLabels: Record<string, string> = {
  pexels: 'Pexels — stock videos', pixabay: 'Pixabay — stock videos', coverr: 'Coverr — stock videos',
  local: 'Local files — no API', openai_image: 'AI images — OpenAI-compatible API',
  wavespeed: 'WaveSpeed — AI video', volcengine_seedance: 'Seedance — AI video',
  ofox: 'OFox — AI video', metaso_minimax: 'Metaso / MiniMax — AI video',
  muapi: 'MuAPI — AI video', loomloom: 'LoomLoom — AI video',
};
export const speechLabels: Record<string, string> = {
  'azure-tts-v1': 'Microsoft Edge TTS — no API key', 'azure-tts-v2': 'Microsoft Azure Speech — API key',
  'gemini-tts': 'Google Gemini — text to speech',
};
export const geminiTtsModels = [
  {value:'gemini-2.5-flash-preview-tts',label:'Gemini 2.5 Flash TTS'},
  {value:'gemini-2.5-pro-preview-tts',label:'Gemini 2.5 Pro TTS'},
  {value:'gemini-3.8-flash-tts',label:'Gemini 3.8 Flash TTS'},
  {value:'gemini-3.8-flash-lite-tts',label:'Gemini 3.8 Flash-Lite TTS'},
];
export const musicLabels: Record<string, string> = {
  '': 'No music', random: 'Random local music — no API', preset: 'Built-in music — no API',
  custom: 'Uploaded music — no API', sonilo: 'Sonilo — AI music', elevenlabs: 'ElevenLabs — AI music',
  lyria: 'Google Lyria 3.5 — AI music',
};

export async function api(path: string, body?: unknown, method?: string): Promise<any> {
  const target = path.startsWith('/api/') ? path : `/api/v1/studio${path}`;
  const response = await fetch(target, {
    method: method ?? (body === undefined ? 'GET' : 'POST'),
    credentials: 'same-origin',
    headers: body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail ?? data.message ?? `HTTP ${response.status}`;
    const error = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    Object.assign(error, { status: response.status });
    throw error;
  }
  return data;
}

export function download(name: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function upload(kind: string, file: File): Promise<Data> {
  const form = new FormData(); form.set('file', file);
  return api(`/uploads/${kind}`, form);
}

export function durationEstimate(text: string, rate: number): [number, number] | null {
  const normalized = text.trim().replace(/\s+/g, ' ');
  if (!normalized) return null;
  const cjk = /[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]/gu;
  const chars = normalized.match(cjk)?.length ?? 0;
  const words = normalized.replace(cjk, ' ').match(/[\p{L}\p{N}_]+(?:[-'’][\p{L}\p{N}_]+)*/gu)?.length ?? 0;
  const punctuation = normalized.match(/[,，.。!?！？;；:：]/g)?.length ?? 0;
  const seconds = (chars / 4.2 + words / 2.6 + punctuation * .12) / Math.max(rate || 1, .1);
  return [Math.max(1, Math.round(seconds * .85)), Math.max(1, Math.round(seconds * 1.15))];
}
