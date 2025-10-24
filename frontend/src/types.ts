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
