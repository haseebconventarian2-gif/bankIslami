## Architecture

FastAPI service
-> Router (text vs audio)
-> Azure OpenAI
-> HTTP response

Text -> GPT -> Text
Audio -> STT -> GPT -> TTS -> Audio

### Azure endpoints used
- /openai/deployments/{deployment}/chat/completions
- /openai/deployments/{deployment}/audio/transcriptions
- /openai/deployments/{deployment}/audio/speech
