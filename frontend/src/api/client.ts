import axios from "axios";

// Base API : VITE_API_BASE_URL en prod, sinon proxy Vite "/api/v1".
const baseURL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const api = axios.create({ baseURL });

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
