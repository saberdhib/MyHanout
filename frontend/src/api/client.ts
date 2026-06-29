import axios from "axios";

// Base API : VITE_API_BASE_URL en prod, sinon proxy Vite "/api/v1".
const baseURL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const api = axios.create({ baseURL });

// --- Auth (JWT) : login auto avec les identifiants de démo en dev. ----------
let accessToken: string | null = localStorage.getItem("token");

const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL || "admin@myhanout.example";
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || "admin";

export async function login(email = DEMO_EMAIL, password = DEMO_PASSWORD): Promise<void> {
  const { data } = await axios.post(`${baseURL}/auth/login`, { email, password });
  accessToken = data.access_token;
  localStorage.setItem("token", accessToken!);
}

api.interceptors.request.use(async (config) => {
  if (!accessToken) await login();
  config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

// Sur 401, on retente une fois après re-login (token expiré).
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      accessToken = null;
      await login();
      error.config.headers.Authorization = `Bearer ${accessToken}`;
      return api.request(error.config);
    }
    return Promise.reject(error);
  },
);

export interface ListResponse<T> {
  items: T[];
  total: number;
}

export interface Stock {
  id: number;
  product_id: number;
  quantity: number;
  reorder_threshold: number;
  expiry_date: string | null;
  product_name: string | null;
  product_sku: string | null;
  low_stock: boolean;
}

export interface InvoiceLine {
  id: number;
  description: string | null;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface Invoice {
  id: number;
  number: string | null;
  supplier_id: number | null;
  issue_date: string | null;
  due_date: string | null;
  total_amount: number | null;
  currency: string;
  status: string;
  ocr_status: string;
  lines: InvoiceLine[];
}

export interface ForecastPoint {
  ds: string;
  yhat: number;
  yhat_lower: number | null;
  yhat_upper: number | null;
}

export interface Forecast {
  product_id: number | null;
  model: string;
  horizon_days: number;
  points: ForecastPoint[];
  explanation: string | null;
}

export const getStocks = () =>
  api.get<ListResponse<Stock>>("/stocks").then((r) => r.data);

export const getStockAlerts = () =>
  api.get<ListResponse<Stock>>("/stocks/alerts").then((r) => r.data);

export const getInvoices = () =>
  api.get<ListResponse<Invoice>>("/invoices").then((r) => r.data);

export const getForecast = (productId: number, horizon = 14) =>
  api
    .get<Forecast>(`/forecasts/${productId}`, { params: { horizon_days: horizon } })
    .then((r) => r.data);

// --- Onboarding self-service -----------------------------------------------

export interface SignupPayload {
  email: string;
  password: string;
  organization_name: string;
  business_type?: string;
}

export async function signup(payload: SignupPayload): Promise<void> {
  const { data } = await axios.post(`${baseURL}/onboarding/signup`, payload);
  accessToken = data.access_token;
  localStorage.setItem("token", accessToken!);
}

export const addSupplier = (name: string) =>
  api.post("/onboarding/suppliers", { name }).then((r) => r.data);

export const addProduct = (p: { sku: string; name: string; unit?: string }) =>
  api.post("/onboarding/products", p).then((r) => r.data);

export const inviteMember = (email: string, role: string) =>
  api.post("/onboarding/invitations", { email, role }).then((r) => r.data);

// --- Phase 2 : suggestions, saisie fin de journée, MLOps -------------------

export interface SuggestionLine {
  product_id: number;
  product_name: string | null;
  unit: string;
  suggested_quantity: number;
  predicted_demand: number;
  safety_buffer: number;
  current_stock: number;
  lead_time_days: number;
  confidence: number;
  explanation: string;
}

export interface Suggestion {
  horizon_days: number;
  generated_for: string;
  model: string;
  lines: SuggestionLine[];
}

export interface OrderConfirmed {
  id: number;
  status: string;
  action_mode: string;
  total_amount: number;
  supplier_message: string | null;
  lines: { product_id: number; quantity: number; unit_price: number }[];
}

export interface MlopsMetric {
  product_id: number;
  model: string;
  n: number;
  mae: number | null;
  mape: number | null;
}

export const getSuggestion = (horizon = "demain") =>
  api.post<Suggestion>("/orders/suggest", { horizon }).then((r) => r.data);

export const confirmOrder = (
  lines: { product_id: number; quantity: number }[],
  action_mode = "record_only",
) =>
  api
    .post<OrderConfirmed>("/orders/confirm", { lines, action_mode })
    .then((r) => r.data);

export const createDailyEntry = (entry: {
  product_id: number;
  entry_date: string;
  quantity_ordered: number;
  stock_remaining: number;
}) => api.post("/daily-entries", { ...entry, source: "dashboard" }).then((r) => r.data);

export const getMlopsMetrics = () =>
  api.get<{ metrics: MlopsMetric[] }>("/mlops/metrics").then((r) => r.data.metrics);
