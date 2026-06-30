import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import { Gauge } from "../components/Charts";
import { usePolling } from "../hooks/usePolling";
import { useEventStream } from "../hooks/useEventStream";
import {
  confirmProduction,
  createRecipe,
  deleteRecipe,
  dismissProduction,
  getProducts,
  getRecipes,
  getProductionPlan,
  type CatalogProduct,
  type Recipe,
} from "../api/client";

export default function Production() {
  const { data: plan, refresh } = usePolling(() => getProductionPlan(), 20000);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [products, setProducts] = useState<CatalogProduct[]>([]);

  const loadRecipes = useCallback(() => {
    getRecipes().then((d) => setRecipes(d.items));
  }, []);
  useEffect(() => {
    loadRecipes();
    getProducts().then((d) => setProducts(d.items));
  }, [loadRecipes]);

  const onEvent = useCallback(
    (e: { type: string }) => {
      if (e.type === "pipeline_finished" || e.type === "forecast_ready") refresh();
    },
    [refresh],
  );
  const { connected } = useEventStream(onEvent);

  async function act(id: number, fn: (id: number) => Promise<unknown>) {
    await fn(id);
    refresh();
  }

  const plans = (plan?.plans ?? []).filter((p) => p.suggested_quantity > 0);
  const ingredients = plan?.ingredients ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Production & recettes 🥖</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Combien fabriquer aujourd'hui (dérivé de la prévision) et les ingrédients à prévoir.{" "}
          <span className={connected ? "text-emerald-600" : "text-night/40"}>
            ● {connected ? "temps réel" : "polling"}
          </span>
        </p>
      </div>

      <Card title={`Plan de production (${plans.length})`} subtitle="Produits finis à fabriquer">
        <div className="space-y-3">
          {plans.map((p) => (
            <div
              key={`${p.product_id}-${p.id}`}
              className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold">{p.product_name ?? `Produit #${p.product_id}`}</div>
                <div className="text-sm text-night/50 dark:text-surface/50">
                  {p.batches.toFixed(0)} fournée(s)
                </div>
              </div>
              <div className="mt-2 grid gap-3 sm:grid-cols-4">
                <Metric label="À produire" value={`${p.suggested_quantity.toFixed(0)}`} />
                <Metric label="Demande prévue" value={`${p.forecast_demand.toFixed(0)}`} />
                <Metric label="Stock actuel" value={`${p.current_stock.toFixed(0)}`} />
                <div>
                  <div className="text-xs text-night/50 dark:text-surface/50">
                    Confiance {(p.confidence * 100).toFixed(0)}%
                  </div>
                  <Gauge value={p.confidence} />
                </div>
              </div>
              <p className="mt-2 text-sm text-night/70 dark:text-surface/70">{p.explanation}</p>
              {p.id > 0 && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => act(p.id, confirmProduction)}
                    className="rounded-card bg-brand px-3 py-1.5 text-sm font-semibold text-white"
                  >
                    Confirmer
                  </button>
                  <button
                    onClick={() => act(p.id, dismissProduction)}
                    className="rounded-card border border-night/15 px-3 py-1.5 text-sm dark:border-white/15"
                  >
                    Écarter
                  </button>
                </div>
              )}
            </div>
          ))}
          {plans.length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Rien à produire (le stock couvre la demande), ou aucune recette définie ci-dessous.
            </p>
          )}
        </div>
      </Card>

      {ingredients.length > 0 && (
        <Card
          title="Ingrédients à prévoir"
          subtitle={`Coût estimé total : ~${(plan?.total_ingredient_cost ?? 0).toFixed(0)} €`}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-night/50 dark:text-surface/50">
                  <th className="py-1">Ingrédient</th>
                  <th className="py-1">Quantité</th>
                  <th className="py-1">Coût estimé</th>
                </tr>
              </thead>
              <tbody>
                {ingredients.map((i) => (
                  <tr key={i.ingredient_product_id} className="border-t border-night/[0.06] dark:border-white/10">
                    <td className="py-1.5">{i.ingredient_name ?? `#${i.ingredient_product_id}`}</td>
                    <td className="py-1.5">
                      {i.quantity.toFixed(2)} {i.unit}
                    </td>
                    <td className="py-1.5">~{i.estimated_cost.toFixed(2)} €</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <RecipeManager
        recipes={recipes}
        products={products}
        onChange={() => {
          loadRecipes();
          refresh();
        }}
      />
    </div>
  );
}

function RecipeManager({
  recipes,
  products,
  onChange,
}: {
  recipes: Recipe[];
  products: CatalogProduct[];
  onChange: () => void;
}) {
  const [productId, setProductId] = useState<number | "">("");
  const [name, setName] = useState("");
  const [yieldQty, setYieldQty] = useState(1);
  const [ingId, setIngId] = useState<number | "">("");
  const [ingQty, setIngQty] = useState(1);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!productId || !name.trim()) return;
    await createRecipe({
      product_id: Number(productId),
      name: name.trim(),
      yield_quantity: yieldQty,
      items: ingId ? [{ ingredient_product_id: Number(ingId), quantity: ingQty }] : [],
    });
    setName("");
    setProductId("");
    setIngId("");
    onChange();
  }

  return (
    <Card title="Recettes (nomenclature)" subtitle="Produit fini → ingrédients par fournée">
      <form onSubmit={add} className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <select
          value={productId}
          onChange={(e) => setProductId(e.target.value ? Number(e.target.value) : "")}
          className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
        >
          <option value="">Produit fini…</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nom de la recette"
          className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
        />
        <input
          type="number"
          value={yieldQty}
          onChange={(e) => setYieldQty(Number(e.target.value))}
          placeholder="Rendement / fournée"
          className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
        />
        <select
          value={ingId}
          onChange={(e) => setIngId(e.target.value ? Number(e.target.value) : "")}
          className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
        >
          <option value="">Ingrédient (option)…</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <input
            type="number"
            value={ingQty}
            onChange={(e) => setIngQty(Number(e.target.value))}
            className="w-20 rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
          />
          <button className="rounded-card bg-brand px-3 py-1.5 text-sm font-semibold text-white">
            Ajouter
          </button>
        </div>
      </form>

      <ul className="mt-4 space-y-2 text-sm">
        {recipes.map((r) => (
          <li
            key={r.id}
            className="flex items-start justify-between gap-2 rounded-card border border-night/[0.06] p-3 dark:border-white/10"
          >
            <div>
              <div className="font-semibold">
                {r.name}{" "}
                <span className="text-night/40 dark:text-surface/40">
                  → {r.product_name} (fournée {r.yield_quantity})
                </span>
              </div>
              <div className="text-xs text-night/50 dark:text-surface/50">
                {r.items.length === 0
                  ? "aucun ingrédient"
                  : r.items
                      .map((i) => `${i.ingredient_name ?? `#${i.ingredient_product_id}`} ×${i.quantity}`)
                      .join(", ")}
              </div>
            </div>
            <button
              onClick={() => deleteRecipe(r.id).then(onChange)}
              className="text-xs text-rose-600 hover:underline"
            >
              Supprimer
            </button>
          </li>
        ))}
        {recipes.length === 0 && (
          <li className="text-night/40 dark:text-surface/40">Aucune recette. Ajoutez-en une ci-dessus.</li>
        )}
      </ul>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-night/50 dark:text-surface/50">{label}</div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}
