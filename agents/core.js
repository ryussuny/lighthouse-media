import Anthropic from "@anthropic-ai/sdk";
import { config } from "dotenv";
import { EventEmitter } from "events";

config();

const client = new Anthropic();

export class Agent extends EventEmitter {
  constructor({ name, role, department, systemPrompt, schedule }) {
    super();
    this.name = name;
    this.role = role;
    this.department = department;
    this.systemPrompt = systemPrompt;
    this.schedule = schedule; // cron expression
    this.status = "idle"; // idle, working, done, error
    this.lastRun = null;
    this.lastOutput = null;
    this.metrics = { runs: 0, successes: 0, failures: 0 };
  }

  async execute(input = "") {
    this.status = "working";
    this.emit("status", { agent: this.name, status: "working" });

    try {
      const message = await client.messages.create({
        model: "claude-sonnet-4-20250514",
        max_tokens: 4096,
        system: this.systemPrompt,
        messages: [{ role: "user", content: input || "오늘의 업무를 수행하세요." }],
      });

      const output = message.content[0].text;
      this.lastOutput = output;
      this.lastRun = new Date().toISOString();
      this.status = "done";
      this.metrics.runs++;
      this.metrics.successes++;
      this.emit("status", { agent: this.name, status: "done", output });
      return output;
    } catch (error) {
      this.status = "error";
      this.metrics.runs++;
      this.metrics.failures++;
      this.emit("status", { agent: this.name, status: "error", error: error.message });
      throw error;
    }
  }

  getState() {
    return {
      name: this.name,
      role: this.role,
      department: this.department,
      status: this.status,
      lastRun: this.lastRun,
      metrics: this.metrics,
    };
  }
}

export class AgentOrchestrator extends EventEmitter {
  constructor() {
    super();
    this.agents = new Map();
    this.pipeline = [];
    this.dailyLog = [];
  }

  register(agent) {
    this.agents.set(agent.name, agent);
    agent.on("status", (data) => {
      this.emit("agent-update", data);
      this.dailyLog.push({ ...data, timestamp: new Date().toISOString() });
    });
  }

  async runPipeline(pipelineName, steps) {
    this.emit("pipeline-start", { name: pipelineName, steps: steps.length });
    let context = {};

    for (const step of steps) {
      const agent = this.agents.get(step.agent);
      if (!agent) {
        console.error(`Agent not found: ${step.agent}`);
        continue;
      }

      const input = step.inputBuilder ? step.inputBuilder(context) : step.input;
      try {
        const output = await agent.execute(input);
        context[step.agent] = output;
        this.emit("step-complete", { pipeline: pipelineName, agent: step.agent });
      } catch (err) {
        this.emit("step-error", { pipeline: pipelineName, agent: step.agent, error: err.message });
        if (!step.optional) break;
      }
    }

    this.emit("pipeline-complete", { name: pipelineName, context });
    return context;
  }

  getStatus() {
    const statuses = {};
    for (const [name, agent] of this.agents) {
      statuses[name] = agent.getState();
    }
    return statuses;
  }

  getDailyLog() {
    return this.dailyLog;
  }
}
