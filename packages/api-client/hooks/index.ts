export * from './api-base';
export type { components, operations, paths } from '../generated/schema.d.ts';

// Convenience alias for the common case — most call sites want one
// specific response/request shape, not the raw `components["schemas"]`
// indexing every time. Usage: `import type { Schemas } from
// '@medical-platform/api-client'` then `Schemas['PatientRead']`.
import type { components as _components } from '../generated/schema.d.ts';
export type Schemas = _components['schemas'];
