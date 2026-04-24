import express from "express";
import { createServer } from "http";
import { Server } from "socket.io";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const server = createServer(app);
const io = new Server(server);

app.use(express.json());
app.use(express.static(join(__dirname, "public")));

// 전자책 다운로드 요청 (팔로우+좋아요 확인 후 발송)
app.post("/api/ebook-request", (req, res) => {
  const { name, email, instagram_handle, ebook_slug, confirmed_follow, confirmed_like } = req.body;
  if (!email) return res.status(400).json({ error: "이메일 필수" });

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

  // 팔로우+좋아요 확인되면 즉시 다운로드 URL 제공
  if (request.status === "approved") {
    res.json({ success: true, status: "approved", message: "팔로우와 좋아요 감사합니다! 전자책을 바로 읽을 수 있습니다.", downloadUrl: `/ebooks/${new Date().toISOString().split("T")[0]}/${ebook_slug}.html` });
  } else {
    res.json({ success: true, status: "pending", message: "팔로우와 좋아요를 확인 후 이메일로 보내드립니다." });
  }
});

app.get("/api/ebook-requests", (req, res) => {
  const requestsFile = join(dataDir, "ebook-requests.json");
  res.json(existsSync(requestsFile) ? JSON.parse(readFileSync(requestsFile, "utf-8")) : []);
});

// 전자책 목록 API
app.get("/api/ebooks", (req, res) => {
  const ebooksDir = join(__dirname, "public", "ebooks");
  if (!existsSync(ebooksDir)) return res.json([]);
  const dates = readdirSync(ebooksDir).filter(d => /\d{4}-\d{2}-\d{2}/.test(d)).sort().reverse();
  const all = [];
  for (const date of dates.slice(0, 7)) {
    const indexFile = join(ebooksDir, date, "index.json");
    if (existsSync(indexFile)) {
      const data = JSON.parse(readFileSync(indexFile, "utf-8"));
      all.push(...(data.books || []));
    }
  }
  res.json(all);
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

function ensureDir() { if (!existsSync(dataDir)) mkdirSync(dataDir, { recursive: true }); }
function load(file) { return existsSync(file) ? JSON.parse(readFileSync(file, "utf-8")) : []; }
function save(file, data) { ensureDir(); writeFileSync(file, JSON.stringify(data, null, 2)); }

function getOrders() { return load(ordersFile); }
function saveOrders(o) { save(ordersFile, o); }
function getLeads() { return load(leadsFile); }
function saveLeads(l) { save(leadsFile, l); }

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

  // 다운로드 토큰 발급 (결제 확인 전에도 열람 가능)
  const token = Date.now().toString(36) + Math.random().toString(36).slice(2);
  downloadTokens.set(token, { type: "paid", email: order.email, orderId: order.id, created: Date.now() });

  io.emit("sale", { amount: order.amount, product: order.product, name: order.name });
  io.emit("metrics-update", getRealMetrics());
  io.emit("order-new", order);
  onNewOrder(order);
  res.json({ success: true, orderId: order.id, downloadUrl: `/ebook-paid.html?token=${token}` });
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
  console.log(`   유료 전자책: http://localhost:${PORT}/ebook-paid.html\n`);
});
