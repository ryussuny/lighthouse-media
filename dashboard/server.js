import express from "express";
import { createServer } from "http";
import { Server } from "socket.io";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import nodemailer from "nodemailer";
import "dotenv/config";

// === 주문/리드 이메일 알림 ===
const mailer = process.env.GMAIL_APP_PASS
  ? nodemailer.createTransport({
      service: "gmail",
      auth: { user: process.env.GMAIL_USER, pass: process.env.GMAIL_APP_PASS },
    })
  : null;

async function notify(subject, text) {
  if (!mailer) { console.log("⚠️ 메일 알림 미설정 (GMAIL_APP_PASS 없음)"); return; }
  try {
    await mailer.sendMail({
      from: `"Lighthouse 알림" <${process.env.GMAIL_USER}>`,
      to: process.env.NOTIFY_TO || process.env.GMAIL_USER,
      subject,
      text,
    });
    console.log(`📨 알림 발송: ${subject}`);
  } catch (e) {
    console.error("메일 알림 실패:", e.message);
  }
}

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const server = createServer(app);
const io = new Server(server);

app.use(express.json());

// 구매 즉시 열람 토큰 (주문 시 발급 → /read?t= 로만 열람 가능)
const readTokens = new Map();

// 유료 전자책 직접 접근 차단 → 스토어로 (URL 알아도 못 봄)
app.use((req, res, next) => {
  if (/^\/ebooks\/[^/]+\/paid-.*\.html$/i.test(req.path)) {
    return res.redirect("/home.html#store");
  }
  next();
});

// 구매 후 즉시 열람: 유효한 토큰이면 유료책 HTML 제공
app.get("/read", (req, res) => {
  const tok = readTokens.get(req.query.t);
  if (!tok) return res.redirect("/home.html#store");
  if (Date.now() - tok.created > 30 * 24 * 60 * 60 * 1000) { // 30일 유효
    readTokens.delete(req.query.t);
    return res.redirect("/home.html#store");
  }
  const rel = (tok.url || "").replace(/^\//, "");
  const file = join(__dirname, "public", rel);
  if (!/ebooks[\\/][^\\/]+[\\/]paid-.*\.html$/i.test(file) || !existsSync(file)) {
    return res.redirect("/home.html#store");
  }
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.send(readFileSync(file, "utf-8"));
});

app.use(express.static(join(__dirname, "public")));

// 전자책 다운로드 요청 (팔로우+좋아요 확인 후 발송)
app.post("/api/ebook-request", (req, res) => {
  const { name, email, instagram_handle, ebook_slug, confirmed_follow, confirmed_like } = req.body;
  if (!email) return res.status(400).json({ error: "이메일 필수" });
  if (/^paid-/i.test(ebook_slug || "")) {
    return res.status(403).json({ error: "유료 전자책은 스토어에서 구매해 주세요.", redirect: "/home.html#store" });
  }

  const requestsFile = join(dataDir, "ebook-requests.json");
  const reqs = existsSync(requestsFile) ? JSON.parse(readFileSync(requestsFile, "utf-8")) : [];

  const request = {
    id: reqs.length + 1,
    name: name || "",
    email,
    instagram_handle: instagram_handle || "",
    ebook_slug: ebook_slug || "",
    confirmed_follow: !!confirmed_follow,
    confirmed_like: !!confirmed_like,
    status: (confirmed_follow && confirmed_like) ? "approved" : "pending",
    created: new Date().toISOString(),
  };

  reqs.push(request);
  save(requestsFile, reqs);
  console.log(`📚 전자책 요청! #${request.id} — ${name} / ${email} / follow:${confirmed_follow} like:${confirmed_like}`);
  io.emit("ebook-request", request);

  // 팔로우+좋아요 확인되면 즉시 다운로드 URL 제공 (실제 존재하는 폴더에서 slug로 조회 — 오늘 날짜 가정 금지)
  if (request.status === "approved") {
    const matched = allEbooks().find(b => b.slug === ebook_slug);
    const downloadUrl = matched ? matched.url : null;
    if (!downloadUrl) {
      return res.json({ success: true, status: "pending", message: "전자책을 찾을 수 없어 확인 후 이메일로 보내드립니다." });
    }
    res.json({ success: true, status: "approved", message: "팔로우와 좋아요 감사합니다! 전자책을 바로 읽을 수 있습니다.", downloadUrl });
  } else {
    res.json({ success: true, status: "pending", message: "팔로우와 좋아요를 확인 후 이메일로 보내드립니다." });
  }
});

app.get("/api/ebook-requests", (req, res) => {
  const requestsFile = join(dataDir, "ebook-requests.json");
  res.json(existsSync(requestsFile) ? JSON.parse(readFileSync(requestsFile, "utf-8")) : []);
});

// 전자책 목록 API
function allEbooks() {
  const ebooksDir = join(__dirname, "public", "ebooks");
  if (!existsSync(ebooksDir)) return [];
  const dates = readdirSync(ebooksDir).filter(d => /\d{4}-\d{2}-\d{2}/.test(d)).sort().reverse();
  const all = [];
  for (const date of dates) {
    const indexFile = join(ebooksDir, date, "index.json");
    if (existsSync(indexFile)) {
      const data = JSON.parse(readFileSync(indexFile, "utf-8"));
      all.push(...(data.books || []));
    }
  }
  return all;
}

app.get("/api/ebooks", (req, res) => res.json(allEbooks()));

// 로컬 시스템 하트비트 (JARVIS PC → 관제탑, 30분마다)
let lastHeartbeat = null;
app.post("/api/heartbeat", (req, res) => {
  lastHeartbeat = { ...req.body, received: new Date().toISOString() };
  res.json({ ok: true });
});

// 오늘의 한 마디 (날짜 기반 자동 변경, 미리 만든 문구 풀에서)
app.get("/api/daily-message", (req, res) => {
  const file = join(__dirname, "public", "daily-messages.json");
  let msgs = [];
  try { msgs = JSON.parse(readFileSync(file, "utf-8")).messages || []; } catch {}
  if (!msgs.length) return res.json({ message: "오늘 하루도 수고 많으셨습니다." });
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 0);
  const day = Math.floor((now - start) / 86400000); // 올해 몇 번째 날
  res.json({ message: msgs[day % msgs.length], date: now.toISOString().slice(0, 10) });
});

