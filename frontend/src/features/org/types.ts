export type Paged<T> = { data: T[]; page: { next_cursor: string | null; prev_cursor: string | null } };

export interface Business {
  id: string;
  trading_name: string;
  category: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  standing: string;
  verification_status: string;
  my_role: string | null;
  created_at: string;
  updated_at: string;
}

export interface BusinessMember {
  id: string;
  user_id: string;
  user_phone: string;
  user_display_name: string;
  role: string;
  status: string;
  created_at: string;
}

export interface BusinessLocation {
  id: string;
  label: string;
  type: string;
  address_text: string;
  lat: string | null;
  lng: string | null;
  zone_code: string | null;
  contact_name: string;
  contact_phone: string;
  hours: Record<string, unknown>;
  access_notes: string;
}

export interface OperatorProfile {
  id: string;
  user_id: string;
  user_phone: string;
  full_name: string;
  display_name: string;
  phones: string[];
  status: string;
}

export interface OperatingLocation {
  id: string;
  name: string;
  type: string;
  lat: string | null;
  lng: string | null;
  zone_code: string | null;
  landmark: string;
  created_by_id: string | null;
}

export interface OperatorGroup {
  id: string;
  name: string;
  type: string;
  standing: string;
  assignment_mode: string;
  verification_status: string;
  my_role: string | null;
}

export interface GroupMember {
  id: string;
  operator_id: string;
  operator_name: string;
  role: string;
  status: string;
  since: string;
}

export const BUSINESS_ROLES = ['OWNER', 'DISPATCHER', 'VIEWER'] as const;
export const LOCATION_TYPES = ['MAIN', 'BRANCH', 'WAREHOUSE', 'STORE', 'PICKUP_POINT'] as const;
export const GROUP_TYPES = ['YARD_OWNER', 'FLEET', 'SACCO', 'PARTNERSHIP'] as const;
export const GROUP_ROLES = ['OWNER', 'MANAGER', 'DRIVER'] as const;
export const BASE_TYPES = ['STAGE', 'BASE', 'YARD', 'WAITING_AREA'] as const;
