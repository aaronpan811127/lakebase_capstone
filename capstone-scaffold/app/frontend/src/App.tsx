import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "@/components/Layout";

const Customers = lazy(() => import("@/pages/Customers"));
const CustomerDetail = lazy(() => import("@/pages/CustomerDetail"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Reports = lazy(() => import("@/pages/Reports"));

export default function App() {
  return (
    <Layout>
      <Suspense fallback={<div className="loading">Loading…</div>}>
        <Routes>
          <Route path="/" element={<Navigate to="/customers" replace />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/customers/:id" element={<CustomerDetail />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="*" element={<Navigate to="/customers" replace />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
