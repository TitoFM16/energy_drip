import type { Schemas } from '@medical-platform/api-client';

export type TokenResponse = Schemas['TokenResponse'];

// UserRead's shape is exactly what GET /auth/me returns and this type
// consumes — no separate CurrentUser response model exists on the backend.
export type CurrentUser = Schemas['UserRead'];
