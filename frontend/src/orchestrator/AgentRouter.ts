import { CustomGptService } from '../services/customgpt';
import type { AgentConfig, AgentMessage, UserMessage } from '../types/chat';

interface AgentResponse {
  agent: AgentConfig;
  message: AgentMessage;
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

export class AgentRouter {
  private readonly service: CustomGptService;
  private readonly agents: AgentConfig[];

  constructor(service = new CustomGptService(), agents: AgentConfig[] = DEFAULT_AGENTS) {
    this.service = service;
    this.agents = agents;
  }

  public async routePrompt(userMessage: UserMessage): Promise<AgentMessage[]> {
    const routingDecisions = this.determineAgents(userMessage.content);

    const responses = await Promise.allSettled(
      routingDecisions.map(async (agent) => {
        try {
          const reply = await this.service.sendMessage({
            projectId: agent.projectId,
            prompt: userMessage.content,
            conversationId: userMessage.id,
          });

          const message: AgentMessage = {
            id: reply.id,
            role: 'agent',
            agentId: agent.id,
            agentName: agent.name,
            projectId: agent.projectId,
            content: reply.message,
            timestamp: reply.createdAt,
          };

          return { agent, message } satisfies AgentResponse;
        } catch (error) {
          throw { agent, error };
        }
      })
    );

    const aggregated: AgentMessage[] = [];

    for (const response of responses) {
      if (response.status === 'fulfilled') {
        aggregated.push(response.value.message);
      } else {
        const { agent, error } = response.reason as { agent: AgentConfig; error: unknown };
        aggregated.push({
          id: crypto.randomUUID(),
          role: 'agent',
          agentId: agent.id,
          agentName: agent.name,
          projectId: agent.projectId,
          content: error instanceof Error ? error.message : 'Unknown error while contacting agent.',
          timestamp: new Date().toISOString(),
        });
      }
    }

    return aggregated;
  }

  private determineAgents(prompt: string): AgentConfig[] {
    const normalized = prompt.toLowerCase();

    const matchedAgents = this.agents.filter((agent) => {
      switch (agent.id) {
        case 'community-educator':
          return /general|information|info|overview|faq|question/.test(normalized);
        case 'compliance-expert':
          return /legal|law|compliance|regulation|regulatory|statute|contract/.test(normalized);
        case 'expectations-advisor':
          return /office|policy|policies|workplace|expectation|procedure|guideline/.test(normalized);
        case 'cartography-explorer':
          return /direction|drive|route|map|navigate|navigation|location|way/.test(normalized);
        default:
          return true;
      }
    });

    return matchedAgents.length > 0 ? matchedAgents : this.agents;
  }
}
