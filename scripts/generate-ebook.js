import Anthropic from "@anthropic-ai/sdk";
import { writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";
import { config } from "dotenv";

config();

const client = new Anthropic();
const PRODUCTS_DIR = join(import.meta.dirname, "..", "products");

async function generateEbook(topic, type = "full") {
  console.log(`\n📖 전자책 생성 시작: "${topic}"`);
  console.log(`   유형: ${type === "lead" ? "리드마그넷 (7p)" : "풀 전자책 (50-80p)"}\n`);

  // Step 1: 목차 생성
  console.log("   [1/4] 목차 생성 중...");
  const tocResponse = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 2000,
    messages: [{
      role: "user",
      content: `전자책 목차를 만들어줘.

주제: ${topic}
타겟: 20대 후반~40대 직장인 (번아웃/자기계발/마음관리)
톤: 따뜻하고 지적이며 실용적
유형: ${type === "lead" ? "리드마그넷 (7페이지, 5챕터)" : "풀 전자책 (50-80페이지, 8-12챕터)"}

[출력 형식]
전자책 제목:
부제:
전체 페이지 예상:

챕터 목록:
- 챕터 1: [제목] — 핵심 메시지 / 예상 페이지수
- 챕터 2: ...

각 챕터는 독자가 "이것만은 가져간다"는 핵심 인사이트가 있어야 함.
마지막 챕터는 반드시 실천 워크시트 포함.`,
    }],
  });

  const toc = tocResponse.content[0].text;
  console.log("   ✅ 목차 완료");

  // Step 2: 각 챕터 작성
  console.log("   [2/4] 본문 작성 중...");
  const chaptersResponse = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 4096,
    messages: [
      { role: "user", content: `다음 목차로 전자책 전체 본문을 작성해줘.\n\n${toc}\n\n[작성 기준]\n- 각 챕터 2,000~3,000자\n- 실제 사례/연구 인용\n- 실천 가능한 팁 포함\n- 톤: 따뜻하고 지적이며 실용적\n- 금지: 과장, 선동, "인생이 바뀝니다" 류\n- 마크다운 형식` },
    ],
  });

  const chapters = chaptersResponse.content[0].text;
  console.log("   ✅ 본문 완료");

  // Step 3: 랜딩페이지 카피
  console.log("   [3/4] 랜딩페이지 카피 생성 중...");
  const landingResponse = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 2000,
    messages: [{
      role: "user",
      content: `다음 전자책의 랜딩페이지 판매 카피를 작성해줘.

${toc}

[구조]
1. 헤드라인 (Before→After)
2. 서브헤드 (누구에게 필요한지)
3. 문제 공감 5개
4. 해결책 제시
5. 목차 미리보기
6. 구매자 후기 3개 (가상)
7. FAQ 5개
8. 가격: ${type === "lead" ? "무료" : "14,900원"}
9. CTA

금지: "놓치면 후회", "단 3명만", "인생이 바뀝니다"
솔직하고 구체적으로.`,
    }],
  });

  const landing = landingResponse.content[0].text;
  console.log("   ✅ 랜딩페이지 카피 완료");

  // Step 4: 홍보 콘텐츠
  console.log("   [4/4] 홍보 콘텐츠 생성 중...");
  const promoResponse = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 2000,
    messages: [{
      role: "user",
      content: `다음 전자책 홍보를 위한 콘텐츠를 만들어줘.

${toc}

1. 인스타 카드뉴스 텍스트 (10장, 각 장 50자 이내)
2. 유튜브 숏폼 스크립트 (60초)
3. 뉴스레터 홍보 섹션 (200자)
4. 스레드 게시물 3개

톤: 따뜻하고 지적이며 실용적`,
    }],
  });

  const promo = promoResponse.content[0].text;
  console.log("   ✅ 홍보 콘텐츠 완료");

  // 저장
  const slug = topic.replace(/[^가-힣a-zA-Z0-9]/g, "-").substring(0, 30);
  const ebookDir = join(PRODUCTS_DIR, `ebook-${slug}`);
  if (!existsSync(ebookDir)) mkdirSync(ebookDir, { recursive: true });

  writeFileSync(join(ebookDir, "01-toc.md"), `# 목차\n\n${toc}`);
  writeFileSync(join(ebookDir, "02-content.md"), `# ${topic}\n\n${chapters}`);
  writeFileSync(join(ebookDir, "03-landing-page.md"), `# 랜딩페이지\n\n${landing}`);
  writeFileSync(join(ebookDir, "04-promo.md"), `# 홍보 콘텐츠\n\n${promo}`);

  console.log(`\n   📦 전자책 생성 완료!`);
  console.log(`   위치: products/ebook-${slug}/`);
  console.log(`   - 01-toc.md (목차)`);
  console.log(`   - 02-content.md (본문)`);
  console.log(`   - 03-landing-page.md (랜딩페이지)`);
  console.log(`   - 04-promo.md (홍보 콘텐츠)\n`);

  return { toc, chapters, landing, promo };
}

// CLI 실행
const topic = process.argv[2] || "월요일이 무섭지 않은 사람들의 5가지 습관";
const type = process.argv[3] || "full";
generateEbook(topic, type).catch(console.error);
