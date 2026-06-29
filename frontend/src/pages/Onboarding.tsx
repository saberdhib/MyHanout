import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Logo } from "../components/Logo";
import { addProduct, addSupplier, inviteMember, signup } from "../api/client";

// Onboarding self-service, pensé mobile : créer son commerce, un produit,
// un fournisseur, inviter un comptable. Charte appliquée (vert/nuit, Manrope).
export default function Onboarding() {
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [org, setOrg] = useState({ organization_name: "", email: "", password: "" });
  const [product, setProduct] = useState({ sku: "", name: "" });
  const [accountantEmail, setAccountantEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function createOrg() {
    setError(null);
    try {
      await signup(org);
      setStep(2);
    } catch {
      setError("Échec de création. Email déjà utilisé ?");
    }
  }

  async function setup() {
    if (product.sku && product.name) {
      const s = await addSupplier("Mon fournisseur");
      await addProduct({ ...product, unit: "unit" });
      void s;
    }
    setStep(3);
  }

  async function invite() {
    if (accountantEmail) await inviteMember(accountantEmail, "accountant");
    nav("/");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface p-4">
      <div className="w-full max-w-md rounded-card bg-white p-8 shadow-soft">
        <div className="mb-6 flex items-center gap-3">
          <Logo size={40} />
          <div>
            <div className="text-xl font-extrabold">MyHanout AI</div>
            <div className="text-sm text-gray-500">Créez votre commerce</div>
          </div>
        </div>

        {error && <div className="mb-4 rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>}

        {step === 1 && (
          <div className="space-y-3">
            <Field label="Nom du commerce" value={org.organization_name}
              onChange={(v) => setOrg({ ...org, organization_name: v })} />
            <Field label="Email" value={org.email} onChange={(v) => setOrg({ ...org, email: v })} />
            <Field label="Mot de passe" type="password" value={org.password}
              onChange={(v) => setOrg({ ...org, password: v })} />
            <Cta onClick={createOrg}>Créer mon commerce →</Cta>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Ajoutez un premier produit (optionnel).</p>
            <Field label="SKU" value={product.sku} onChange={(v) => setProduct({ ...product, sku: v })} />
            <Field label="Nom du produit" value={product.name}
              onChange={(v) => setProduct({ ...product, name: v })} />
            <Cta onClick={setup}>Continuer →</Cta>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Invitez votre comptable (optionnel).</p>
            <Field label="Email du comptable" value={accountantEmail} onChange={setAccountantEmail} />
            <Cta onClick={invite}>Terminer →</Cta>
          </div>
        )}

        <div className="mt-6 text-center text-xs text-gray-400">Étape {step} / 3</div>
      </div>
    </div>
  );
}

function Field(props: { label: string; value: string; type?: string; onChange: (v: string) => void }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-gray-600">{props.label}</span>
      <input
        type={props.type || "text"}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        className="w-full rounded-card border border-gray-200 px-3 py-2 focus:border-brand focus:outline-none"
      />
    </label>
  );
}

function Cta({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="w-full rounded-card bg-brand px-4 py-2 font-semibold text-white shadow-soft hover:bg-brand-dark"
    >
      {children}
    </button>
  );
}
