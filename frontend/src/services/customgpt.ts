import axios from 'axios';

const API_BASE_URL = 'https://app.customgpt.ai/api/v1';

interface CreateConversationResponse {
  id: string;
  sessionId: string;
  name: string | null;
}

interface SendMessageParams {
  projectId: number;
  prompt: string;
  conversationId: string;
}

export interface CustomGptResponse {
  id: string;
  message: string;
  createdAt: string;
  conversationId: string;
}

export class CustomGptService {
  private readonly apiKey: string;
  private readonly client = axios.create({
    baseURL: API_BASE_URL,
  });

  constructor(apiKey: string = __CUSTOM_GPT_API_KEY__) {
    if (!apiKey) {
      throw new Error('CustomGPT API key is missing. Please set VITE_CUSTOMGPT_API_KEY.');
    }

    this.apiKey = apiKey;

    this.client.interceptors.request.use((config) => {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${this.apiKey}`;

      const isFormData = typeof FormData !== 'undefined' && config.data instanceof FormData;

      if (isFormData) {
        delete config.headers['Content-Type'];
      } else if (config.headers['Content-Type'] === undefined) {
        config.headers['Content-Type'] = 'application/json';
      }

      return config;
    });
  }

  public async createConversation(
    projectId: number,
    name?: string
  ): Promise<CreateConversationResponse> {
    const payload = name ? { name } : {};
    const response = await this.client.post(`/projects/${projectId}/conversations`, payload);
    const data = response.data?.data;

    if (!data || typeof data.session_id !== 'string') {
      throw new Error('Unexpected response while creating a CustomGPT conversation.');
    }

    return {
      id: data.id !== undefined ? String(data.id) : crypto.randomUUID(),
      sessionId: data.session_id,
      name: data.name ?? null,
    };
  }

  public async sendMessage(params: SendMessageParams): Promise<CustomGptResponse> {
    const formData = new FormData();
    formData.append('prompt', params.prompt);

    const response = await this.client.post(
      `/projects/${params.projectId}/conversations/${params.conversationId}/messages`,
      formData
    );

    const data = response.data?.data;

    if (!data || typeof data.openai_response !== 'string') {
      throw new Error('Unexpected response from CustomGPT.');
    }

    return {
      id: data.id !== undefined ? String(data.id) : crypto.randomUUID(),
      message: data.openai_response,
      createdAt: data.created_at ?? new Date().toISOString(),
      conversationId: data.conversation_id !== undefined
        ? String(data.conversation_id)
        : params.conversationId,
    };
  }
}
