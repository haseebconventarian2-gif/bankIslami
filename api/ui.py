UI_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>BankIslami Assistant</title>
    <style>
      @import url("https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Space+Grotesk:wght@400;500;600&display=swap");
      :root {
        --bg: #0b1412;
        --panel: #0f1f1c;
        --chat: #0c1714;
        --incoming: #17342b;
        --outgoing: #0f4f3a;
        --text: #eef5f1;
        --muted: #9fb2aa;
        --accent: #d5b46b;
        --accent-2: #5ed3a1;
        --stroke: #1f3a31;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "Space Grotesk", "Segoe UI", sans-serif;
        background:
          radial-gradient(900px 500px at 10% -10%, rgba(213,180,107,0.25), transparent),
          radial-gradient(700px 400px at 100% 0%, rgba(94,211,161,0.18), transparent),
          linear-gradient(180deg, #07110f, #0b1412 40%, #0b1412);
        color: var(--text);
      }
      .app {
        max-width: 980px;
        margin: 24px auto;
        padding: 16px;
      }
      .shell {
        border-radius: 16px;
        overflow: hidden;
        background: var(--panel);
        box-shadow: 0 30px 80px rgba(0, 0, 0, 0.45);
        border: 1px solid var(--stroke);
      }
      .topbar {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 18px;
        background: linear-gradient(135deg, #0d2a22, #0f1f1c 60%);
      }
      .avatar {
        width: 36px;
        height: 36px;
        border-radius: 999px;
        background: radial-gradient(circle at 30% 30%, #ffe6a9, #d5b46b 60%, #8c6b2f);
        box-shadow: 0 0 0 2px rgba(213,180,107,0.35);
      }
      .title {
        font-size: 18px;
        font-weight: 600;
        font-family: "DM Serif Display", "Times New Roman", serif;
        letter-spacing: 0.5px;
      }
      .subtitle {
        color: var(--muted);
        font-size: 12px;
      }
      .chat {
        background:
          radial-gradient(500px 300px at 80% 0%, rgba(255,255,255,0.03), transparent),
          linear-gradient(180deg, rgba(15,31,28,0.4), rgba(12,23,20,0.7)),
          var(--chat);
        min-height: 420px;
        padding: 18px;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .bubble {
        max-width: 75%;
        padding: 10px 12px;
        border-radius: 12px;
        line-height: 1.35;
        font-size: 14px;
        word-wrap: break-word;
        border: 1px solid transparent;
      }
      .incoming { background: var(--incoming); align-self: flex-start; border-color: rgba(94,211,161,0.18); }
      .outgoing { background: var(--outgoing); align-self: flex-end; border-color: rgba(213,180,107,0.2); }
      .suggestions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 8px 18px 16px;
        border-top: 1px dashed rgba(255,255,255,0.06);
        background: #0f1f1c;
      }
      .chip {
        border: 1px solid var(--stroke);
        background: rgba(255,255,255,0.03);
        color: var(--text);
        border-radius: 999px;
        padding: 6px 10px;
        font-size: 12px;
        cursor: pointer;
      }
      .chip:hover { border-color: var(--accent-2); }
      .composer {
        display: grid;
        grid-template-columns: 1fr auto auto;
        gap: 8px;
        padding: 12px;
        border-top: 1px solid var(--stroke);
        background: #0f1f1c;
      }
      .input {
        width: 100%;
        padding: 10px 12px;
        border-radius: 10px;
        border: 1px solid var(--stroke);
        background: #0c1714;
        color: var(--text);
      }
      .btn {
        border: none;
        border-radius: 10px;
        padding: 10px 12px;
        cursor: pointer;
        font-weight: 600;
      }
      .btn.send { background: var(--accent); color: #1b1b14; }
      .btn.mic { background: #1b2e27; color: var(--text); border: 1px solid var(--stroke); }
      .panel {
        display: grid;
        grid-template-columns: 1fr auto auto;
        gap: 8px;
        padding: 12px;
        border-top: 1px solid var(--stroke);
        background: #0f1f1c;
      }
      .hint { color: var(--muted); font-size: 12px; }
      @media (max-width: 700px) {
        .composer, .panel { grid-template-columns: 1fr; }
        .bubble { max-width: 90%; }
      }
    </style>
  </head>
  <body>
    <div class="app">
      <div class="shell">
        <div class="topbar">
          <div class="avatar"></div>
          <div>
            <div class="title">BankIslami Assistant</div>
            <div class="subtitle">always on - answers in text or voice</div>
          </div>
        </div>
        <div class="chat" id="chat">
          <div class="bubble incoming">Welcome to BankIslami! How may I assist you?</div>
        </div>
        <div class="suggestions">
          <button class="chip" data-msg="Tell me about account options">Account options</button>
          <button class="chip" data-msg="How does Raast payment work?">Raast payments</button>
          <button class="chip" data-msg="What are the mobile app features?">Mobile app</button>
          <button class="chip" data-msg="Tell me about debit cards">Debit cards</button>
        </div>
        <div class="composer">
          <input id="textInput" class="input" placeholder="Type a message" />
          <button class="btn send" id="sendText">Send</button>
          <button class="btn mic" id="recordBtn">Record</button>
        </div>
        <div class="panel">
          <input id="audioFile" class="input" type="file" accept="audio/*" />
          <button class="btn mic" id="sendAudio">Send Audio</button>
          <div class="hint" id="recordHint">Mic ready</div>
        </div>
      </div>
    </div>
    <script>
      const textInput = document.getElementById("textInput");
      const audioFile = document.getElementById("audioFile");
      const chat = document.getElementById("chat");
      const recordBtn = document.getElementById("recordBtn");
      const recordHint = document.getElementById("recordHint");
      const chips = Array.from(document.querySelectorAll(".chip"));

      let mediaRecorder = null;
      let chunks = [];

      function addBubble(text, type) {
        const bubble = document.createElement("div");
        bubble.className = "bubble " + type;
        bubble.textContent = text;
        chat.appendChild(bubble);
        chat.scrollTop = chat.scrollHeight;
        return bubble;
      }

      function addAudioBubble(blob, type) {
        const bubble = document.createElement("div");
        bubble.className = "bubble " + type;
        const audio = document.createElement("audio");
        audio.controls = true;
        audio.src = URL.createObjectURL(blob);
        audio.style.width = "220px";
        bubble.appendChild(audio);
        chat.appendChild(bubble);
        chat.scrollTop = chat.scrollHeight;
      }

      async function sendText() {
        const text = (textInput.value || "").trim();
        if (!text) return;
        addBubble(text, "outgoing");
        textInput.value = "";
        const thinking = addBubble("...", "incoming");
        const res = await fetch("/text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text })
        });
        const data = await res.json().catch(() => ({}));
        thinking.textContent = data.text || ("Error: " + res.status);
      }

      async function sendAudio(file) {
        if (!file) return;
        addAudioBubble(file, "outgoing");
        const thinking = addBubble("Voice note received...", "incoming");
        const form = new FormData();
        form.append("file", file);
        const res = await fetch("/audio", { method: "POST", body: form });
        if (!res.ok) {
          thinking.textContent = "Error: " + res.status;
          return;
        }
        const blob = await res.blob();
        thinking.remove();
        addAudioBubble(blob, "incoming");
      }

      document.getElementById("sendText").addEventListener("click", sendText);
      textInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendText();
      });

      chips.forEach((chip) => {
        chip.addEventListener("click", async () => {
          const text = chip.getAttribute("data-msg") || chip.textContent;
          textInput.value = text || "";
          await sendText();
        });
      });

      document.getElementById("sendAudio").addEventListener("click", async () => {
        if (!audioFile.files.length) return;
        await sendAudio(audioFile.files[0]);
        audioFile.value = "";
      });

      async function startRecording() {
        if (!navigator.mediaDevices?.getUserMedia) {
          recordHint.textContent = "Mic not supported in this browser.";
          return;
        }
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          mediaRecorder = new MediaRecorder(stream);
          chunks = [];
          mediaRecorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
          mediaRecorder.onstop = async () => {
            const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
            stream.getTracks().forEach((t) => t.stop());
            recordHint.textContent = "Sending voice note...";
            await sendAudio(blob);
            recordHint.textContent = "Mic ready";
            recordBtn.textContent = "Record";
          };
          mediaRecorder.start();
          recordHint.textContent = "Recording...";
          recordBtn.textContent = "Stop";
        } catch (err) {
          recordHint.textContent = "Mic access denied.";
        }
      }

      recordBtn.addEventListener("click", async () => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
          mediaRecorder.stop();
          return;
        }
        await startRecording();
      });

    </script>
  </body>
</html>
"""
