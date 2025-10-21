export interface BaseMessage {
  id: string;
  content: string;
  timestamp: string;
}

export interface UserMessage extends BaseMessage {
  role: 'user';
}

export interface AgentMessage extends BaseMessage {
  role: 'agent';
  agentId: string;
  agentName: string;
  projectId: number;
}

export interface AgentConfig {
  id: string;
  name: string;
  description: string;
  projectId: number;
}
