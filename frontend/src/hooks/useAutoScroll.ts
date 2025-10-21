import { useEffect, useRef } from 'react';
import type { AgentMessage, UserMessage } from '../types/chat';

type Message = UserMessage | AgentMessage;

export default function useAutoScroll(messages: Message[]) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  return { containerRef };
}
