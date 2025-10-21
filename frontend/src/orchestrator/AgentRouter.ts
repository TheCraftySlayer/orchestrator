import { CustomGptService } from '../services/customgpt';
import type { AgentConfig, AgentMessage, UserMessage } from '../types/chat';

interface RoutingDecision {
  agentId: string | null;
  summary: string;
}

const DEFAULT_AGENTS: AgentConfig[] = [
  {
    id: 'community-educator',
    name: 'Assessor Community Educator',
    description: 'Shares general information and broad guidance for open-ended questions.',
    projectId: 83668,
  },
  {
    id: 'compliance-expert',
    name: "Assessor's Compliance Expert",
    description: 'Provides legal insights, compliance clarifications, and regulatory guidance.',
    projectId: 49501,
  },
  {
    id: 'expectations-advisor',
    name: 'Advisor for Clear Expectations',
    description: 'Clarifies office policies, workplace expectations, and procedural details.',
    projectId: 37400,
  },
  {
    id: 'cartography-explorer',
    name: "Assessor's Cartography Explorer",
    description: 'Offers driving directions, navigation support, and location-specific assistance.',
    projectId: 9262,
  },
];

const ORCHESTRATOR_AGENT: AgentConfig = {
  id: 'orchestrator',
  name: 'Conversation Orchestrator',
  description: 'Coordinates routing across the specialized experts.',
  projectId: 83861,
};

export class AgentRouter {
  private readonly service: CustomGptService;
  private readonly agents: AgentConfig[];
  private readonly orchestrator: AgentConfig;
  private readonly sessions = new Map<number, string>();

  constructor(
    service = new CustomGptService(),
    agents: AgentConfig[] = DEFAULT_AGENTS,
    orchestrator: AgentConfig = ORCHESTRATOR_AGENT
  ) {
    this.service = service;
    this.agents = agents;
    this.orchestrator = orchestrator;
  }

  public async routePrompt(userMessage: UserMessage): Promise<AgentMessage[]> {
    const orchestratorDecision = await this.requestRoutingDecision(userMessage);
    const resolvedAgent = this.resolveAgent(orchestratorDecision, userMessage.content);

    const messages: AgentMessage[] = [];

    if (orchestratorDecision.summary.trim() !== '') {
      messages.push(this.buildAgentMessage(this.orchestrator, orchestratorDecision.summary));
    }

    const expertMessage = await this.requestExpertResponse(resolvedAgent, userMessage);
    messages.push(expertMessage);

    const orchestratedReply = await this.requestOrchestratorSynthesis(
      userMessage,
      resolvedAgent,
      expertMessage
    );

    messages.push(orchestratedReply);

    return messages;
  }

  private async requestRoutingDecision(userMessage: UserMessage): Promise<RoutingDecision> {
    const agentList = this.agents
      .map((agent) => `- ${agent.id}: ${agent.description}`)
      .join('\n');

    const prompt = [
      'You are the orchestrator responsible for routing user questions to a single expert agent.',
      'Each response must be valid JSON with the following shape: {"agentId":"<id>","summary":"<short summary>"}.',
      'If you are uncertain, choose the best matching agent. If no agent fits, return {"agentId":null,"summary":"<reason>"}.',
      'Respond with JSON only and avoid additional commentary.',
      'Available agents:',
      agentList,
      'User message:',
      userMessage.content,
    ].join('\n');

    try {
      const sessionId = await this.getSessionId(this.orchestrator.projectId);
      const reply = await this.service.sendMessage({
        projectId: this.orchestrator.projectId,
        prompt,
        sessionId,
      });

      const parsed = this.parseRoutingDecision(reply.message);
      const agentId = parsed.agentId ?? null;
      const agentName = agentId
        ? this.agents.find((candidate) => candidate.id === agentId)?.name
        : undefined;

      const summary = parsed.summary
        ? parsed.summary
        : agentName
          ? `Routing conversation to ${agentName}.`
          : 'Routing decision received from orchestrator.';

      return { agentId, summary };
    } catch (error) {
      const fallbackSummary =
        error instanceof Error
          ? `Routing failed (${error.message}). Falling back to heuristic selection.`
          : 'Routing failed due to an unknown error. Falling back to heuristic selection.';

      return { agentId: null, summary: fallbackSummary };
    }
  }

