import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Stocks from "./pages/Stocks";
import Forecasts from "./pages/Forecasts";
import Invoices from "./pages/Invoices";
import Suppliers from "./pages/Suppliers";
import Onboarding from "./pages/Onboarding";
import Suggestions from "./pages/Suggestions";
import EndOfDay from "./pages/EndOfDay";
import Quality from "./pages/Quality";
import Chat from "./pages/Chat";
import Promos from "./pages/Promos";
import Integrations from "./pages/Integrations";

export default function App() {
  return (
    <Routes>
      {/* Onboarding hors shell (pas de sidebar). */}
      <Route path="/signup" element={<Onboarding />} />
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="chat" element={<Chat />} />
        <Route path="promos" element={<Promos />} />
        <Route path="stocks" element={<Stocks />} />
        <Route path="forecasts" element={<Forecasts />} />
        <Route path="suggestions" element={<Suggestions />} />
        <Route path="end-of-day" element={<EndOfDay />} />
        <Route path="quality" element={<Quality />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="integrations" element={<Integrations />} />
        <Route path="suppliers" element={<Suppliers />} />
      </Route>
    </Routes>
  );
}
