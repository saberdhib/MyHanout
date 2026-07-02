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
  // Rôle plateforme (backoffice MyHanout) — indice UX ; l'accès reste vérifié en base.
  if (data.platform_role) localStorage.setItem("platform_role", data.platform_role);
  else localStorage.removeItem("platform_role");
}

/** Rôle plateforme courant (superadmin | support | billing) ou null. */
export const platformRole = (): string | null => localStorage.getItem("platform_role");

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

// --- Chaîne du froid (équipements) -----------------------------------------

export interface EquipmentStatus {
  id: number;
  name: string;
  kind: string;
  location: string | null;
  min_temp_c: number;
  max_temp_c: number;
  last_temp_c: number | null;
  last_recorded_at: string | null;
  status: string; // ok | alert | unknown
  explanation: string;
}
export interface EquipmentStatusList {
  items: EquipmentStatus[];
  alerts: number;
  explanation: string;
}

export const getEquipment = () =>
  api.get<EquipmentStatusList>("/equipment").then((r) => r.data);
export const pollEquipment = () =>
  api.post<{ provider: string; readings: number; alerts: number }>("/equipment/poll").then((r) => r.data);
export const createEquipment = (body: {
  name: string;
  kind: string;
  location?: string;
  min_temp_c: number;
  max_temp_c: number;
  sensor_external_id?: string;
}) => api.post<EquipmentStatus>("/equipment", body).then((r) => r.data);

// --- Connecteur caisse (POS) -----------------------------------------------
export const syncPos = () =>
  api
    .post<{ provider: string; inserted: number; duplicates: number; skipped_unknown_sku: number }>(
      "/import/pos/sync",
    )
    .then((r) => r.data);

// --- Config socle : modules actifs par type de commerce ---------------------
export interface ModulesConfig {
  business_type: string | null;
  enabled: string[];
  modules: { key: string; label: string; enabled: boolean }[];
}
export const getModules = () =>
  api.get<ModulesConfig>("/config/modules").then((r) => r.data);

// --- Connecteurs : état (sans secret) --------------------------------------
export interface Connector {
  key: string;
  label: string;
  category: string; // messaging | data | iot | ai
  provider: string;
  status: string; // mock | live | needs_config
  configured: boolean;
  hint: string;
}
export interface ConnectorsConfig {
  items: Connector[];
  explanation: string;
}
export const getConnectors = () =>
  api.get<ConnectorsConfig>("/config/connectors").then((r) => r.data);

// --- Connecteurs par commerce (modèle B, self-service, owner) ---
export interface ConnectorStatus {
  kind: string; // whatsapp | slack | telegram
  configured: boolean;
  active: boolean;
  public: Record<string, string>;
  has_secret: boolean;
}
export const getConnectorSettings = () =>
  api.get<ConnectorStatus[]>("/connectors/manage").then((r) => r.data);
export const saveConnector = (kind: string, fields: Record<string, string>, active = true) =>
  api.put<ConnectorStatus>(`/connectors/manage/${kind}`, { fields, active }).then((r) => r.data);
export const deleteConnector = (kind: string) =>
  api.delete(`/connectors/manage/${kind}`).then((r) => r.data);

// --- Ouverture : clés API + webhooks (n8n / Make / Zapier) -----------------
export interface ApiKey {
  id: number;
  name: string;
  prefix: string;
  scopes: string;
  revoked: boolean;
  last_used_at: string | null;
}
export interface ApiKeyCreated extends ApiKey {
  key: string;
}
export interface Webhook {
  id: number;
  url: string;
  events: string;
  active: boolean;
  last_status: number | null;
  failures: number;
}
export interface WebhookCreated extends Webhook {
  secret: string;
}

export const listApiKeys = () =>
  api.get<ListResponse<ApiKey>>("/api-keys").then((r) => r.data);
export const createApiKey = (name: string, scopes = "*") =>
  api.post<ApiKeyCreated>("/api-keys", { name, scopes }).then((r) => r.data);
export const revokeApiKey = (id: number) => api.delete(`/api-keys/${id}`).then((r) => r.data);

export const listWebhooks = () =>
  api.get<ListResponse<Webhook>>("/webhooks").then((r) => r.data);
