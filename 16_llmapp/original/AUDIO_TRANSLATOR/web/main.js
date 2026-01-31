const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");
const btnSave = document.getElementById("btnSave");
const btnClear = document.getElementById("btnClear");
const btnSpeak = document.getElementById("btnSpeak");
const btnSpeakStop = document.getElementById("btnSpeakStop");
const autoSpeakChk = document.getElementById("autoSpeak");
const directionSel = document.getElementById("direction");

const live = document.getElementById("live");
const transcriptBox = document.getElementById("transcript");
const translatedBox = document.getElementById("translated");
const termsDiv = document.getElementById("terms");

let recognition = null;
let fullTranscript = "";
let fullTranslated = "";
let isRunning = false;

/* ========= 用語説明：累積管理 ========= */
let termStore = new Map(); // key: translation|note

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderTerms(terms) {
  if (!terms || terms.length === 0) {
    termsDiv.innerHTML = `<div class="small">（重要語は検出されませんでした）</div>`;
    return;
  }

  const html = terms.map(t => {
    const term = escapeHtml(t.term || "");
    const tr = escapeHtml(t.translation || "");
    const note = escapeHtml(t.note || "");
    return `
      <div class="term-item">
        <b>${tr}</b> <span class="term-raw">(${term})</span><br>
        <span class="term-note">${note}</span>
      </div>
    `;
  }).join("");

  termsDiv.innerHTML = html;
}

function appendTerms(terms) {
  if (!terms || terms.length === 0) {
    if (termStore.size === 0) renderTerms([]);
    return;
  }
  for (const t of terms) {
    const key = (t.translation || "") + "|" + (t.note || "");
    termStore.set(key, t);
  }
  renderTerms(Array.from(termStore.values()));
}

/* ========= 読み上げ（Text → Speech） ========= */
function speakText(text) {
  if (!text) return;

  const u = new SpeechSynthesisUtterance(text);
  u.lang = (directionSel.value === "EN2JA") ? "ja-JP" : "en-US";
  u.rate = 1.0;
  u.pitch = 1.0;

  speechSynthesis.cancel(); // 途中再生を止める
  speechSynthesis.speak(u);

  btnSpeakStop.disabled = false;
}

btnSpeak.onclick = () => {
  speakText(translatedBox.value.trim());
};

btnSpeakStop.onclick = () => {
  speechSynthesis.cancel();
  btnSpeakStop.disabled = true;
};

/* ========= 翻訳API ========= */
async function translateFinalText(finalText) {
  const direction = directionSel.value;
  const res = await fetch("/api/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: finalText, direction })
  });
  return await res.json(); // { translated, terms }
}

/* ========= 音声認識 ========= */
function setupRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("このブラウザは音声認識に対応していません。Chrome / Edge を使ってください。");
    return null;
  }

  const r = new SpeechRecognition();

  // 翻訳方向に応じて認識言語を切り替え
  r.lang = (directionSel.value === "EN2JA") ? "en-US" : "ja-JP";

  r.interimResults = true;
  r.continuous = true;

  r.onresult = async (event) => {
    let interim = "";
    let finalText = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const txt = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalText += txt;
      else interim += txt;
    }

    live.textContent = interim ? interim : "…";

    if (finalText) {
      fullTranscript += finalText + "\n";
      transcriptBox.value = fullTranscript;
      btnSave.disabled = false;

      try {
        const data = await translateFinalText(finalText);
        const translated = data.translated || "";
        const terms = data.terms || [];

        fullTranslated += translated + "\n";
        translatedBox.value = fullTranslated;

        appendTerms(terms);

        btnSpeak.disabled = false;

        // ★ 自動読み上げ
        if (autoSpeakChk.checked) {
          speakText(translated);
        }

      } catch (e) {
        console.error(e);
      }
    }
  };

  r.onend = () => {
    if (isRunning) {
      try { r.start(); } catch (e) {}
    }
  };

  r.onerror = (e) => {
    console.error("speech error:", e);
  };

  return r;
}

/* ========= ボタン操作 ========= */
btnStart.onclick = () => {
  if (isRunning) return;

  recognition = setupRecognition();
  if (!recognition) return;

  isRunning = true;
  btnStart.disabled = true;
  btnStop.disabled = false;

  live.textContent = "Listening…";
  if (termStore.size === 0) renderTerms([]);

  try { recognition.start(); } catch (e) {}
};

btnStop.onclick = () => {
  isRunning = false;
  btnStart.disabled = false;
  btnStop.disabled = true;
  live.textContent = "停止しました";
  try { recognition.stop(); } catch (e) {}
};

// 保存（必要なときだけ）
btnSave.onclick = () => {
  const content =
`[TRANSCRIPT]
${fullTranscript}

[TRANSLATION]
${fullTranslated}
`;

  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const now = new Date();
  const ts = now.toISOString().slice(0,19).replace(/[:T]/g, "");
  a.href = url;
  a.download = `realtime_translation_${ts}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

// クリア
btnClear.onclick = () => {
  fullTranscript = "";
  fullTranslated = "";
  transcriptBox.value = "";
  translatedBox.value = "";
  live.textContent = "";
  btnSave.disabled = true;
  btnSpeak.disabled = true;

  termStore.clear();
  renderTerms([]);
};
