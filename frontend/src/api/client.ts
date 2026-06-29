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
  paid: boolean;
  lines: InvoiceLine[];
}

export const uploadInvoice = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post<Invoice>("/invoices/upload", form).then((r) => r.data);
};

export interface EmailImportResult {
  provider: string;
  imported: number;
  items: { invoice_id: number; filename: string; sender: string; reasons: string[] }[];
}

export const importInvoicesFromEmail = (limit = 10) =>
  api
    .post<EmailImportResult>("/invoices/import/email", null, { params: { limit } })
    .then((r) => r.data);

export const patchInvoice = (
  id: number,
  fields: Partial<{
    number: string;
    issue_date: string;
    due_date: string;
    total_amount: number;
    supplier_id: number;
    paid: boolean;
  }>,
) => api.patch<Invoice>(`/invoices/${id}`, fields).then((r) => r.data);

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

// --- Demo pack : chat, signaux, promos ------------------------------------

export interface ChatReply {
  reply: string;
  agent: string;
  explanation: string | null;
}

export interface Signals {
  weather: { day: string; temp_c: number; condition: string; demand_hint: string };
  trends: { topic: string; score: number; hint: string }[];
}

export interface Promo {
  id: number;
  product_id: number | null;
  title: string;
  message: string;
  discount_pct: number;
  reason: string | null;
  status: string;
  channels: string | null;
  audience_count: number;
  visual_url: string | null;
  visual_prompt: string | null;
}

export const sendChat = (message: string) =>
  api.post<ChatReply>("/chat", { message }).then((r) => r.data);

export const getSignals = () => api.get<Signals>("/signals").then((r) => r.data);

export const scanPromos = (withinDays = 3) =>
  api
    .post<ListResponse<Promo>>("/promos/scan", null, { params: { within_days: withinDays } })
    .then((r) => r.data);

export const getPromos = () =>
  api.get<ListResponse<Promo>>("/promos").then((r) => r.data);

export const publishPromo = (id: number, channels = ["social", "customers"]) =>
  api.post<Promo>(`/promos/${id}/publish`, { channels }).then((r) => r.data);

export const generatePromoVisual = (id: number) =>
  api.post<Promo>(`/promos/${id}/visual`).then((r) => r.data);

// --- Intégrations : import JSON + sync entrepôt de données -----------------

export interface ImportResult {
  suppliers_upserted: number;
  products_upserted: number;
  stocks_upserted: number;
  sales_inserted: number;
}

export interface DwhSyncResult {
  target: string;
  rows: number;
  detail: string | null;
}

export const importJson = (payload: unknown) =>
  api.post<ImportResult>("/import/json", payload).then((r) => r.data);

export const syncDwh = () =>
  api.post<DwhSyncResult>("/import/dwh/sync").then((r) => r.data);

// --- Couche financière (pré-compta / pilotage) -----------------------------

export interface TreasuryLine {
  label: string;
  amount: number;
  explanation: string;
}
export interface TreasuryView {
  period_from: string;
  period_to: string;
  currency: string;
  sales_in: number;
  outflows_paid: number;
  estimated_balance: number;
  upcoming_7d: number;
  upcoming_30d: number;
  alert: string | null;
  lines: TreasuryLine[];
  disclaimer: string;
}

export interface InventoryItem {
  product_id: number;
  product_name: string | null;
  quantity: number;
  unit_cost: number;
  value: number;
  at_risk: boolean;
  explanation: string;
}
export interface InventoryValuation {
  currency: string;
  total_value: number;
  at_risk_value: number;
  items: InventoryItem[];
  explanation: string;
  disclaimer: string;
}

export interface ProductMargin {
  product_id: number;
  product_name: string | null;
  units_sold: number;
  avg_sale_price: number;
  last_cost: number;
  margin_unit: number;
  margin_pct: number | null;
  cost_trend: string | null;
  signal: string | null;
  explanation: string;
}
export interface MarginReport {
  period_from: string;
  period_to: string;
  items: ProductMargin[];
  explanation: string;
  disclaimer: string;
}

export interface ExpenseCategory {
  id: number;
  code: string;
  label: string;
  kind: string;
  accounting_hint: string | null;
}

export interface ExpenseInvoice {
  id: number;
  number: string | null;
  supplier_id: number | null;
  total_amount: number | null;
  currency: string;
  paid: boolean;
  category_id: number | null;
  expense_kind: string;
  classification_source: string | null;
  classification_confidence: number | null;
  classification_explanation: string | null;
}

export interface FinanceAlert {
  type: string;
  severity: string;
  title: string;
  reason: string;
  invoice_ids: number[];
  product_id: number | null;
}

export const getTreasury = () => api.get<TreasuryView>("/finance/treasury").then((r) => r.data);
export const getInventoryValue = () =>
  api.get<InventoryValuation>("/finance/inventory-value").then((r) => r.data);
export const getMargins = () => api.get<MarginReport>("/finance/margins").then((r) => r.data);
export const getExpenseCategories = () =>
  api.get<ListResponse<ExpenseCategory>>("/finance/categories").then((r) => r.data.items);
export const getExpenses = () =>
  api.get<ListResponse<ExpenseInvoice>>("/finance/expenses").then((r) => r.data.items);
export const classifyAll = () =>
  api.post<{ classified: number }>("/finance/expenses/classify-all").then((r) => r.data);
export const classifyInvoice = (id: number) =>
  api.post<ExpenseInvoice>(`/finance/invoices/${id}/classify`).then((r) => r.data);
export const confirmClassification = (id: number, category_id: number, kind: string) =>
  api
    .post<ExpenseInvoice>(`/finance/invoices/${id}/classification`, { category_id, kind })
    .then((r) => r.data);
export const getFinanceAlerts = () =>
  api.get<{ alerts: FinanceAlert[]; explanation: string }>("/finance/alerts").then((r) => r.data);
