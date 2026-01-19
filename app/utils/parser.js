export function parseMessage(payload) {
  try {
    const message = payload?.entry?.[0]?.changes?.[0]?.value?.messages?.[0];
    if (!message) return null;

    const from = message.from;
    if (!from) return null;

    if (message.type === 'audio' && message.audio?.id) {
      return {
        from,
        type: 'audio',
        mediaId: message.audio.id,
        mediaType: message.audio.mime_type
      };
    }

    if (message.type === 'text' && message.text?.body?.trim()) {
      return { from, type: 'text', text: message.text.body };
    }

    return null;
  } catch {
    return null;
  }
}
