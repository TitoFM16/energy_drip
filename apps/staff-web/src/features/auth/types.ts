export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  roles: string[];
}
