import { apiRequest } from '@/services/apiClient';

import type {
  Business,
  BusinessLocation,
  BusinessMember,
  GroupMember,
  OperatingLocation,
  OperatorGroup,
  OperatorProfile,
  Paged,
} from './types';

export const orgApi = {
  // ── Businesses ────────────────────────────────────────────────────
  listBusinesses: () => apiRequest<Paged<Business>>('/businesses'),
  createBusiness: (body: Partial<Business>) =>
    apiRequest<Business>('/businesses', { method: 'POST', body }),
  getBusiness: (id: string) => apiRequest<Business>(`/businesses/${id}`),
  updateBusiness: (id: string, body: Partial<Business>) =>
    apiRequest<Business>(`/businesses/${id}`, { method: 'PATCH', body }),
  listMembers: (id: string) =>
    apiRequest<{ data: BusinessMember[] }>(`/businesses/${id}/members`),
  addMember: (id: string, body: { phone: string; role: string }) =>
    apiRequest<BusinessMember>(`/businesses/${id}/members`, { method: 'POST', body }),
  updateMember: (id: string, memberId: string, body: { role?: string; status?: string }) =>
    apiRequest<BusinessMember>(`/businesses/${id}/members/${memberId}`, { method: 'PATCH', body }),
  removeMember: (id: string, memberId: string) =>
    apiRequest<null>(`/businesses/${id}/members/${memberId}`, { method: 'DELETE' }),
  listLocations: (id: string) =>
    apiRequest<{ data: BusinessLocation[] }>(`/businesses/${id}/locations`),
  addLocation: (id: string, body: Partial<BusinessLocation> & { zone_code?: string }) =>
    apiRequest<BusinessLocation>(`/businesses/${id}/locations`, { method: 'POST', body }),
  removeLocation: (id: string, locationId: string) =>
    apiRequest<null>(`/businesses/${id}/locations/${locationId}`, { method: 'DELETE' }),

  // ── Operator profile ─────────────────────────────────────────────
  getMyOperator: () => apiRequest<OperatorProfile>('/operators/me'),
  createOperator: (body: { full_name: string; display_name?: string; phones?: string[] }) =>
    apiRequest<OperatorProfile>('/operators', { method: 'POST', body }),
  updateOperator: (id: string, body: Partial<OperatorProfile>) =>
    apiRequest<OperatorProfile>(`/operators/${id}`, { method: 'PATCH', body }),

  // ── Operating locations ─────────────────────────────────────────
  listOperatingLocations: () => apiRequest<Paged<OperatingLocation>>('/operating-locations'),
  createOperatingLocation: (body: {
    name: string;
    type: string;
    landmark?: string;
    zone_code?: string;
  }) => apiRequest<OperatingLocation>('/operating-locations', { method: 'POST', body }),

  // ── Groups ──────────────────────────────────────────────────────
  listGroups: () => apiRequest<Paged<OperatorGroup>>('/groups'),
  createGroup: (body: { name: string; type: string; assignment_mode?: string }) =>
    apiRequest<OperatorGroup>('/groups', { method: 'POST', body }),
  getGroup: (id: string) => apiRequest<OperatorGroup>(`/groups/${id}`),
  updateGroup: (id: string, body: Partial<OperatorGroup>) =>
    apiRequest<OperatorGroup>(`/groups/${id}`, { method: 'PATCH', body }),
  listGroupMembers: (id: string) =>
    apiRequest<{ data: GroupMember[] }>(`/groups/${id}/members`),
  addGroupMember: (id: string, body: { operator_id: string; role: string }) =>
    apiRequest<GroupMember>(`/groups/${id}/members`, { method: 'POST', body }),
  removeGroupMember: (id: string, memberId: string) =>
    apiRequest<null>(`/groups/${id}/members/${memberId}`, { method: 'DELETE' }),
};
