export type Organization = {
  id: number;
  name: string;
  code: string;
  email?: string;
  phone?: string;
  plan: string;
  plan_status: string;
  trial_ends?: string | null;
  subscription_ends?: string | null;
  grace_days?: number;
  package_name?: string;
  subscription_open?: boolean;
  subscription_in_grace?: boolean;
  days_until_lock?: number | null;
  currency?: string;
  brand_name?: string;
  brand_tagline?: string;
  brand_primary_color?: string;
  brand_secondary_color?: string;
  brand_logo_url?: string | null;
  brand_logo_dark_url?: string | null;
  brand_favicon_url?: string | null;
};

export type UserProfile = {
  role: string;
  phone?: string;
  designation?: string;
  organization?: Organization | null;
  is_active_member?: boolean;
  primary_role?: number | null;
  primary_role_name?: string;
};

export type PermissionsMap = Record<string, string[]>;

export type User = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active?: boolean;
  is_superuser?: boolean;
  profile?: UserProfile;
  permissions?: PermissionsMap;
  role_ids?: number[];
  is_owner?: boolean;
};

export type AuthState = {
  user: User | null;
  organization: Organization | null;
  subscriptionOpen: boolean;
  permissions: PermissionsMap;
  access: string | null;
  refresh: string | null;
  loading: boolean;
  error: string | null;
  isPlatformUser: boolean;
  platformRole: string | null;
  platformCapabilities: string[];
};
