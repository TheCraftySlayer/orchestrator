import { describe, expect, it } from 'vitest';

import { AgentRouter } from './AgentRouter';
import type { AgentMessage, UserMessage } from '../types/chat';
import type { CustomGptResponse, CustomGptService } from '../services/customgpt';

interface ConversationRecord {
  id: string;
  sessionId: string;
}

class StubCustomGptService {
  private readonly responses = new Map<number, CustomGptResponse[]>();
  private readonly conversations = new Map<number, ConversationRecord>();

  constructor(responses: Record<number, CustomGptResponse[]>) {
    for (const [projectId, entries] of Object.entries(responses)) {
      this.responses.set(Number(projectId), [...entries]);
    }
  }

  async createConversation(projectId: number): Promise<ConversationRecord> {
    const existing = this.conversations.get(projectId);
    if (existing) {
      return existing;
    }

    const record = {
      id: `conversation-${projectId}`,
      sessionId: `session-${projectId}`,
    } satisfies ConversationRecord;

    this.conversations.set(projectId, record);
    return record;
  }

  async sendMessage(
    params: { projectId: number } & Record<string, unknown>
  ): Promise<CustomGptResponse> {
    const queue = this.responses.get(params.projectId);
    if (!queue || queue.length === 0) {
      throw new Error(`No stub response for project ${params.projectId}`);
    }

    return queue.shift()!;
  }
}

describe('AgentRouter', () => {
  const orchestratorProjectId = 83861;
  const communityProjectId = 83668;
  const cartographyProjectId = 9262;

  const buildUserMessage = (content: string): UserMessage => ({
    id: 'user-1',
    role: 'user',
    content,
    timestamp: new Date().toISOString(),
  });

  const mapMessages = (messages: AgentMessage[]): string[] => messages.map((message) => message.agentId);

  it('falls back to the community educator when cartography is suggested without parcel context', async () => {
    const stub = new StubCustomGptService({
      [orchestratorProjectId]: [
        {
          id: 'route-1',
          message: '{"agentId":"cartography-explorer","summary":"General greeting"}',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
        {
          id: 'synth-1',
          message: 'Synthesis reply',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
      ],
      [communityProjectId]: [
        {
          id: 'community-1',
          message: 'Community educator response',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83668',
        },
      ],
    });

    const router = new AgentRouter(stub as unknown as CustomGptService);
    const messages = await router.routePrompt(buildUserMessage('hello there'));

    expect(mapMessages(messages)).toContain('community-educator');
    expect(messages[1]?.agentId).toBe('community-educator');
  });

  it('prefers the community educator for greetings that include incidental mentions of "way"', async () => {
    const stub = new StubCustomGptService({
      [orchestratorProjectId]: [
        {
          id: 'route-1b',
          message: '{"agentId":"cartography-explorer","summary":"General greeting"}',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
        {
          id: 'synth-1b',
          message: 'Synthesis reply',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
      ],
      [communityProjectId]: [
        {
          id: 'community-1b',
          message: 'Community educator response',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83668',
        },
      ],
    });

    const router = new AgentRouter(stub as unknown as CustomGptService);
    const messages = await router.routePrompt(buildUserMessage('hello, by the way...'));

    expect(mapMessages(messages)).toContain('community-educator');
    expect(messages[1]?.agentId).toBe('community-educator');
  });

  it.each([
    'Need directions for UPC R12345678A please.',
    'Need directions for UPC R12-345-678 please.',
    'Need directions for UPC R12 345 678 please.',
  ])('routes to the cartography explorer when a parcel identifier is present (%s)', async (content) => {
    const stub = new StubCustomGptService({
      [orchestratorProjectId]: [
        {
          id: 'route-2',
          message: '{"agentId":"cartography-explorer","summary":"Routing to map expert"}',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
        {
          id: 'synth-2',
          message: 'Synthesis reply',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
      ],
      [cartographyProjectId]: [
        {
          id: 'cartography-1',
          message: 'Parcel lookup results',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-9262',
        },
      ],
    });

    const router = new AgentRouter(stub as unknown as CustomGptService);
    const messages = await router.routePrompt(buildUserMessage(content));

    expect(mapMessages(messages)).toContain('cartography-explorer');
    expect(messages[1]?.agentId).toBe('cartography-explorer');
  });

  it('ignores orchestrator project identifiers returned as agent ids', async () => {
    const stub = new StubCustomGptService({
      [orchestratorProjectId]: [
        {
          id: 'route-3',
          message: '{"agentId":"83861","summary":"General greeting"}',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
        {
          id: 'synth-3',
          message: 'Synthesis reply',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
      ],
      [communityProjectId]: [
        {
          id: 'community-2',
          message: 'Community educator response',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83668',
        },
      ],
    });

    const router = new AgentRouter(stub as unknown as CustomGptService);
    const messages = await router.routePrompt(buildUserMessage('hello'));

    expect(mapMessages(messages)).toContain('community-educator');
    expect(messages[1]?.agentId).toBe('community-educator');
  });

  it('routes to the cartography explorer when directional language is present without parcel context', async () => {
    const stub = new StubCustomGptService({
      [orchestratorProjectId]: [
        {
          id: 'route-4',
          message: '{"agentId":null,"summary":"No clear match"}',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
        {
          id: 'synth-4',
          message: 'Synthesis reply',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-83861',
        },
      ],
      [cartographyProjectId]: [
        {
          id: 'cartography-2',
          message: 'Directional response',
          createdAt: new Date().toISOString(),
          conversationId: 'conv-9262',
        },
      ],
    });

    const router = new AgentRouter(stub as unknown as CustomGptService);
    const messages = await router.routePrompt(
      buildUserMessage('Which way should I go to reach the assessor office?')
    );

    expect(mapMessages(messages)).toContain('cartography-explorer');
    expect(messages[1]?.agentId).toBe('cartography-explorer');
  });
});
