// filename: index.js
// author: gbox3d
// created: 2025-05-20
// 이 주석은 수정하지 마세요.

const theAppContext = {
  dom: {},
  settings: {
    apiBaseUrl: localStorage.getItem("BASE_TTSAPI_URL") || "",
  },
};

export default function main() {
  // ──────────── DOM 캐싱 ────────────
  theAppContext.dom.input      = document.getElementById("input-speech");
  theAppContext.dom.btnSpeech  = document.getElementById("btn-speech");
  theAppContext.dom.apiBaseUrl = document.getElementById("apiBaseUrl");
  theAppContext.dom.authToken  = document.getElementById("authToken");
  theAppContext.dom.btnSave    = document.getElementById("save");
  theAppContext.dom.player     = document.getElementById("player");
  theAppContext.dom.status     = document.getElementById("status");

  // 값 복원
  theAppContext.dom.apiBaseUrl.value = theAppContext.settings.apiBaseUrl;

  theAppContext.dom.input.value = "간장 공장 공장장은 강 공장장이고 된장 공장 공장장은 장 공장장이다. 강된장 공장 공장장은 공 공장장이다."


  // ──────────── 이벤트 바인딩 ────────────
  theAppContext.dom.btnSpeech.addEventListener("click", onSpeech);
  theAppContext.dom.btnSave?.addEventListener("click", onSave);
}

/* -------------------------------
   요청 → MP3 Blob → 재생
-------------------------------- */
async function onSpeech() {
  const text = theAppContext.dom.input.value.trim();
  if (!text) {
    theAppContext.dom.status.textContent = "⚠️  텍스트를 입력하세요.";
    return;
  }

  theAppContext.dom.status.textContent = "⏳ 합성 중…";

  try {
    // 1) POST /tts
    const res = await fetch(`${theAppContext.settings.apiBaseUrl}/tts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(theAppContext.settings.token && { Authorization: `Bearer ${theAppContext.settings.token}` }),
      },
      body: JSON.stringify({ text, format: "mp3", speed: 1.0 }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    // 2) 바이너리 → Blob
    const buf  = await res.arrayBuffer();                       // ⬅ arrayBuffer 사용 :contentReference[oaicite:3]{index=3}
    const blob = new Blob([buf], { type: res.headers.get("Content-Type") || "audio/mpeg" });

    // 3) Blob URL 생성 및 재생
    const url = URL.createObjectURL(blob);                      // ⬅ createObjectURL 패턴 :contentReference[oaicite:4]{index=4}
    theAppContext.dom.player.src = url;
    theAppContext.dom.player.play();
    theAppContext.dom.status.textContent = "✅ 재생 중… (완료 후 자동 해제)";

    // 4) 다운로드 링크 제공 (선택)
    makeDownload(url);
  } catch (err) {
    console.error(err);
    theAppContext.dom.status.textContent = `❌ 오류: ${err.message}`;
  }
}

/* -------------------------------
   옵션 저장
-------------------------------- */
function onSave() {
  theAppContext.settings.apiBaseUrl = theAppContext.dom.apiBaseUrl.value.trim() || location.origin;
  theAppContext.settings.token      = theAppContext.dom.authToken.value.trim();

  localStorage.setItem("apiBaseUrl", theAppContext.settings.apiBaseUrl);
  localStorage.setItem("authToken", theAppContext.settings.token);
  theAppContext.dom.status.textContent = "💾 설정이 저장되었습니다.";
}

/* -------------------------------
   생성된 음성 파일 다운로드 링크
-------------------------------- */
function makeDownload(url) {
  let link = document.getElementById("downloadLink");
  if (!link) {
    link = document.createElement("a");
    link.id   = "downloadLink";
    link.textContent = "⬇️ 다운로드";
    link.className   = "w3-margin-left";
    theAppContext.dom.player.insertAdjacentElement("afterend", link);
  }
  link.href = url;
  link.download = "speech.mp3";
}
