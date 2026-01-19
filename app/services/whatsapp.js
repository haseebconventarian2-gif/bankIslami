import axios from 'axios';
import { saveAudio } from './mediaStore.js';

function requireEnv(name) {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
}

function graphBase() {
  const version = process.env.META_API_VERSION || process.env.VERSION || 'v20.0';
  return `https://graph.facebook.com/${version}`;
}

function baseUrl() {
  return requireEnv('PUBLIC_BASE_URL').replace(/\/+$/, '');
}

function authHeader() {
  return {
    Authorization: `Bearer ${requireEnv('ACCESS_TOKEN')}`
  };
}

function audioContentType() {
  const format = (process.env.AZURE_TTS_FORMAT || 'mp3').toLowerCase();
  const isMp3 = format === 'mp3' || format === 'mpeg' || format === 'audio/mpeg';
  return isMp3 ? 'audio/mpeg' : 'audio/ogg';
}

function messageUrl() {
  const phoneNumberId = requireEnv('PHONE_NUMBER_ID');
  return `${graphBase()}/${phoneNumberId}/messages`;
}

export async function downloadMedia(mediaId) {
  const meta = await axios.get(`${graphBase()}/${mediaId}`, {
    headers: authHeader()
  });

  const file = await axios.get(meta.data.url, {
    responseType: 'arraybuffer',
    headers: authHeader()
  });

  return Buffer.from(file.data);
}

export async function replyText(to, text) {
  await axios.post(
    messageUrl(),
    {
      messaging_product: 'whatsapp',
      to,
      type: 'text',
      text: { body: text }
    },
    { headers: authHeader() }
  );
}

export async function replyAudio(to, audioBuffer) {
  const contentType = audioContentType();
  const mediaId = saveAudio(audioBuffer, contentType);
  const mediaUrl = `${baseUrl()}/media/${mediaId}`;

  await axios.post(
    messageUrl(),
    {
      messaging_product: 'whatsapp',
      to,
      type: 'audio',
      audio: { link: mediaUrl }
    },
    { headers: authHeader() }
  );
}
