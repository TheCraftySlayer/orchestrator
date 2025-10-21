import { FormEvent, useMemo, useRef } from 'react';
import clsx from 'clsx';
import type { AgentMessage, UserMessage } from '../types/chat';
import useAutoScroll from '../hooks/useAutoScroll';

interface ChatWindowProps {
  messages: Array<UserMessage | AgentMessage>;
  onSendMessage: (content: string) => Promise<void>;
  isLoading: boolean;
}

function MessageBubble({ message }: { message: UserMessage | AgentMessage }) {
  const isUser = message.role === 'user';
  const agentLabel = 'agentId' in message ? message.agentName : '';
  const label = isUser ? 'You' : `Agent ${agentLabel}`;

  return (
    <div
      className={clsx('message', {
        'message-user': isUser,
        'message-agent': !isUser,
      })}
    >
      <div className="message-label">{label}</div>
      <div className="message-content">{message.content}</div>
      <div className="message-timestamp">{new Date(message.timestamp).toLocaleTimeString()}</div>
    </div>
  );
}

function ChatWindow({ messages, onSendMessage, isLoading }: ChatWindowProps) {
  const formRef = useRef<HTMLFormElement | null>(null);
  const { containerRef } = useAutoScroll(messages);

  const orderedMessages = useMemo(() => messages, [messages]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const content = (formData.get('message') as string)?.trim();

    if (!content) {
      return;
    }

    await onSendMessage(content);
    formRef.current?.reset();
  };

  return (
    <div className="chat-window">
      <header className="chat-header">
        <h1>Multi-Agent Orchestrator</h1>
        <p>Send a message and receive responses from specialized agents.</p>
      </header>

      <section className="chat-messages" ref={containerRef}>
        {orderedMessages.length === 0 ? (
          <div className="chat-empty">Start the conversation by typing your first message.</div>
        ) : (
          orderedMessages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
        {isLoading ? <div className="chat-loading">Collecting agent responses…</div> : null}
      </section>

      <form className="chat-input" onSubmit={handleSubmit} ref={formRef}>
        <textarea
          name="message"
          placeholder="Type your message"
          rows={3}
          disabled={isLoading}
          aria-label="Chat message"
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Waiting…' : 'Send'}
        </button>
      </form>
    </div>
  );
}

export default ChatWindow;
