// Backend address. Set VITE_API_BASE in .env (e.g. https://my-api.onrender.com) for a deployed backend.
// Empty string = same origin, which works with the Vite dev proxy in vite.config.ts.
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? "";
