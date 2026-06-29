import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Stocks from "./pages/Stocks";
import Forecasts from "./pages/Forecasts";
import Invoices from "./pages/Invoices";
import Suppliers from "./pages/Suppliers";
import Onboarding from "./pages/Onboarding";

export default function App() {
  return (
    <Routes>
      {/* Onboarding hors shell (pas de sidebar). */}
      <Route path="/signup" element={<Onboarding />} />
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="stocks" element={<Stocks />} />
        <Route path="forecasts" element={<Forecasts />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="suppliers" element={<Suppliers />} />
      </Route>
    </Routes>
  );
}
