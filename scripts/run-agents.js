import { AgentOrchestrator } from "../agents/core.js";
import { createAllAgents } from "../agents/definitions.js";
import cron from "node-cron";

const orchestrator = new AgentOrchestrator();
const agents = createAllAgents();
agents.forEach((a) => orchestrator.register(a));

console.log(`\n🏢 Lighthouse Media — Agent System Online`);
console.log(`   등록된 에이전트: ${agents.length}개\n`);

// 각 에이전트의 스케줄에 따라 cron 등록
agents.forEach((agent) => {
  if (agent.schedule) {
    cron.schedule(agent.schedule, async () => {
      console.log(`⏰ [${new Date().toLocaleTimeString("ko-KR")}] ${agent.name} 실행 시작`);
      try {
        await agent.execute();
        console.log(`✅ ${agent.name} 완료`);
      } catch (err) {
        console.error(`❌ ${agent.name} 실패: ${err.message}`);
      }
    });
    console.log(`   📅 ${agent.name} (${agent.role}) → ${agent.schedule}`);
  }
});

console.log(`\n   모든 스케줄 등록 완료. 대기 중...\n`);

// 상태 확인 API용으로 export
export { orchestrator };
