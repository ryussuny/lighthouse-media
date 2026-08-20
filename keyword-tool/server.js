import express from "express";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { config } from "dotenv";
import {
  hasAdApi, hasDataLab,
  fetchKeywordStats, fetchTrend,
  demoStats, demoTrend,
} from "./naver.js";

config();

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(express.json());
app.use(express.static(join(__dirname, "public")));

const PORT = process.env.KEYWORD_TOOL_PORT || 3400;

app.get("/api/keyword", async (req, res) => {
  const keyword = String(req.query.q || "").trim();
  if (!keyword) return res.status(400).json({ error: "키워드를 입력하세요." });
  if (keyword.length > 30) return res.status(400).json({ error: "키워드는 30자 이내로 입력하세요." });

  // 검색량·연관키워드 (검색광고 API → 실패/무키 시 데모)
  let stats, statsEngine = "demo";
  if (hasAdApi()) {
    try {
      stats = await fetchKeywordStats(keyword);
      statsEngine = "naver";
    } catch (err) {
      console.error("검색광고 API 실패, 데모로 폴백:", err.response?.status || err.message);
    }
  }
  if (!stats || !stats.self) stats = demoStats(keyword);

  // 월별 추이 (데이터랩 API → 실패/무키 시 데모)
  let trend, trendEngine = "demo";
  if (hasDataLab()) {
    try {
      trend = await fetchTrend(keyword);
      trendEngine = "datalab";
    } catch (err) {
      console.error("데이터랩 API 실패, 데모로 폴백:", err.response?.status || err.message);
    }
  }
  if (!trend || trend.length === 0) trend = demoTrend(keyword);

  res.json({
    keyword,
    engines: { stats: statsEngine, trend: trendEngine },
    self: stats.self,
    related: stats.related,
    trend,
  });
});

app.get("/api/health", (req, res) => {
  res.json({ ok: true, adApi: hasAdApi(), dataLab: hasDataLab() });
});

app.listen(PORT, () => {
  console.log(`🔍 키워드 조회 도구 실행 중 → http://localhost:${PORT}`);
  if (!hasAdApi()) console.log("ℹ️  네이버 검색광고 API 키 없음 → 검색량은 데모 데이터");
  if (!hasDataLab()) console.log("ℹ️  네이버 데이터랩 API 키 없음 → 추이는 데모 데이터");
});
