import axios from 'axios';
import FormData from 'form-data';

/**
 * Azure OpenAI REST helpers
 *
 * Endpoints:
 * - Chat Completions: /openai/deployments/{deployment}/chat/completions?api-version=...
 * - Transcriptions:   /openai/deployments/{deployment}/audio/transcriptions?api-version=...
 * - Text-to-Speech:   /openai/deployments/{deployment}/audio/speech?api-version=...
 *
 * References:
 * - Whisper transcription endpoint pattern shown in Microsoft Learn quickstart. 
 * - TTS /audio/speech endpoint and request body shown in Microsoft Learn quickstart.
 */

function requireEnv(name) {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
}

function baseUrl() {
  // Ensure no trailing slash issues
  const endpoint = requireEnv('AZURE_OPENAI_ENDPOINT').replace(/\/+$/, '');
  return endpoint;
}

function apiHeaders(extra = {}) {
  return {
    'api-key': requireEnv('AZURE_OPENAI_API_KEY'),
    ...extra
  };
}

function apiVersion() {
  return process.env.AZURE_OPENAI_API_VERSION || '2025-04-01-preview';
}

export async function generateText(userPrompt) {
  const deployment = requireEnv('AZURE_GPT_DEPLOYMENT');

  const url = `${baseUrl()}/openai/deployments/${encodeURIComponent(deployment)}/chat/completions?api-version=${encodeURIComponent(apiVersion())}`;

  const body = {
    messages: [
      { role: 'system', content: 'You are a helpful WhatsApp assistant. Keep replies concise.' },
      { role: 'user', content: String(userPrompt ?? '') }
    ],
    temperature: 0.3
  };

  const r = await axios.post(url, body, {
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    timeout: 120000
  });

  const text = r.data?.choices?.[0]?.message?.content;
  return (text || '').trim() || 'Sorry, I could not generate a response.';
}

export async function transcribeAudio(audioBuffer) {
  const deployment = requireEnv('AZURE_STT_DEPLOYMENT');

  const url = `${baseUrl()}/openai/deployments/${encodeURIComponent(deployment)}/audio/transcriptions?api-version=${encodeURIComponent(apiVersion())}`;

  const form = new FormData();
  // WhatsApp audio is often OGG/Opus; Azure accepts common audio containers.
  form.append('file', audioBuffer, { filename: 'in.ogg', contentType: 'audio/ogg' });

  const r = await axios.post(url, form, {
    headers: { ...apiHeaders(), ...form.getHeaders() },
    maxBodyLength: Infinity,
    timeout: 300000
  });

  const text = r.data?.text;
  return (text || '').trim() || '';
}

export async function synthesizeSpeech(text) {
  const deployment = requireEnv('AZURE_TTS_DEPLOYMENT');

  const url = `${baseUrl()}/openai/deployments/${encodeURIComponent(deployment)}/audio/speech?api-version=${encodeURIComponent(apiVersion())}`;

  const voice = process.env.AZURE_TTS_VOICE || 'alloy';
  const format = process.env.AZURE_TTS_FORMAT || 'mp3';

  // Per Microsoft Learn, request body includes model, input, voice (and can include format).
  const body = {
    model: deployment, // Azure SDK examples pass deploymentName as model.
    input: String(text ?? ''),
    voice,
    format
  };

  const r = await axios.post(url, body, {
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    responseType: 'arraybuffer',
    timeout: 300000
  });

  return Buffer.from(r.data);
}
