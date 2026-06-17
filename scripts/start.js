#!/usr/bin/env node
/**
 * Lighthouse Media — 전체 시스템 시작
 *
 * 사용법:
 *   node scripts/start.js          → 대시보드 + 시뮬레이션 모드
 *   node scripts/start.js --live   → 대시보드 + 실제 AI 에이전트 실행
 *   node scripts/start.js --daily  → 일일 루틴만 실행 (1회)
 *   node scripts/start.js --ebook "주제"  → 전자책 생성
 *   node scripts/start.js --report → 주간 리포트 생성
 */

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

const args = process.argv.slice(2);

console.log(`
╔══════════════════════════════════════════════════╗
║                                                  ║
║     🏢  L I G H T H O U S E   M E D I A        ║
║                                                  ║
║     AI-Powered Content & Media Company           ║
║     "실제로 삶이 나아지는 콘텐츠"                ║
║                                                  ║
╚══════════════════════════════════════════════════╝

  30 AI Agents | 5 Departments | 1 Mission
  Target: 월 매출 500만원
`);

if (args.includes("--daily")) {
  console.log("▶ 일일 루틴 실행...\n");
  spawn("node", [join(__dirname, "daily-routine.js")], { stdio: "inherit", cwd: ROOT });
} else if (args.includes("--report")) {
  console.log("▶ 주간 리포트 생성...\n");
  spawn("node", [join(__dirname, "weekly-report.js")], { stdio: "inherit", cwd: ROOT });
} else if (args.includes("--ebook")) {
  const topicIdx = args.indexOf("--ebook") + 1;
  const topic = args[topicIdx] || "번아웃에서 벗어나는 7일 루틴";
  console.log(`▶ 전자책 생성: "${topic}"\n`);
  spawn("node", [join(__dirname, "generate-ebook.js"), topic], { stdio: "inherit", cwd: ROOT });
} else {
  // 기본: 대시보드 실행
  console.log("▶ 3D 대시보드 시작...\n");
  const dashboard = spawn("node", [join(ROOT, "dashboard", "server.js")], { stdio: "inherit", cwd: ROOT });

  if (args.includes("--live")) {
    console.log("▶ AI 에이전트 스케줄러 시작...\n");
    spawn("node", [join(__dirname, "run-agents.js")], { stdio: "inherit", cwd: ROOT });
  }
}
