// Matches docker-compose.yml's port mappings — same ports every command in
// this repo already assumes (docs/*.md, the Makefile, this whole session's
// manual verification).
export const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';
export const STAFF_WEB_URL = process.env.E2E_STAFF_WEB_URL ?? 'http://localhost:5173';
export const PATIENT_WEB_URL = process.env.E2E_PATIENT_WEB_URL ?? 'http://localhost:5174';
export const LANDING_URL = process.env.E2E_LANDING_URL ?? 'http://localhost:5175';
