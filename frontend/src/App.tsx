import { Routes, Route, Navigate, useParams } from "react-router-dom";
import LandingPage from "@/pages/LandingPage";
import AuthPage from "@/pages/AuthPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import DashboardLayout from "@/layouts/DashboardLayout";
import DashboardPage from "@/pages/DashboardPage";
import TransactionsPage from "@/pages/TransactionsPage";
import WalletPage from "@/pages/WalletPage";
import NetworkCasesPage from "@/pages/NetworkCasesPage";
import FlowExplorerPage from "@/pages/FlowExplorerPage";
import ReportsPage from "@/pages/ReportsPage";
import { PublicOnly, RequireAuth } from "@/components/AuthGuards";

function RedirectWalletLegacy() {
  const { address } = useParams<{ address: string }>();
  return <Navigate to={`/dashboard/wallets/${address}`} replace />;
}

function RedirectNetworkLegacy() {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/dashboard/networks/${id}`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/login"
        element={
          <PublicOnly>
            <AuthPage />
          </PublicOnly>
        }
      />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <DashboardLayout />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="wallets" element={<WalletPage />} />
        <Route path="wallets/:address" element={<WalletPage />} />
        <Route path="networks" element={<NetworkCasesPage />} />
        <Route path="networks/:id" element={<NetworkCasesPage />} />
        <Route path="explorer" element={<FlowExplorerPage />} />
        <Route path="reports" element={<ReportsPage />} />
      </Route>
      <Route path="/transactions" element={<Navigate to="/dashboard/transactions" replace />} />
      <Route path="/wallets" element={<Navigate to="/dashboard/wallets" replace />} />
      <Route path="/wallets/:address" element={<RedirectWalletLegacy />} />
      <Route path="/networks" element={<Navigate to="/dashboard/networks" replace />} />
      <Route path="/networks/:id" element={<RedirectNetworkLegacy />} />
      <Route path="/explorer" element={<Navigate to="/dashboard/explorer" replace />} />
      <Route path="/reports" element={<Navigate to="/dashboard/reports" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
