import { Routes, Route, NavLink } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import TransactionsPage from "./pages/TransactionsPage";
import WalletPage from "./pages/WalletPage";
import NetworkCasesPage from "./pages/NetworkCasesPage";
import FlowExplorerPage from "./pages/FlowExplorerPage";
import ReportsPage from "./pages/ReportsPage";
import {
  LayoutDashboard,
  ArrowLeftRight,
  Wallet,
  Network,
  GitBranch,
  FileText,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { to: "/wallets", label: "Wallets", icon: Wallet },
  { to: "/networks", label: "Network Cases", icon: Network },
  { to: "/explorer", label: "Flow Explorer", icon: GitBranch },
  { to: "/reports", label: "Reports", icon: FileText },
];

export default function App() {
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <aside className="w-64 border-r border-gray-800 bg-gray-900 flex flex-col">
        <div className="px-6 py-5 border-b border-gray-800">
          <h1 className="text-xl font-bold tracking-tight text-white">
            Aegis AML
          </h1>
          <p className="text-xs text-gray-400 mt-1">Blockchain Intelligence</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-600/20 text-blue-400"
                    : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/wallets" element={<WalletPage />} />
          <Route path="/wallets/:address" element={<WalletPage />} />
          <Route path="/networks" element={<NetworkCasesPage />} />
          <Route path="/networks/:id" element={<NetworkCasesPage />} />
          <Route path="/explorer" element={<FlowExplorerPage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Routes>
      </main>
    </div>
  );
}