export const createWebhook = (url: string, events = "*") =>
  api.post<WebhookCreated>("/webhooks", { url, events }).then((r) => r.data);
export const deleteWebhook = (id: number) => api.delete(`/webhooks/${id}`).then((r) => r.data);

// --- Catalogue : gestion produits + familles -------------------------------
export interface CatalogProduct {
  id: number;
  sku: string;
  name: string;
  category: string | null;
  family: string | null;
  unit: string;
  unit_price: number | null;
  perishable: boolean;
  shelf_life_days: number | null;
  supplier_id: number | null;
}

export const getFamilies = () =>
  api.get<string[]>("/catalog/families").then((r) => r.data);

export const getProducts = (params?: { family?: string; search?: string }) =>
  api.get<ListResponse<CatalogProduct>>("/catalog/products", { params }).then((r) => r.data);

export const createProduct = (body: Partial<CatalogProduct> & { sku: string; name: string }) =>
  api.post<CatalogProduct>("/catalog/products", body).then((r) => r.data);

export const updateProduct = (id: number, body: Partial<CatalogProduct>) =>
  api.patch<CatalogProduct>(`/catalog/products/${id}`, body).then((r) => r.data);

// --- Boucherie (lots / décomposition / traçabilité) ------------------------
export interface MeatLotRow {
  id: number;
  lot_code: string;
  species: string;
  label: string;
  status: string;
  gross_weight_kg: number;
  purchase_cost: number;
}
export interface MeatCutOut {
  id: number;
  cut_label: string;
  product_id: number | null;
  expected_weight_kg: number | null;
  actual_weight_kg: number | null;
  is_waste: boolean;
  allocated_cost: number | null;
  cost_per_kg: number | null;
  explanation: string | null;
}
export interface MeatLotSummary {
  id: number;
  lot_code: string;
  species: string;
  label: string;
  status: string;
  gross_weight_kg: number;
  purchase_cost: number;
  saleable_weight_kg: number;
  waste_weight_kg: number;
  yield_pct: number | null;
  cost_per_kg: number | null;
  cuts: MeatCutOut[];
  traceability: string;
  explanation: string;
}
export interface MeatCutIn {
  cut_label: string;
  actual_weight_kg?: number;
  expected_weight_kg?: number;
  is_waste?: boolean;
}

// --- Socle data platform : pipelines, recommandations, alertes, temps réel ---

export interface PipelineRun {
  id: number;
  job_name: string;
  status: string;
  trigger: string;
  started_at: string | null;
  finished_at: string | null;
  data_freshness_at: string | null;
  rows_processed: number;
  error: string | null;
  duration_ms: number | null;
}

export interface PipelineJobHealth {
  job_name: string;
  last_status: string | null;
  last_run_at: string | null;
  data_freshness_at: string | null;
  last_error: string | null;
}

export interface PipelineHealth {
  jobs: PipelineJobHealth[];
  explanation: string;
}

export interface Recommendation {
  id: number;
  product_id: number;
  product_name: string | null;
  action: string;
  suggested_quantity: number;
  horizon_days: number;
  confidence: number;
  risk_factor: number;
  score: number;
  status: string;
  model_version: string;
  pipeline_run_id: number | null;
  explanation: string;
}

export interface SimulateResult {
  product_id: number;
  ordered_quantity: number;
  horizon_days: number;
  forecast_demand: number;
  current_stock: number;
  projected_stock: number;
  stockout_risk: number;
  overstock_days: number;
  explanation: string;
}

export interface Alert {
  id: number;
  kind: string;
  priority: string;
  status: string;
  title: string;
  message: string | null;
  rule: string | null;
  threshold: number | null;
  observed_value: number | null;
  recommended_action: string | null;
  explanation: string | null;
  entity_type: string | null;
  entity_id: number | null;
  created_at: string | null;
}

export const getPipelineRuns = (params?: { job?: string; status?: string }) =>
  api.get<ListResponse<PipelineRun>>("/pipelines/runs", { params }).then((r) => r.data);
export const getPipelineHealth = () =>
  api.get<PipelineHealth>("/pipelines/health").then((r) => r.data);
export const triggerPipeline = (job: string) =>
  api.post<PipelineRun>(`/pipelines/${job}/trigger`).then((r) => r.data);