  private parseRoutingDecision(response: string): { agentId?: string | null; summary?: string } {
    const trimmed = response.trim();

    const jsonMatch = trimmed.match(/\{[\s\S]*\}/);
    const candidate = jsonMatch?.[0] ?? trimmed;

    try {
      const parsed = JSON.parse(candidate) as {
        agentId?: string | null;
        summary?: string;
        reason?: string;
      };

      return {
        agentId: parsed.agentId ?? null,
        summary: parsed.summary ?? parsed.reason,
      };
    } catch (error) {
      const normalized = trimmed.toLowerCase();
      const matchedAgent = this.agents.find((agent) =>
        normalized.includes(agent.id) || normalized.includes(agent.name.toLowerCase())
      );

      return {
        agentId: matchedAgent?.id ?? null,
        summary: trimmed,
      };
    }
  }

  private resolveAgent(decision: RoutingDecision, prompt: string): AgentConfig {
    if (decision.agentId) {
      const agent = this.agents.find((candidate) => candidate.id === decision.agentId);
      if (agent) {
        return agent;
      }
    }

    return this.fallbackAgent(prompt);
  }

  private fallbackAgent(prompt: string): AgentConfig {
    const normalized = prompt.toLowerCase();

    const matchers: Array<{ test: RegExp; agentId: AgentConfig['id'] }> = [
      { test: /legal|law|compliance|regulation|regulatory|statute|contract/, agentId: 'compliance-expert' },
      { test: /office|policy|policies|workplace|expectation|procedure|guideline/, agentId: 'expectations-advisor' },
      { test: /direction|drive|route|map|navigate|navigation|location|way/, agentId: 'cartography-explorer' },
      { test: /general|information|info|overview|faq|question/, agentId: 'community-educator' },
    ];

    for (const matcher of matchers) {
      if (matcher.test.test(normalized)) {
        const agent = this.agents.find((candidate) => candidate.id === matcher.agentId);
        if (agent) {
          return agent;
        }
      }
    }

    return this.agents[0];
  }

  private async requestExpertResponse(agent: AgentConfig, userMessage: UserMessage): Promise<AgentMessage> {
    try {
      const sessionId = await this.getSessionId(agent.projectId);
      const reply = await this.service.sendMessage({
        projectId: agent.projectId,
        prompt: userMessage.content,
        sessionId,
      });

      return this.buildAgentMessage(agent, reply.message, {
        id: reply.id,
        timestamp: reply.createdAt,
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unknown error while contacting agent.';

      return this.buildAgentMessage(agent, message);
    }
  }

  private async requestOrchestratorSynthesis(
    userMessage: UserMessage,
    agent: AgentConfig,
    expertMessage: AgentMessage
  ): Promise<AgentMessage> {
    const prompt = [
      'You previously routed a user request to a domain expert.',
      `User message: ${userMessage.content}`,
      `Expert agent (${agent.id}) response: ${expertMessage.content}`,
      'Provide a concise, user-ready answer that references the expert guidance when appropriate.',
    ].join('\n\n');

    try {
      const sessionId = await this.getSessionId(this.orchestrator.projectId);
      const reply = await this.service.sendMessage({
        projectId: this.orchestrator.projectId,
        prompt,
        sessionId,
      });

      return this.buildAgentMessage(this.orchestrator, reply.message, {
        id: reply.id,
        timestamp: reply.createdAt,
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? `Unable to synthesize final response: ${error.message}`
          : 'Unable to synthesize final response due to an unknown error.';

      return this.buildAgentMessage(this.orchestrator, message);
    }
  }

  private buildAgentMessage(
    agent: AgentConfig,
    content: string,
    metadata: { id?: string; timestamp?: string } = {}
  ): AgentMessage {
    return {
      id: metadata.id ?? crypto.randomUUID(),
      role: 'agent',
      agentId: agent.id,
      agentName: agent.name,
      projectId: agent.projectId,
      content,
      timestamp: metadata.timestamp ?? new Date().toISOString(),
    };
  }

  private async getSessionId(projectId: number): Promise<string> {
    const existing = this.sessions.get(projectId);
    if (existing) {
      return existing;
    }

    const conversation = await this.service.createConversation(projectId);
    this.sessions.set(projectId, conversation.sessionId);
    return conversation.sessionId;
  }
}
