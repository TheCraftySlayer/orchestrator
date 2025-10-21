import { useState } from 'react';
import ChatWindow from './components/ChatWindow';
import { AgentRouter } from './orchestrator/AgentRouter';
import type { AgentMessage, UserMessage } from './types/chat';

const agentRouter = new AgentRouter();

function App() {
  const [messages, setMessages] = useState<Array<UserMessage | AgentMessage>>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    const userMessage: UserMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const agentMessages = await agentRouter.routePrompt(userMessage);
      setMessages((prev) => [...prev, ...agentMessages]);
    } catch (error) {
      const fallback: AgentMessage = {
        id: crypto.randomUUID(),
        role: 'agent',
        agentId: 'system',
        agentName: 'System',
        projectId: -1,
        content:
          error instanceof Error
            ? `An error occurred: ${error.message}`
            : 'An unknown error occurred while contacting the agents.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, fallback]);
    } finally {
      setIsLoading(false);
    }
  };

  return <ChatWindow messages={messages} onSendMessage={handleSendMessage} isLoading={isLoading} />;
}

export default App;
