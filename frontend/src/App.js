import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import { Loading } from "@/components/kit";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Discovery from "@/pages/Discovery";
import Companies from "@/pages/Companies";
import CompanyDetail from "@/pages/CompanyDetail";
import Contacts from "@/pages/Contacts";
import Validation from "@/pages/Validation";
import Campaigns from "@/pages/Campaigns";
import Emails from "@/pages/Emails";
import Followups from "@/pages/Followups";
import Replies from "@/pages/Replies";
import Opportunities from "@/pages/Opportunities";
import Services from "@/pages/Services";
import Templates from "@/pages/Templates";
import Exclusions from "@/pages/Exclusions";
import Activity from "@/pages/Activity";
import Errors from "@/pages/Errors";
import Settings from "@/pages/Settings";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="h-screen flex items-center justify-center"><Loading /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

const routes = [
  ["/", <Dashboard />], ["/discovery", <Discovery />], ["/entreprises", <Companies />], ["/entreprises/:id", <CompanyDetail />],
  ["/contacts", <Contacts />], ["/validation", <Validation />], ["/campagnes", <Campaigns />],
  ["/emails", <Emails />], ["/relances", <Followups />], ["/reponses", <Replies />],
  ["/opportunites", <Opportunities />], ["/services", <Services />], ["/modeles", <Templates />],
  ["/exclusions", <Exclusions />], ["/journal", <Activity />], ["/erreurs", <Errors />],
  ["/parametres", <Settings />],
];

function App() {
  return (
    <AuthProvider>
      <Toaster position="top-right" richColors />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          {routes.map(([path, el]) => (
            <Route key={path} path={path} element={<Protected>{el}</Protected>} />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
