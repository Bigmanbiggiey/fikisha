import { apiRequest } from '@/services/apiClient';

export interface HealthResponse {
  status: string;
}

export interface ReferenceResponse {
  locales: { supported: string[]; default: string; operator_default: string };
  config_version: number;
  vehicle_types: string[];
}

export const diagnosticsApi = {
  health(): Promise<HealthResponse> {
    return apiRequest<HealthResponse>('/health/', { auth: false });
  },
  reference(): Promise<ReferenceResponse> {
    return apiRequest<ReferenceResponse>('/reference');
  },
};
