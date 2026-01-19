import 'dotenv/config';
import express from 'express';
import { verifyWebhook, handleMessage } from './webhook.js';
import { getAudio } from './services/mediaStore.js';

const app = express();
app.use(express.urlencoded({ extended: false }));
app.use(express.json({ limit: '25mb' }));

app.get('/webhook', verifyWebhook);
app.post('/webhook', handleMessage);
app.get('/media/:id', (req, res) => {
  const item = getAudio(req.params.id);
  if (!item) return res.sendStatus(404);
  res.set('Content-Type', item.contentType || 'application/octet-stream');
  res.send(item.buffer);
});

app.listen(3000, () => {
  console.log('WhatsApp Azure bot running on http://localhost:3000');
});