// JARVIS 관제탑: 프로젝트 보드 + 실시간 지표 통합
app.get("/api/jarvis", (req, res) => {
  const boardFile = join(__dirname, "..", "config", "jarvis-board.json");
  const board = existsSync(boardFile) ? JSON.parse(readFileSync(boardFile, "utf-8")) : { projects: [], music: { tracks: [] }, schedulers: [], links: [], goal: { monthly: 5000000 }, updated: "-" };
  res.json({ board, metrics: getRealMetrics(), orders: getOrders(), heartbeat: lastHeartbeat });
});

// 메인 페이지를 홈페이지로 리디렉트
app.get("/", (req, res) => {
  res.sendFile(join(__dirname, "public", "home.html"));
});

import { writeFileSync, readFileSync, existsSync, mkdirSync, readdirSync } from "fs";

// === DATA LAYER ===
const dataDir = join(__dirname, "..", "data");
const ordersFile = join(dataDir, "orders.json");
const leadsFile = join(dataDir, "leads.json");
const metricsFile = join(dataDir, "metrics.json");
const directivesFile = join(dataDir, "directives.json");

function ensureDir() { if (!existsSync(dataDir)) mkdirSync(dataDir, { recursive: true }); }
function load(file) { return existsSync(file) ? JSON.parse(readFileSync(file, "utf-8")) : []; }
function save(file, data) { ensureDir(); writeFileSync(file, JSON.stringify(data, null, 2)); }

function getOrders() { return load(ordersFile); }
function saveOrders(o) { save(ordersFile, o); }
function getLeads() { return load(leadsFile); }
function saveLeads(l) { save(leadsFile, l); }
function getDirectives() { return load(directivesFile); }
function saveDirectives(d) { save(directivesFile, d); }