export const recomputeForecasts = () =>
  api.post<PipelineRun>("/forecasts/recompute").then((r) => r.data);

export const getRecommendations = (params?: { status?: string; live?: boolean }) =>
  api.get<ListResponse<Recommendation>>("/recommendations", { params }).then((r) => r.data);
export const simulateOrder = (product_id: number, quantity: number, horizon_days?: number) =>
  api
    .post<SimulateResult>("/recommendations/simulate", { product_id, quantity, horizon_days })
    .then((r) => r.data);

export const getAlerts = (status?: string) =>
  api.get<ListResponse<Alert>>("/alerts", { params: status ? { status } : {} }).then((r) => r.data);
export const resolveAlert = (id: number, note?: string, dismiss = false) =>
  api.post<Alert>(`/alerts/${id}/resolve`, { note, dismiss }).then((r) => r.data);

export interface MarkdownSuggestion {
  id: number;
  product_id: number;
  product_name: string | null;
  quantity_at_risk: number;
  expiry_date: string | null;
  days_to_expiry: number;
  current_price: number;
  suggested_price: number;
  discount_pct: number;
  expected_units_cleared: number;
  recovered_value: number;
  avoided_loss: number;
  baseline_loss: number;
  confidence: number;
  score: number;
  status: string;
  model_version: string;
  pipeline_run_id: number | null;
  explanation: string;
}

export const getMarkdowns = (status?: string) =>
  api
    .get<ListResponse<MarkdownSuggestion>>("/markdown", { params: status ? { status } : {} })
    .then((r) => r.data);
export const scanMarkdowns = () =>
  api.post<ListResponse<MarkdownSuggestion>>("/markdown/scan").then((r) => r.data);
export const applyMarkdown = (id: number) =>
  api.post<MarkdownSuggestion>(`/markdown/${id}/apply`).then((r) => r.data);
export const rejectMarkdown = (id: number) =>
  api.post<MarkdownSuggestion>(`/markdown/${id}/reject`).then((r) => r.data);

// --- Production & recettes (agent Production) ---
export interface RecipeItem {
  id: number;
  ingredient_product_id: number;
  ingredient_name: string | null;
  quantity: number;
  unit: string;
}
export interface Recipe {
  id: number;
  product_id: number;
  product_name: string | null;
  name: string;
  yield_quantity: number;
  unit: string;
  active: boolean;
  notes: string | null;
  items: RecipeItem[];
}
export interface ProductionPlan {
  id: number;
  product_id: number;
  product_name: string | null;
  recipe_id: number | null;
  plan_date: string | null;
  horizon_days: number;
  forecast_demand: number;
  current_stock: number;
  suggested_quantity: number;
  batches: number;
  confidence: number;
  status: string;
  model_version: string;
  explanation: string;
}
export interface IngredientNeed {
  ingredient_product_id: number;
  ingredient_name: string | null;
  quantity: number;
  unit: string;
  estimated_cost: number;
}
export interface ProductionPlanResult {
  plans: ProductionPlan[];
  ingredients: IngredientNeed[];
  total_ingredient_cost: number;
}

export const getRecipes = () =>
  api.get<ListResponse<Recipe>>("/recipes").then((r) => r.data);
export const createRecipe = (body: {
  product_id: number;
  name: string;
  yield_quantity: number;
  unit?: string;
  notes?: string;
  items: { ingredient_product_id: number; quantity: number; unit?: string }[];
}) => api.post<Recipe>("/recipes", body).then((r) => r.data);
export const deleteRecipe = (id: number) => api.delete(`/recipes/${id}`).then((r) => r.data);

export const getProductionPlan = () =>
  api.get<ProductionPlanResult>("/production/plan").then((r) => r.data);
export const scanProduction = () =>
  api.post<ProductionPlanResult>("/production/scan").then((r) => r.data);
export const confirmProduction = (id: number) =>
  api.post<ProductionPlan>(`/production/${id}/confirm`).then((r) => r.data);
export const dismissProduction = (id: number) =>
  api.post<ProductionPlan>(`/production/${id}/dismiss`).then((r) => r.data);

