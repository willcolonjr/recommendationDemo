export interface Recommendation {
  id: string;
  name: string;
  location: string;
  description: string;
  score: number;
  weight: number;
  strategy: string;
  info: string;
}

export interface EmbeddingModelOption {
  id: string;
  name: string;
  provider: string;
  description: string;
}

export interface EmbeddingModelListResponse {
  default_model_id: string;
  models: EmbeddingModelOption[];
}