function getRealMetrics() {
  const orders = getOrders();
  const leads = getLeads();
  const today = new Date().toISOString().split("T")[0];
  const confirmedOrders = orders.filter(o => o.status !== "refunded");
  const todayOrders = confirmedOrders.filter(o => o.created && o.created.startsWith(today));
  const totalRevenue = confirmedOrders.reduce((s, o) => s + (o.amount || 0), 0);
  const todayRevenue = todayOrders.reduce((s, o) => s + (o.amount || 0), 0);

  return {
    revenue: { today: todayRevenue, month: totalRevenue, goal: 5000000 },
    orders: { total: orders.length, confirmed: orders.filter(o => o.status === "confirmed").length, pending: orders.filter(o => o.status === "pending").length, today: todayOrders.length },
    leads: { total: leads.length, today: leads.filter(l => l.created && l.created.startsWith(today)).length },
    subscribers: { youtube: 0, instagram: 0, newsletter: leads.length },
  };
}

// === API ROUTES ===

app.get("/api/orders", (req, res) => res.json(getOrders()));

app.put("/api/orders/:id", (req, res) => {
  const orders = getOrders();
  const order = orders.find(o => o.id === parseInt(req.params.id));
  if (!order) return res.status(404).json({ error: "not found" });
  order.status = req.body.status || order.status;
  saveOrders(orders);
  console.log(`📝 주문 #${order.id} → ${order.status}`);
  io.emit("order-update", order);
  io.emit("metrics-update", getRealMetrics());
  res.json(order);
});

app.get("/api/leads", (req, res) => res.json(getLeads()));
app.get("/api/stats", (req, res) => res.json(getRealMetrics()));

// 부서별 업무 지시 — 라이트하우스 그룹 조직도(company.html)에서 제출, JARVIS가 대화 시작 시 pending 항목을 확인·처리
app.get("/api/directives", (req, res) => res.json(getDirectives()));

app.post("/api/directives", (req, res) => {
  const { department, instruction } = req.body || {};
  if (!department || !instruction) return res.status(400).json({ error: "department, instruction 필요" });
  const directives = getDirectives();
  const item = {
    id: (directives.at(-1)?.id || 0) + 1,
    department,
    instruction,
    status: "pending",
    created: new Date().toISOString(),
  };
  directives.push(item);
  saveDirectives(directives);
  io.emit("directive-new", item);
  console.log(`📋 업무 지시 접수 [${department}] ${instruction}`);
  res.json(item);
});

app.put("/api/directives/:id", (req, res) => {
  const directives = getDirectives();
  const item = directives.find(d => d.id === parseInt(req.params.id));
  if (!item) return res.status(404).json({ error: "not found" });
  item.status = req.body.status || item.status;
  if (req.body.result) item.result = req.body.result;
  item.updated = new Date().toISOString();
  saveDirectives(directives);
  io.emit("directive-update", item);
  res.json(item);
});

