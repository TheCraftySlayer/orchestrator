import axios from 'axios';

const API_BASE_URL = 'https://app.customgpt.ai/api/v1';

interface CreateConversationResponse {
  id: string;
  sessionId: string;
  name: string | null;
}

type ResponseSourceOption = 'default' | 'own_content' | 'openai_content';

interface SendMessageParams {
  projectId: number;
  sessionId: string;
  prompt: string;
  customPersona?: string;
  chatbotModel?: string;
  responseSource?: ResponseSourceOption;
  customContext?: string;
  stream?: boolean;
  lang?: string;
  externalId?: string;
  cacheControl?: 'no-cache';
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
      config.headers['X-API-Key'] = this.apiKey;
      config.headers.Accept = config.headers.Accept ?? 'application/json';

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
    const resolvedName = name?.trim();
    const conversationName =
      resolvedName && resolvedName.length > 0
        ? resolvedName
        : `Session started ${new Date().toISOString()}`;

    const payload = { name: conversationName };
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
    const payload: Record<string, unknown> = { prompt: params.prompt };

    if (params.customPersona) {
      payload.custom_persona = params.customPersona;
    }
    if (params.chatbotModel) {
      payload.chatbot_model = params.chatbotModel;
    }
    if (params.responseSource) {
      payload.response_source = params.responseSource;
    }
    if (params.customContext) {
      payload.custom_context = params.customContext;
    }

    const query: Record<string, unknown> = {};
    if (params.stream !== undefined) {
      query.stream = params.stream;
    }
    if (params.lang) {
      query.lang = params.lang;
    }
    if (params.externalId) {
      query.external_id = params.externalId;
    }

    const requestConfig: {
      params?: Record<string, unknown>;
      headers?: Record<string, string>;
    } = {};

    if (Object.keys(query).length > 0) {
      requestConfig.params = query;
    }

    if (params.cacheControl) {
      requestConfig.headers = { 'Cache-Control': params.cacheControl };
    }

    const response = await this.client.post(
      `/projects/${params.projectId}/conversations/${params.sessionId}/messages`,
      payload,
      requestConfig
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
        : params.sessionId,
    };
  }
}
