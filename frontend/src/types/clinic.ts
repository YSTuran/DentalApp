export interface Clinic {
  id: string;
  code: string;
  name: string;
  address: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicListResponse {
  items: Clinic[];
  total: number;
  limit: number;
  offset: number;
}

export interface ClinicFormInput {
  code: string;
  name: string;
  address: string;
  phone: string;
  reason: string;
}
