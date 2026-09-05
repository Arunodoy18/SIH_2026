/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL of the deployed backend API, no trailing slash (e.g. https://nirnay-backend.onrender.com).
   *  Unset in local dev — vite.config.ts proxies /api to http://127.0.0.1:8000 instead. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
