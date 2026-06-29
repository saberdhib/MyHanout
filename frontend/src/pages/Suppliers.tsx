import { Card } from "../components/Card";

// Placeholder : l'endpoint /suppliers sera exposé dans une itération ultérieure.
export default function Suppliers() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Fournisseurs</h1>
      <Card>
        <p className="text-sm text-gray-600">
          Page en construction. L'API fournisseurs (lecture + délais de paiement)
          sera branchée prochainement.
        </p>
      </Card>
    </div>
  );
}
