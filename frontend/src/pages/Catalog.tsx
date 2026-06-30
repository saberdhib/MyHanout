import { useEffect, useMemo, useState } from "react";
import { Card } from "../components/Card";
import {
  createProduct,
  getFamilies,
  getProducts,
  updateProduct,
  type CatalogProduct,
} from "../api/client";

const EMPTY = { sku: "", name: "", family: "", unit: "unit", unit_price: "" };

function PerishableTag() {
  return (
    <span className="ml-1 inline-flex rounded-pill bg-accent/15 px-2 py-0.5 text-[11px] font-semibold text-accent">
      périssable
    </span>
  );
}

export default function Catalog() {
  const [families, setFamilies] = useState<string[]>([]);
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState({ ...EMPTY });
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [editFamily, setEditFamily] = useState<string>("");

  async function refresh() {
    const [f, p] = await Promise.all([
      getFamilies(),
      getProducts({ family: filter || undefined, search: search || undefined }),
    ]);
    setFamilies(f);
    setProducts(p.items);
  }

  useEffect(() => {
    refresh().catch(() => setError("API injoignable."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  // Regroupement par famille pour un affichage « par rayon ».
  const grouped = useMemo(() => {
    const m = new Map<string, CatalogProduct[]>();
    for (const p of products) {
      const k = p.family || "(sans famille)";
      (m.get(k) ?? m.set(k, []).get(k)!).push(p);
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [products]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createProduct({
        sku: draft.sku.trim(),
        name: draft.name.trim(),
        family: draft.family || undefined,
        unit: draft.unit || "unit",
        unit_price: draft.unit_price ? Number(draft.unit_price) : undefined,
      });
      setDraft({ ...EMPTY });
      await refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Création impossible.");
    }
  }

  async function saveFamily(p: CatalogProduct) {
    await updateProduct(p.id, { family: editFamily || null });
    setEditing(null);
    await refresh();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Catalogue produits</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Gérez vos produits et rangez-les par famille (rayon).
        </p>
      </div>

      {error && <div className="rounded-card bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <Card title="Ajouter un produit">
        <form onSubmit={add} className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
          <input
            required
            placeholder="SKU"
            value={draft.sku}
            onChange={(e) => setDraft({ ...draft, sku: e.target.value })}
            className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
          />
          <input
            required
            placeholder="Nom"
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5 lg:col-span-2"
          />
          <select
            value={draft.family}
            onChange={(e) => setDraft({ ...draft, family: e.target.value })}
            className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
          >
            <option value="">— famille —</option>
            {families.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
          <input
            placeholder="Prix"
            type="number"
            step="0.01"
            value={draft.unit_price}
            onChange={(e) => setDraft({ ...draft, unit_price: e.target.value })}
            className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
          />
          <button className="rounded-card bg-brand px-3 py-1.5 text-sm font-semibold text-white">
            Ajouter
          </button>
        </form>
      </Card>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-night/50 dark:text-surface/50">Filtrer :</span>
        <button
          onClick={() => setFilter("")}
          className={`rounded-pill px-3 py-1 text-xs ${filter === "" ? "bg-brand text-white" : "bg-night/10 dark:bg-white/10"}`}
        >
          Tous
        </button>
        {families.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-pill px-3 py-1 text-xs ${filter === f ? "bg-brand text-white" : "bg-night/10 dark:bg-white/10"}`}
          >
            {f}
          </button>
        ))}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            refresh();
          }}
          className="ml-auto"
        >
          <input
            placeholder="Rechercher…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
          />
        </form>
      </div>

      {grouped.map(([family, items]) => (
        <Card key={family} title={family} subtitle={`${items.length} produit(s)`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-night/10 text-left text-night/50 dark:border-white/10 dark:text-surface/50">
                <th className="py-2">SKU</th>
                <th>Produit</th>
                <th>Unité</th>
                <th>Prix</th>
                <th>Famille</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr
                  key={p.id}
                  className="border-b border-night/[0.06] last:border-0 dark:border-white/[0.06]"
                >
                  <td className="py-2 font-mono text-xs">{p.sku}</td>
                  <td>
                    {p.name} {p.perishable && <PerishableTag />}
                  </td>
                  <td>{p.unit}</td>
                  <td>{p.unit_price != null ? `${p.unit_price.toFixed(2)} €` : "—"}</td>
                  <td>
                    {editing === p.id ? (
                      <span className="flex items-center gap-1">
                        <select
                          value={editFamily}
                          onChange={(e) => setEditFamily(e.target.value)}
                          className="rounded border border-night/15 px-1 py-0.5 text-xs dark:border-white/15 dark:bg-white/5"
                        >
                          <option value="">— aucune —</option>
                          {families.map((f) => (
                            <option key={f} value={f}>
                              {f}
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={() => saveFamily(p)}
                          className="rounded bg-brand px-2 py-0.5 text-xs text-white"
                        >
                          OK
                        </button>
                      </span>
                    ) : (
                      <button
                        onClick={() => {
                          setEditing(p.id);
                          setEditFamily(p.family ?? "");
                        }}
                        className="text-brand hover:underline"
                      >
                        {p.family ?? "ranger…"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ))}
      {products.length === 0 && (
        <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
          Aucun produit. Ajoute-en un ci-dessus.
        </p>
      )}
    </div>
  );
}
