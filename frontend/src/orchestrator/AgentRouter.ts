import { CustomGptService } from '../services/customgpt';
import type { AgentConfig, AgentMessage, UserMessage } from '../types/chat';

interface AgentResponse {
  agent: AgentConfig;
  message: AgentMessage;
}

const DEFAULT_AGENTS: AgentConfig[] = [
  {
    id: 'support',
    name: 'Customer Support',
    description: 'Handles customer support inquiries and troubleshooting.',
    projectId: 83668,
  },
  {
    id: 'sales',
    name: 'Sales Advisor',
    description: 'Answers questions about pricing, plans, and purchasing.',
    projectId: 49501,
  },
  {
    id: 'documentation',
    name: 'Documentation Guide',
    description: 'Provides detailed documentation references and explanations.',
    projectId: 37400,
  },
  {
    id: 'developer',
    name: 'Developer Expert',
    description: 'Assists with integration and development related questions.',
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
        case 'support':
          return /support|help|issue|problem|bug|error/.test(normalized);
        case 'sales':
          return /price|plan|buy|purchase|cost/.test(normalized);
        case 'documentation':
          return /documentation|docs|guide|manual|instructions/.test(normalized);
        case 'developer':
          return /api|integration|developer|code|sdk/.test(normalized);
        default:
          return true;
      }
    });

    return matchedAgents.length > 0 ? matchedAgents : this.agents;
  }
}