// --- Briefing du matin (agent Tâches du jour) ---
export interface BriefingItem {
  id: number;
  category: string;
  priority: number;
  title: string;
  detail: string | null;
  action: string | null;
  value: number;
  entity_type: string | null;
  entity_id: number | null;
  done: boolean;
}
export interface Briefing {
  id: number;
  briefing_date: string | null;
  summary: string;
  total_items: number;
  total_value: number;
  status: string;
  items: BriefingItem[];
}

export const getBriefing = () =>
  api.get<Briefing | null>("/briefing").then((r) => r.data);
export const generateBriefing = () =>
  api.post<Briefing>("/briefing/generate").then((r) => r.data);
export const sendBriefing = (id: number) =>
  api.post<Briefing>(`/briefing/${id}/send`).then((r) => r.data);
export const completeBriefingItem = (id: number, done = true) =>
  api.post(`/briefing/items/${id}/done`, null, { params: { done } }).then((r) => r.data);

// --- Prix conseillés (agent Prix) ---
export interface PriceSuggestion {
  product_id: number;
  product_name: string | null;
  current_price: number;
  unit_cost: number;
  current_margin: number;
  suggested_price: number;
  target_margin: number;
  action: string; // raise | lower | hold
  delta: number;
  confidence: number;
  explanation: string;
}
export const getPriceSuggestions = () =>
  api.get<ListResponse<PriceSuggestion>>("/pricing/suggestions").then((r) => r.data);
export const applyPrice = (product_id: number, price: number) =>
  api.post<PriceSuggestion>("/pricing/apply", { product_id, price }).then((r) => r.data);

// --- Effectifs (agent Effectifs) ---
export interface StaffingDay {
  date: string;
  weekday: string;
  predicted_demand: number;
  vs_average_pct: number;
  suggested_staff: number;
  base_staff: number;
  delta: number;
  explanation: string;
}
export interface StaffingPlan {
  days: StaffingDay[];
  average_demand: number;
  base_staff: number;
  units_per_staff: number;
  explanation: string;
}
export const getStaffingPlan = (horizon_days = 7) =>
  api.get<StaffingPlan>("/staffing/plan", { params: { horizon_days } }).then((r) => r.data);

// --- Bilan hebdomadaire (agent Bilan) ---
export interface WeeklyReport {
  period_start: string;
  period_end: string;
  revenue: number;
  revenue_prev: number;
  revenue_delta_pct: number;
  units_sold: number;
  gross_margin: number;
  gross_margin_pct: number;
  top_products: { product_id: number; name: string | null; revenue: number }[];
  alerts_open: number;
  markdown_recovered: number;
  orders_suggested: number;
  highlights: string[];
  actions: string[];
  narrative: string;
}
export const getWeeklyReport = () =>
  api.get<WeeklyReport>("/report/weekly").then((r) => r.data);
export const sendWeeklyReport = () =>
  api.post<WeeklyReport>("/report/weekly/send").then((r) => r.data);

// --- Contrôles : 3-way match factures + démarque inconnue ---
export interface InvoiceFinding {
  invoice_id: number;
  invoice_number: string;
  supplier_name: string | null;
  product_id: number;
  product_name: string | null;
  kind: string; // price_drift | price_vs_order | qty_vs_order
  expected: number;
  observed: number;
  overcharge: number;
  explanation: string;
}
export interface InvoiceControlReport {
  findings: InvoiceFinding[];
  total_overcharge: number;
  invoices_checked: number;
  explanation: string;
}
export interface ShrinkageItem {
  product_id: number;
  product_name: string | null;
  baseline_date: string;
  expected_stock: number;
  actual_stock: number;
  missing_units: number;
  estimated_loss: number;
  explanation: string;
}
export interface ShrinkageReport {
  items: ShrinkageItem[];
  total_loss: number;
  products_checked: number;
  explanation: string;
}
// --- Carnet HACCP (hygiène + conformité froid) ---
export interface HygieneTask {
  id: number;
  name: string;
  frequency: string;
  active: boolean;
  notes: string | null;
  due: boolean;
  last_done_at: string | null;
  last_done_by: string | null;
}
export interface EquipmentCompliance {
  equipment_id: number;
  equipment_name: string;
  min_temp_c: number;
  max_temp_c: number;
  readings: number;
  in_range: number;
  compliance_pct: number;
  last_temp_c: number | null;
  last_at: string | null;
  breaches: string[];
}
export interface HaccpRegister {
  period_days: number;
  generated_at: string;
  temperature: EquipmentCompliance[];
  hygiene: {
    id: number;
    task_id: number;
    task_name: string | null;
    done_at: string;
    done_by: string | null;
    note: string | null;
  }[];
  tasks_due: number;
  explanation: string;
}
export const getHygieneTasks = () =>
  api.get<ListResponse<HygieneTask>>("/haccp/tasks").then((r) => r.data);