// 채널 실시간 데이터 API (YouTube + Instagram + Facebook)
app.get("/api/channels", async (req, res) => {
  const result = { youtube: null, instagram: null, facebook: null };

  // 토큰 로드
  const tokensPath = join(__dirname, "..", "config", "tokens.json");
  let tokens = {};
  if (existsSync(tokensPath)) tokens = JSON.parse(readFileSync(tokensPath, "utf-8"));

  const igToken = tokens.instagram;
  const fbToken = tokens.facebook_page;

  // Instagram
  if (igToken) {
    try {
      const igResp = await fetch(`https://graph.facebook.com/v21.0/17841425580883266?fields=name,username,followers_count,follows_count,media_count&access_token=${igToken}`);
      const igData = await igResp.json();
      if (!igData.error) {
        // 최근 게시물
        const mediaResp = await fetch(`https://graph.facebook.com/v21.0/17841425580883266/media?fields=id,caption,media_type,timestamp,like_count&limit=5&access_token=${igToken}`);
        const mediaData = await mediaResp.json();
        result.instagram = {
          followers: igData.followers_count || 0,
          following: igData.follows_count || 0,
          media_count: igData.media_count || 0,
          username: igData.username,
          recentPosts: mediaData.data || [],
        };
      }
    } catch(e) {}
  }

  // Facebook
  if (fbToken) {
    try {
      const fbResp = await fetch(`https://graph.facebook.com/v21.0/1097948196731052?fields=name,fan_count,category,posts.limit(5){message,created_time}&access_token=${fbToken}`);
      const fbData = await fbResp.json();
      if (!fbData.error) {
        result.facebook = {
          fans: fbData.fan_count || 0,
          category: fbData.category || '',
          posts_count: fbData.posts?.data?.length || 0,
          recentPosts: fbData.posts?.data || [],
        };
      }
    } catch(e) {}
  }

  // YouTube (Python 스크립트 호출)
  try {
    const { execSync } = await import("child_process");
    const ytJson = execSync("python scripts/youtube-data.py", { cwd: join(__dirname, ".."), timeout: 15000, encoding: "utf-8" });
    result.youtube = JSON.parse(ytJson.trim());
  } catch(e) {}

  res.json(result);
});

// === 에이전트 상태 (실제 작동 기반) ===
const agentDefs = [
  { id: "trend-researcher", name: "트렌드 리서처", dept: "콘텐츠", floor: 3 },
  { id: "content-director", name: "콘텐츠 디렉터", dept: "콘텐츠", floor: 3 },
  { id: "scriptwriter", name: "스크립트 작가", dept: "콘텐츠", floor: 3 },
  { id: "copywriter", name: "카피라이터", dept: "콘텐츠", floor: 3 },
  { id: "seo", name: "SEO 담당", dept: "마케팅", floor: 2 },
  { id: "video-editor", name: "영상 편집", dept: "제작", floor: 2 },
  { id: "thumbnail", name: "썸네일 기획", dept: "제작", floor: 2 },
  { id: "audio", name: "오디오 관리", dept: "제작", floor: 2 },
  { id: "designer", name: "디자이너", dept: "제작", floor: 2 },
  { id: "subtitle", name: "자막 담당", dept: "제작", floor: 2 },
  { id: "marketing", name: "마케팅 총괄", dept: "마케팅", floor: 2 },
  { id: "youtube-ops", name: "유튜브 운영", dept: "운영", floor: 1 },
  { id: "instagram-ops", name: "인스타 운영", dept: "운영", floor: 1 },
  { id: "newsletter", name: "뉴스레터", dept: "운영", floor: 1 },
  { id: "ads", name: "광고 운영", dept: "마케팅", floor: 2 },
  { id: "product-planner", name: "상품 기획", dept: "상품", floor: 1 },
  { id: "sales-copy", name: "판매 카피", dept: "상품", floor: 1 },
  { id: "customer-journey", name: "고객 여정", dept: "마케팅", floor: 2 },
  { id: "payment", name: "결제 자동화", dept: "운영", floor: 1 },
  { id: "support", name: "고객 지원", dept: "고객", floor: 1 },
  { id: "community", name: "커뮤니티", dept: "고객", floor: 1 },
  { id: "reviews", name: "후기 관리", dept: "고객", floor: 1 },
  { id: "analytics", name: "데이터 분석", dept: "분석", floor: 4 },
  { id: "ab-testing", name: "A/B 테스트", dept: "분석", floor: 4 },
  { id: "competitor", name: "경쟁사 분석", dept: "분석", floor: 4 },
  { id: "automation", name: "자동화 관리", dept: "기술", floor: 4 },
  { id: "security", name: "보안 관리", dept: "기술", floor: 4 },
  { id: "ceo-secretary", name: "CEO 비서", dept: "경영", floor: 5 },
  { id: "finance", name: "재무 담당", dept: "경영", floor: 5 },
  { id: "operations", name: "운영 총괄", dept: "경영", floor: 5 },
];

