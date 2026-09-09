import { apiRequest } from '@/services/apiClient';
import type { Paged } from '@/features/org/types';

export interface Vehicle {
  id: string;
  owner_operator_id: string | null;
  owner_group_id: string | null;
  controller_kind: 'OPERATOR' | 'GROUP';
  vehicle_class: string;
  vehicle_class_heavy: boolean;
  sub_descriptor: string;
  registration: string;
  make: string;
  model: string;
  year: number | null;
  capacity_value: string;
  capacity_unit: string;
  ownership: string;
  status: string;
  created_at: string;
}

export const VEHICLE_CLASSES = [
  'MOTORCYCLE',
  'PICKUP',
  'CANTER',
  'TIPPER',
  'LORRY',
  'SEMI_TRUCK',
  'TRAILER',
  'OTHER',
] as const;
export const CAPACITY_UNITS = ['KG', 'TONNES'] as const;
export const OPERATOR_STATUSES = ['ACTIVE', 'INACTIVE', 'UNDER_REPAIR'] as const;

export const vehiclesApi = {
  list: () => apiRequest<Paged<Vehicle>>('/vehicles'),
  get: (id: string) => apiRequest<Vehicle>(`/vehicles/${id}`),
  create: (body: Record<string, unknown>) =>
    apiRequest<Vehicle>('/vehicles', { method: 'POST', body }),
  update: (id: string, body: Record<string, unknown>) =>
    apiRequest<Vehicle>(`/vehicles/${id}`, { method: 'PATCH', body }),
  setStatus: (id: string, status: string, reason = '') =>
    apiRequest<Vehicle>(`/vehicles/${id}/status`, { method: 'POST', body: { status, reason } }),
  deactivate: (id: string, reason = '') =>
    apiRequest<null>(`/vehicles/${id}`, { method: 'DELETE', body: { reason } }),
};