export const createHygieneTask = (name: string, frequency: string) =>
  api.post<HygieneTask>("/haccp/tasks", { name, frequency }).then((r) => r.data);
export const deleteHygieneTask = (id: number) =>
  api.delete(`/haccp/tasks/${id}`).then((r) => r.data);
export const completeHygieneTask = (id: number, note?: string) =>
  api.post(`/haccp/tasks/${id}/complete`, { note }).then((r) => r.data);
export const getHaccpRegister = (days = 14) =>
  api.get<HaccpRegister>("/haccp/register", { params: { days } }).then((r) => r.data);

export const getInvoiceControls = () =>
  api.get<InvoiceControlReport>("/controls/invoices").then((r) => r.data);
export const getShrinkage = () =>
  api.get<ShrinkageReport>("/controls/shrinkage").then((r) => r.data);

// Jeton courant (pour le flux SSE qui passe par fetch, pas axios).
export const currentToken = () => localStorage.getItem("token");
export const apiBaseUrl = baseURL;

export const getMeatLots = () => api.get<MeatLotRow[]>("/meat/lots").then((r) => r.data);
export const getMeatLot = (id: number) =>
  api.get<MeatLotSummary>(`/meat/lots/${id}`).then((r) => r.data);
export const createMeatLot = (body: {
  lot_code: string;
  species: string;
  label: string;
  gross_weight_kg: number;
  purchase_cost: number;
}) => api.post<MeatLotSummary>("/meat/lots", body).then((r) => r.data);
export const setMeatBreakdown = (id: number, cuts: MeatCutIn[]) =>
  api.put<MeatLotSummary>(`/meat/lots/${id}/breakdown`, { cuts }).then((r) => r.data);

// --- Backoffice plateforme (SaaS : pilotage cross-tenant du parc) -----------
export interface PlatformOverview {
  clients_total: number;
  clients_active: number;
  clients_trial: number;
  clients_suspended: number;
  mrr_total_eur: number;
  arr_total_eur: number;
}
export interface ClientSummary {
  organization_id: number;
  name: string;
  slug: string;
  business_type: string | null;
  status: string;
  plan: string;
  subscription_status: string | null;
  mrr_eur: number;
  users: number;
  products: number;
  sales: number;
  created_at: string | null;
}
export interface ClientDetail extends ClientSummary {
  invoices: number;
  connectors_configured: number;
  open_tickets: number;
  last_sale_at: string | null;
  trial_ends_on: string | null;
  started_on: string | null;
  current_period_end: string | null;
  notes: string | null;
}
export interface ProvisionClientPayload {
  name: string;
  slug: string;
  business_type?: string;
  owner_email: string;
  owner_full_name?: string;
  owner_password: string;
  plan?: string;
}

export const getPlatformOverview = () =>
  api.get<PlatformOverview>("/platform/overview").then((r) => r.data);
export const getPlatformClients = () =>
  api.get<ListResponse<ClientSummary>>("/platform/clients").then((r) => r.data);
export const getPlatformClient = (orgId: number) =>
  api.get<ClientDetail>(`/platform/clients/${orgId}`).then((r) => r.data);
export const provisionClient = (payload: ProvisionClientPayload) =>
  api.post<ClientDetail>("/platform/clients", payload).then((r) => r.data);
export const setClientStatus = (orgId: number, status: string, reason?: string) =>
  api
    .post<ClientDetail>(`/platform/clients/${orgId}/status`, { status, reason })
    .then((r) => r.data);
export const setClientPlan = (
  orgId: number,
  plan: string,
  mrr_eur?: number,
  subscription_status?: string,
) =>
  api
    .post<ClientDetail>(`/platform/clients/${orgId}/plan`, {
      plan,
      mrr_eur,
      subscription_status,
    })
    .then((r) => r.data);
