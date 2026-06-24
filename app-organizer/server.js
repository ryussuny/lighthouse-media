import express from "express";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import Anthropic from "@anthropic-ai/sdk";
import { config } from "dotenv";

config();

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(express.json({ limit: "1mb" }));
app.use(express.static(join(__dirname, "public")));

const PORT = process.env.APP_ORGANIZER_PORT || 3300;
const MODEL = process.env.ORGANIZER_MODEL || "claude-sonnet-4-6";

const client = process.env.ANTHROPIC_API_KEY ? new Anthropic() : null;

const SYSTEM_PROMPT = `당신은 스마트폰 홈 화면 정리 전문가입니다.
사용자가 설치한 앱 이름 목록을 받으면, 사용 목적에 따라 폴더로 분류합니다.

규칙:
- 폴더는 5~9개 사이로 만드세요. 너무 잘게 쪼개지 마세요.
- 각 폴더에는 한국어로 짧고 직관적인 이름과 어울리는 이모지 1개를 붙이세요.
- 모든 앱은 정확히 하나의 폴더에만 들어가야 합니다. 입력된 앱을 빠뜨리지 마세요.
- 어디에도 맞지 않는 앱은 "기타" 폴더로 묶으세요.
- 흔한 카테고리 예시: SNS/소통, 금융/결제, 업무/생산성, 미디어/엔터, 쇼핑, 사진/카메라,
  게임, 교통/지도, 건강/운동, 음식/배달, 교육/학습, 여행, 유틸리티, 시스템/설정.
  단, 입력된 앱 구성에 맞게 자유롭게 조정하세요.

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명, 마크다운 코드블록 없이 순수 JSON만 출력하세요.
{
  "folders": [
    { "name": "폴더 이름", "emoji": "📱", "apps": ["앱1", "앱2"] }
  ]
}`;

// 입력 정리: 줄바꿈/쉼표/탭으로 구분된 텍스트를 앱 이름 배열로
function parseApps(raw) {
  if (Array.isArray(raw)) return raw.map((s) => String(s).trim()).filter(Boolean);
  return String(raw || "")
    .split(/[\n,\t]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

// 응답 JSON에서 누락/추가된 앱을 보정
function reconcile(folders, inputApps) {
  const seen = new Set();
  const cleaned = (folders || [])
    .map((f) => ({
      name: String(f.name || "기타").trim(),
      emoji: String(f.emoji || "📁").trim() || "📁",
      apps: (f.apps || [])
        .map((a) => String(a).trim())
        .filter((a) => {
          // 입력에 없던 앱은 버리고, 중복은 첫 등장만 유지
          const ok = inputApps.includes(a) && !seen.has(a);
          if (ok) seen.add(a);
          return ok;
        }),
    }))
    .filter((f) => f.apps.length > 0);

  // 분류에서 누락된 앱은 "기타"로 모음
  const missing = inputApps.filter((a) => !seen.has(a));
  if (missing.length) {
    const etc = cleaned.find((f) => f.name === "기타");
    if (etc) etc.apps.push(...missing);
    else cleaned.push({ name: "기타", emoji: "📦", apps: missing });
  }
  return cleaned;
}

app.post("/api/organize", async (req, res) => {
  const apps = parseApps(req.body.apps);
  if (apps.length === 0) {
    return res.status(400).json({ error: "앱 이름을 하나 이상 입력하세요." });
  }
  if (!client) {
    return res.status(503).json({
      error: "ANTHROPIC_API_KEY가 설정되지 않았습니다. .env에 키를 추가한 뒤 다시 시도하세요.",
    });
  }

  try {
    const message = await client.messages.create({
      model: MODEL,
      max_tokens: 2048,
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: "user",
          content: `다음 앱들을 폴더로 정리해줘 (총 ${apps.length}개):\n${apps.join("\n")}`,
        },
      ],
    });

    const text = message.content.find((b) => b.type === "text")?.text || "";
    // 혹시 모를 코드블록/잡텍스트 제거 후 JSON 파싱
    const jsonStr = text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1);
    let parsed;
    try {
      parsed = JSON.parse(jsonStr);
    } catch {
      return res.status(502).json({ error: "AI 응답을 해석하지 못했습니다. 다시 시도해주세요.", raw: text });
    }

    const folders = reconcile(parsed.folders, apps);
    res.json({ folders, total: apps.length, model: MODEL });
  } catch (err) {
    console.error("organize error:", err.message);
    res.status(500).json({ error: `AI 분류 중 오류: ${err.message}` });
  }
});

app.get("/api/health", (req, res) => {
  res.json({ ok: true, hasApiKey: !!client, model: MODEL });
});

app.listen(PORT, () => {
  console.log(`📱 앱 정리 도우미 실행 중 → http://localhost:${PORT}`);
  if (!client) console.log("⚠️  ANTHROPIC_API_KEY 없음 — .env에 키를 추가하세요.");
});
