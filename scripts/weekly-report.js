import Anthropic from "@anthropic-ai/sdk";
import { writeFileSync, readFileSync, existsSync, mkdirSync } from "fs";
import { join } from "path";
import { config } from "dotenv";

config();

const client = new Anthropic();
const OUTPUT_DIR = join(import.meta.dirname, "..", "output");
const DATA_DIR = join(import.meta.dirname, "..", "data");

// 재무 데이터 저장소
function getFinanceData() {
  const filePath = join(DATA_DIR, "finance.json");
  if (existsSync(filePath)) {
    return JSON.parse(readFileSync(filePath, "utf-8"));
  }
  return {
    weeks: [],
    monthly_costs: {
      tools: [
        { name: "Claude Pro", cost: 22000 },
        { name: "Canva Pro", cost: 14900 },
        { name: "ChatGPT Plus", cost: 28000 },
        { name: "Stibee", cost: 0 },
        { name: "Descript", cost: 33000 },
        { name: "도메인/호스팅", cost: 15000 },
      ],
      total_monthly_fixed: 112900,
    },
  };
}

function saveFinanceData(data) {
  if (!existsSync(DATA_DIR)) mkdirSync(DATA_DIR, { recursive: true });
  writeFileSync(join(DATA_DIR, "finance.json"), JSON.stringify(data, null, 2));
}

async function generateWeeklyReport() {
  const finance = getFinanceData();
  const today = new Date();
  const weekStart = new Date(today);
  weekStart.setDate(today.getDate() - today.getDay());

  // 시뮬레이션 데이터 (실제로는 API에서 가져옴)
  const weekData = {
    period: `${weekStart.toISOString().split("T")[0]} ~ ${today.toISOString().split("T")[0]}`,
    revenue: {
      youtube_adsense: Math.floor(Math.random() * 50000 + 30000),
      instagram_sponsorship: 0,
      ebook_sales: Math.floor(Math.random() * 5) * 14900 + Math.floor(Math.random() * 3) * 29900,
      newsletter_affiliate: Math.floor(Math.random() * 20000),
    },
    costs: {
      fixed: finance.monthly_costs.total_monthly_fixed / 4,
      ads: 0,
      freelance: 0,
    },
    youtube: {
      views: Math.floor(Math.random() * 30000 + 20000),
      subscribers_gained: Math.floor(Math.random() * 100 + 50),
      avg_ctr: (Math.random() * 3 + 4).toFixed(1),
      avg_watch_time: (Math.random() * 3 + 4).toFixed(1),
      top_video: "이번 주 베스트 영상",
    },
    instagram: {
      reach: Math.floor(Math.random() * 50000 + 30000),
      followers_gained: Math.floor(Math.random() * 200 + 80),
      saves: Math.floor(Math.random() * 500 + 200),
      top_post_type: "카드뉴스",
    },
    newsletter: {
      sent: Math.floor(Math.random() * 100 + 800),
      open_rate: (Math.random() * 10 + 38).toFixed(1),
      click_rate: (Math.random() * 5 + 5).toFixed(1),
      new_subscribers: Math.floor(Math.random() * 30 + 10),
    },
  };

  const totalRevenue = Object.values(weekData.revenue).reduce((a, b) => a + b, 0);
  const totalCosts = Object.values(weekData.costs).reduce((a, b) => a + b, 0);
  const profit = totalRevenue - totalCosts;
  const margin = totalRevenue > 0 ? ((profit / totalRevenue) * 100).toFixed(1) : 0;

  const reportPrompt = `너는 Lighthouse Media의 재무 분석가다. 다음 주간 데이터를 분석해서 경영진 리포트를 작성하라.

[주간 데이터]
기간: ${weekData.period}

[매출]
- 유튜브 애드센스: ${weekData.revenue.youtube_adsense.toLocaleString()}원
- 인스타 협찬: ${weekData.revenue.instagram_sponsorship.toLocaleString()}원
- 전자책 판매: ${weekData.revenue.ebook_sales.toLocaleString()}원
- 뉴스레터 제휴: ${weekData.revenue.newsletter_affiliate.toLocaleString()}원
- 총 매출: ${totalRevenue.toLocaleString()}원

[비용]
- 고정비(도구): ${weekData.costs.fixed.toLocaleString()}원
- 광고비: ${weekData.costs.ads.toLocaleString()}원
- 총 비용: ${totalCosts.toLocaleString()}원

[순이익] ${profit.toLocaleString()}원 (마진율: ${margin}%)
[월 매출 목표] 5,000,000원 (현재 진행률: 월 환산 ${(totalRevenue * 4).toLocaleString()}원)

[유튜브]
- 주간 조회수: ${weekData.youtube.views.toLocaleString()}
- 구독자 증가: +${weekData.youtube.subscribers_gained}
- CTR: ${weekData.youtube.avg_ctr}%
- 평균 시청시간: ${weekData.youtube.avg_watch_time}분

[인스타그램]
- 주간 도달: ${weekData.instagram.reach.toLocaleString()}
- 팔로워 증가: +${weekData.instagram.followers_gained}
- 저장수: ${weekData.instagram.saves}

[뉴스레터]
- 발송: ${weekData.newsletter.sent}명
- 오픈율: ${weekData.newsletter.open_rate}%
- 클릭률: ${weekData.newsletter.click_rate}%
- 신규 구독: +${weekData.newsletter.new_subscribers}

리포트 형식:
[매출 상세] — 채널별 분석, 전주 대비 추세
[비용 상세] — 항목별 효율성
[순이익 및 마진율] — 목표 70% 대비 현황
[다음 주 예상] — 근거 기반 예측
[개선 제안 3가지] — 실행 가능한 액션
[위험 신호] — ROI 낮은 채널, 하락 추세`;

  const message = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 3000,
    messages: [{ role: "user", content: reportPrompt }],
  });

  const report = message.content[0].text;

  // 저장
  finance.weeks.push({ ...weekData, totalRevenue, totalCosts, profit, margin, generated: today.toISOString() });
  saveFinanceData(finance);

  const reportDir = join(OUTPUT_DIR, "reports");
  if (!existsSync(reportDir)) mkdirSync(reportDir, { recursive: true });
  writeFileSync(join(reportDir, `weekly-${today.toISOString().split("T")[0]}.md`), `# Lighthouse Media 주간 리포트\n## ${weekData.period}\n\n${report}`);

  console.log(`\n📊 주간 리포트 생성 완료`);
  console.log(`   매출: ${totalRevenue.toLocaleString()}원 | 비용: ${totalCosts.toLocaleString()}원 | 순이익: ${profit.toLocaleString()}원 (${margin}%)`);
  console.log(`   저장: output/reports/weekly-${today.toISOString().split("T")[0]}.md\n`);

  return { weekData, report };
}

generateWeeklyReport().catch(console.error);
