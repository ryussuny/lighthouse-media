import { AgentOrchestrator } from "../agents/core.js";
import { createAllAgents } from "../agents/definitions.js";
import { writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";

const OUTPUT_DIR = join(import.meta.dirname, "..", "output");
const today = new Date().toISOString().split("T")[0];

async function runDailyRoutine() {
  console.log(`\n═══════════════════════════════════════════`);
  console.log(`  LIGHTHOUSE MEDIA — 일일 루틴 시작`);
  console.log(`  ${today} ${new Date().toLocaleTimeString("ko-KR")}`);
  console.log(`═══════════════════════════════════════════\n`);

  const orchestrator = new AgentOrchestrator();
  const agents = createAllAgents();
  agents.forEach((a) => orchestrator.register(a));

  // 실시간 상태 출력
  orchestrator.on("agent-update", ({ agent, status }) => {
    const icon = status === "working" ? "⚙️" : status === "done" ? "✅" : "❌";
    console.log(`  ${icon} [${agent}] ${status}`);
  });

  // === 파이프라인 1: 콘텐츠 제작 ===
  console.log("\n▶ 파이프라인 1: 콘텐츠 제작");
  console.log("─────────────────────────────────────────");

  const contentResult = await orchestrator.runPipeline("content-production", [
    {
      agent: "trend-researcher",
      input: `오늘 날짜: ${today}
우리 타겟: 20대 후반~40대 직장인, 번아웃/자기계발/마음관리
최근 우리 채널에서 잘 된 주제: "월요병 극복법" (조회수 12만), "5분 마음챙김" (저장 800건)
오늘의 트렌드 키워드 10개를 분석해주세요.`,
    },
    {
      agent: "content-director",
      inputBuilder: (ctx) => `[트렌드 리서처 결과]\n${ctx["trend-researcher"]}\n\n이 키워드를 바탕으로 오늘 제작할 주제 3개를 선정해주세요.`,
    },
    {
      agent: "scriptwriter",
      inputBuilder: (ctx) => `[콘텐츠 디렉터 결정]\n${ctx["content-director"]}\n\n유튜브 롱폼 주제에 대해 풀 스크립트를 작성해주세요.`,
    },
    {
      agent: "copywriter",
      inputBuilder: (ctx) => `[오늘의 콘텐츠]\n${ctx["content-director"]}\n\n각 콘텐츠에 대해 제목, 썸네일 문구, 인스타 첫 문장을 작성해주세요.`,
    },
    {
      agent: "seo",
      inputBuilder: (ctx) => `[오늘의 콘텐츠와 카피]\n콘텐츠: ${ctx["content-director"]}\n카피: ${ctx["copywriter"]}\n\nSEO 최적화를 적용해주세요.`,
    },
    {
      agent: "thumbnail",
      inputBuilder: (ctx) => `[오늘의 유튜브 콘텐츠]\n${ctx["content-director"]}\n\n썸네일 3안을 기획해주세요.`,
    },
    {
      agent: "designer",
      inputBuilder: (ctx) => `[카드뉴스 주제]\n${ctx["content-director"]}\n\n인스타 카드뉴스 10장 디자인 지시서를 만들어주세요.`,
    },
    {
      agent: "video-editor",
      inputBuilder: (ctx) => `[스크립트]\n${ctx["scriptwriter"]}\n\n편집 지시서를 작성해주세요.`,
    },
    {
      agent: "audio",
      inputBuilder: (ctx) => `[스크립트]\n${ctx["scriptwriter"]}\n\n더빙용 스크립트로 변환하고 BGM 큐시트를 작성해주세요.`,
    },
    {
      agent: "subtitle",
      inputBuilder: (ctx) => `[스크립트]\n${ctx["scriptwriter"]}\n\n한국어 SRT 자막과 영어 자막을 생성해주세요.`,
    },
  ]);

  // === 파이프라인 2: 경영/분석 ===
  console.log("\n▶ 파이프라인 2: 경영 리포트");
  console.log("─────────────────────────────────────────");

  const managementResult = await orchestrator.runPipeline("management", [
    {
      agent: "ceo-secretary",
      input: `오늘 날짜: ${today}
어제 성과 데이터:
- 유튜브: 신규 조회수 8,500 / 구독자 +23 / CTR 5.2%
- 인스타: 도달 12,000 / 저장 340 / 팔로워 +45
- 뉴스레터: 오픈율 42% / 클릭률 8%
- 매출: 전자책 2건(29,800원) / 애드센스 15,200원

전일 대비 및 주간 추이를 분석하고 오늘의 우선순위를 제안해주세요.`,
    },
    {
      agent: "operations",
      inputBuilder: (ctx) => {
        const status = orchestrator.getStatus();
        const summary = Object.values(status).map((s) => `${s.name}: ${s.status}`).join("\n");
        return `[전 부서 상태]\n${summary}\n\n운영 현황을 점검하고 병목을 보고해주세요.`;
      },
    },
  ]);

  // === 결과 저장 ===
  const dailyDir = join(OUTPUT_DIR, today);
  if (!existsSync(dailyDir)) mkdirSync(dailyDir, { recursive: true });

  const outputs = {
    trends: contentResult["trend-researcher"],
    topics: contentResult["content-director"],
    script: contentResult["scriptwriter"],
    copy: contentResult["copywriter"],
    seo: contentResult["seo"],
    thumbnail: contentResult["thumbnail"],
    cardnews: contentResult["designer"],
    editing: contentResult["video-editor"],
    audio: contentResult["audio"],
    subtitle: contentResult["subtitle"],
    ceo_report: managementResult["ceo-secretary"],
    operations: managementResult["operations"],
  };

  for (const [key, value] of Object.entries(outputs)) {
    if (value) {
      writeFileSync(join(dailyDir, `${key}.md`), value, "utf-8");
    }
  }

  // 전체 리포트 저장
  const fullReport = `# Lighthouse Media 일일 리포트 — ${today}\n\n` +
    Object.entries(outputs)
      .filter(([, v]) => v)
      .map(([k, v]) => `## ${k}\n\n${v}`)
      .join("\n\n---\n\n");

  writeFileSync(join(dailyDir, "full-report.md"), fullReport, "utf-8");

  console.log(`\n═══════════════════════════════════════════`);
  console.log(`  ✅ 일일 루틴 완료 — 결과: output/${today}/`);
  console.log(`═══════════════════════════════════════════\n`);

  return { outputs, status: orchestrator.getStatus(), log: orchestrator.getDailyLog() };
}

runDailyRoutine().catch(console.error);
