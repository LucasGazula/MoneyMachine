export type Data = Record<string, any>;
export type Translate = (key: string) => string;

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
