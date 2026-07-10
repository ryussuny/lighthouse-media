// 네이버 API 클라이언트 + 데모 데이터 생성기
//
// 실데이터 소스 (모두 무료 발급):
//  1) 네이버 검색광고 API (검색량·경쟁도·연관키워드) — https://manage.searchad.naver.com
//     .env: NAVER_AD_ACCESS_KEY / NAVER_AD_SECRET_KEY / NAVER_AD_CUSTOMER_ID
//  2) 네이버 데이터랩 API (월별 검색 추이) — https://developers.naver.com
//     .env: NAVER_CLIENT_ID / NAVER_CLIENT_SECRET
// 키가 없으면 각 소스별로 데모 데이터로 대체된다.

import crypto from "crypto";
import axios from "axios";

const AD_BASE = "https://api.searchad.naver.com";

export function hasAdApi() {
  return !!(process.env.NAVER_AD_ACCESS_KEY && process.env.NAVER_AD_SECRET_KEY && process.env.NAVER_AD_CUSTOMER_ID);
}
export function hasDataLab() {
  return !!(process.env.NAVER_CLIENT_ID && process.env.NAVER_CLIENT_SECRET);
}

// ── 검색광고 API: 키워드 검색량 + 연관키워드 ────────────────────────────
function adHeaders(method, uri) {
  const timestamp = String(Date.now());
  const sig = crypto
    .createHmac("sha256", process.env.NAVER_AD_SECRET_KEY)
    .update(`${timestamp}.${method}.${uri}`)
    .digest("base64");
  return {
    "X-Timestamp": timestamp,
    "X-API-KEY": process.env.NAVER_AD_ACCESS_KEY,
    "X-Customer": process.env.NAVER_AD_CUSTOMER_ID,
    "X-Signature": sig,
  };
}

// "< 10" 같은 문자열 값을 숫자로 정규화
function toCount(v) {
  if (typeof v === "number") return v;
  if (typeof v === "string" && v.includes("<")) return 5;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

export async function fetchKeywordStats(keyword) {
  const uri = "/keywordstool";
  const { data } = await axios.get(AD_BASE + uri, {
    headers: adHeaders("GET", uri),
    params: { hintKeywords: keyword.replace(/\s+/g, ""), showDetail: 1 },
    timeout: 10000,
  });
  const list = (data.keywordList || []).map((k) => ({
    keyword: k.relKeyword,
    pc: toCount(k.monthlyPcQcCnt),
    mobile: toCount(k.monthlyMobileQcCnt),
    total: toCount(k.monthlyPcQcCnt) + toCount(k.monthlyMobileQcCnt),
    compIdx: k.compIdx || "-",
    clickPc: Number(k.monthlyAvePcClkCnt) || 0,
    clickMobile: Number(k.monthlyAveMobileClkCnt) || 0,
    ctrPc: Number(k.monthlyAvePcCtr) || 0,
    ctrMobile: Number(k.monthlyAveMobileCtr) || 0,
    adDepth: Number(k.plAvgDepth) || 0,
  }));
  // 첫 항목이 조회 키워드 본인, 나머지가 연관키워드
  const self = list.find((k) => k.keyword.replace(/\s+/g, "") === keyword.replace(/\s+/g, "").toUpperCase())
    || list.find((k) => k.keyword.replace(/\s+/g, "").toLowerCase() === keyword.replace(/\s+/g, "").toLowerCase())
    || list[0];
  const related = list.filter((k) => k !== self).slice(0, 20);
  return { self, related };
}

// ── 데이터랩 API: 최근 12개월 검색 추이 ─────────────────────────────────
export async function fetchTrend(keyword) {
  const end = new Date();
  end.setDate(1);
  const start = new Date(end);
  start.setMonth(start.getMonth() - 12);
  const fmt = (d) => d.toISOString().slice(0, 10);

  const { data } = await axios.post(
    "https://openapi.naver.com/v1/datalab/search",
    {
      startDate: fmt(start),
      endDate: fmt(new Date(end.getFullYear(), end.getMonth(), 0)),
      timeUnit: "month",
      keywordGroups: [{ groupName: keyword, keywords: [keyword] }],
    },
    {
      headers: {
        "X-Naver-Client-Id": process.env.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": process.env.NAVER_CLIENT_SECRET,
        "Content-Type": "application/json",
      },
      timeout: 10000,
    }
  );
  return (data.results?.[0]?.data || []).map((d) => ({
    month: d.period.slice(0, 7),
    ratio: d.ratio,
  }));
}

// ── 데모 데이터 (결정적: 같은 키워드 → 항상 같은 숫자) ──────────────────
function seedFrom(str) {
  let h = 2166136261;
  for (const ch of String(str)) {
    h ^= ch.codePointAt(0);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
function mulberry32(seed) {
  let a = seed;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const SUFFIXES = ["추천", "가격", "후기", "순위", "비교", "방법", "종류", "브랜드", "세일", "인기", "차이", "사용법", "장단점", "구매", "할인"];
const COMP = ["낮음", "중간", "높음"];

export function demoStats(keyword) {
  const rnd = mulberry32(seedFrom(keyword));
  const scale = Math.floor(10 ** (2.5 + rnd() * 3)); // 300 ~ 300만 범위
  const mobileShare = 0.55 + rnd() * 0.3;
  const total = Math.round(scale * (0.8 + rnd() * 0.4));
  const mobile = Math.round(total * mobileShare);
  const self = {
    keyword,
    pc: total - mobile,
    mobile,
    total,
    compIdx: COMP[Math.floor(rnd() * 3)],
    clickPc: Math.round((total - mobile) * (0.005 + rnd() * 0.03) * 10) / 10,
    clickMobile: Math.round(mobile * (0.005 + rnd() * 0.03) * 10) / 10,
    ctrPc: Math.round(rnd() * 300) / 100,
    ctrMobile: Math.round(rnd() * 400) / 100,
    adDepth: Math.round(rnd() * 15),
  };
  const related = SUFFIXES.filter(() => rnd() > 0.35).slice(0, 12).map((sfx) => {
    const r = mulberry32(seedFrom(keyword + sfx));
    const t = Math.round(total * (0.05 + r() * 0.6));
    const m = Math.round(t * (0.5 + r() * 0.4));
    return {
      keyword: `${keyword} ${sfx}`,
      pc: t - m, mobile: m, total: t,
      compIdx: COMP[Math.floor(r() * 3)],
      clickPc: 0, clickMobile: 0, ctrPc: 0, ctrMobile: 0, adDepth: 0,
    };
  }).sort((a, b) => b.total - a.total);
  return { self, related };
}

export function demoTrend(keyword) {
  const rnd = mulberry32(seedFrom("trend:" + keyword));
  const base = 40 + rnd() * 30;
  const phase = rnd() * Math.PI * 2;
  const amp = 10 + rnd() * 25;
  const now = new Date();
  const points = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const seasonal = Math.sin((d.getMonth() / 12) * Math.PI * 2 + phase) * amp;
    const noise = (rnd() - 0.5) * 12;
    points.push({
      month: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`,
      ratio: Math.max(2, Math.min(100, Math.round(base + seasonal + noise))),
    });
  }
  // 최댓값을 100으로 정규화 (데이터랩과 같은 스케일)
  const max = Math.max(...points.map((p) => p.ratio));
  return points.map((p) => ({ ...p, ratio: Math.round((p.ratio / max) * 100) }));
}