const agentStatus = {};
agentDefs.forEach(a => { agentStatus[a.id] = "idle"; });

// 실시간 이벤트 기반 에이전트 활동 (주문/리드 발생시만 반응)
function triggerAgent(id, duration = 3000) {
  agentStatus[id] = "working";
  io.emit("agent-update", { id, status: "working" });
  setTimeout(() => {
    agentStatus[id] = "done";
    io.emit("agent-update", { id, status: "done" });
    setTimeout(() => {
      agentStatus[id] = "idle";
      io.emit("agent-update", { id, status: "idle" });
    }, 2000);
  }, duration);
}

// 주문 발생 시 관련 에이전트 활성화
function onNewOrder(order) {
  triggerAgent("payment", 2000);
  setTimeout(() => triggerAgent("ceo-secretary", 3000), 1000);
  setTimeout(() => {
    triggerAgent("finance", 2000);
    io.emit("data-flow", { from: "payment", to: "ceo-secretary" });
  }, 2500);
  setTimeout(() => {
    triggerAgent("analytics", 2000);
    io.emit("data-flow", { from: "ceo-secretary", to: "finance" });
    io.emit("data-flow", { from: "finance", to: "analytics" });
  }, 4000);
}

// 리드 발생 시 관련 에이전트 활성화
function onNewLead(lead) {
  triggerAgent("newsletter", 2000);
  setTimeout(() => triggerAgent("customer-journey", 2000), 1500);
  setTimeout(() => {
    triggerAgent("marketing", 2000);
    io.emit("data-flow", { from: "newsletter", to: "customer-journey" });
  }, 3000);
}

// 이벤트 후킹
io.on("connection", (socket) => {
  console.log("📺 클라이언트 연결");
  socket.emit("init", {
    agents: agentDefs.map(a => ({ ...a, status: agentStatus[a.id] })),
    metrics: getRealMetrics(),
  });

  socket.on("run-pipeline", (name) => {
    console.log(`🚀 파이프라인: ${name}`);
    let pipeline = [];
    if (name === "content") pipeline = ["trend-researcher","content-director","scriptwriter","copywriter","seo","thumbnail","designer","video-editor"];
    else if (name === "marketing") pipeline = ["marketing","instagram-ops","youtube-ops","newsletter","ads"];
    else if (name === "analysis") pipeline = ["analytics","ab-testing","competitor","finance"];
    else pipeline = [...new Set(["trend-researcher","content-director","scriptwriter","copywriter","seo","thumbnail","designer","video-editor","marketing","instagram-ops","youtube-ops","newsletter","analytics","finance","ceo-secretary","operations"])];

    let delay = 0;
    pipeline.forEach((id, i) => {
      setTimeout(() => {
        triggerAgent(id, 3000);
        io.emit("pipeline-progress", { name, step: i+1, total: pipeline.length, current: id });
        if (i > 0) io.emit("data-flow", { from: pipeline[i-1], to: id });
      }, delay);
      delay += 1500;
    });
  });
});

// 실제 이벤트 리스너
const origEmit = io.emit.bind(io);
const _origPost = app.post;

// 주문/리드 이벤트에 에이전트 반응 연결
io.on("connection", () => {});
// 기존 라우트에서 이벤트 처리
const origOrderHandler = app._router.stack.find(r => r.route?.path === "/api/order" && r.route?.methods?.post);
const origLeadHandler = app._router.stack.find(r => r.route?.path === "/api/lead" && r.route?.methods?.post);

// 실시간 연결시 주문/리드 발생하면 에이전트 활성화
io.on("connection", (socket) => {
  socket.onAny((event, data) => {
    if (event === "sale") onNewOrder(data);
    if (event === "new-lead") onNewLead(data);
  });
});

// 전자책 다운로드 토큰 관리
const downloadTokens = new Map();

