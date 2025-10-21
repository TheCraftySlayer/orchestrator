import axios from 'axios';

interface SendMessageParams {
  projectId: number;
  prompt: string;
  conversationId?: string;
}

interface CustomGptResponse {
  id: string;
  message: string;
  createdAt: string;
}

const API_BASE_URL = 'https://app.customgpt.ai/api/v1';

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
      config.headers['Content-Type'] = 'application/json';
      return config;
    });
  }

  public async sendMessage(params: SendMessageParams): Promise<CustomGptResponse> {
    const response = await this.client.post(`/projects/${params.projectId}/chat`, {
      messages: [
        {
          role: 'user',
          content: params.prompt,
        },
      ],
      conversation_id: params.conversationId,
    });

    const data = response.data?.data?.[0];

    if (!data) {
      throw new Error('Unexpected response from CustomGPT.');
    }

    return {
      id: data.id ?? crypto.randomUUID(),
      message: data.message ?? '',
      createdAt: data.created_at ?? new Date().toISOString(),
    };
  }
}