// 무료 전자책: 리드 등록 후 다운로드 토큰 발급
app.post("/api/lead", (req, res) => {
  const leads = getLeads();
  const lead = { id: leads.length + 1, ...req.body, status: "new", created: new Date().toISOString() };
  leads.push(lead);
  saveLeads(leads);
  console.log(`📧 새 리드! #${lead.id} — ${lead.name} / ${lead.email}`);

  notify(
    `📧 새 구독자 #${lead.id} — ${lead.name || lead.email}`,
    `무료 전자책 신청/뉴스레터 구독이 들어왔습니다.\n\n이름: ${lead.name || "-"}\n이메일: ${lead.email}\n시각: ${lead.created}`
  );

  // 다운로드 토큰 발급
  const token = Date.now().toString(36) + Math.random().toString(36).slice(2);
  downloadTokens.set(token, { type: "free", email: lead.email, created: Date.now() });

  io.emit("new-lead", lead);
  io.emit("metrics-update", getRealMetrics());
  onNewLead(lead);
  res.json({ success: true, leadId: lead.id, downloadUrl: `/ebook-free.html?token=${token}` });
});

// 유료 전자책: 주문 후 다운로드 토큰 발급
app.post("/api/order", (req, res) => {
  const orders = getOrders();
  const order = { id: orders.length + 1, ...req.body, status: "pending", created: new Date().toISOString() };
  orders.push(order);
  saveOrders(orders);
  console.log(`\n💰 새 주문! #${order.id} — ${order.name} / ${order.email} / ${order.amount?.toLocaleString()}원`);

  notify(
    `💰 새 주문 #${order.id} — ${order.name}님 ${order.amount?.toLocaleString()}원`,
    [
      `새 주문이 접수되었습니다!`,
      ``,
      `상품: ${order.product || "-"}`,
      `입금자명: ${order.name}`,
      `이메일: ${order.email}`,
      `연락처: ${order.phone || "-"}`,
      `금액: ${order.amount?.toLocaleString()}원`,
      `시각: ${order.created}`,
      ``,
      `▶ 할 일: 농협 185-12-226647 입금 확인 후, 위 이메일로 PDF를 보내주세요.`,
      `▶ 주문 관리: https://lighthouse-media.onrender.com/admin.html`,
    ].join("\n")
  );

  io.emit("sale", { amount: order.amount, product: order.product, name: order.name });
  io.emit("metrics-update", getRealMetrics());
  io.emit("order-new", order);
  onNewOrder(order);

  // 즉시 열람: 책 URL이 있으면 열람 토큰 발급 (계좌이체 신뢰 방식)
  let readUrl = null;
  if (order.bookUrl && /paid-.*\.html$/i.test(order.bookUrl)) {
    const token = Date.now().toString(36) + Math.random().toString(36).slice(2);
    readTokens.set(token, { url: order.bookUrl, email: order.email, orderId: order.id, created: Date.now() });
    readUrl = `/read?t=${token}`;
  }
  res.json({ success: true, orderId: order.id, readUrl });
});

// 주기적 메트릭 브로드캐스트 (30초)
setInterval(() => {
  io.emit("metrics-update", getRealMetrics());
}, 30000);

// 만료된 토큰 정리 (24시간)
setInterval(() => {
  const now = Date.now();
  for (const [token, data] of downloadTokens) {
    if (now - data.created > 24 * 60 * 60 * 1000) downloadTokens.delete(token);
  }
}, 60000);

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`\n🏢 Lighthouse Media — 실시간 운영 시스템`);
  console.log(`   대시보드:   http://localhost:${PORT}`);
  console.log(`   판매페이지: http://localhost:${PORT}/shop.html`);
  console.log(`   무료 PDF:   http://localhost:${PORT}/free.html`);
  console.log(`   책 표지:    http://localhost:${PORT}/covers.html`);
  console.log(`   관리자:     http://localhost:${PORT}/admin.html`);
  console.log(`   무료 전자책: http://localhost:${PORT}/ebook-free.html`);
  console.log(`   유료 전자책: (비공개 — 입금 확인 후 PDF 이메일 발송)\n`);
});
