// Logo placeholder MyHanout AI : échoppe stylisée dans une bulle de chat,
// dégradé vert. Remplacer par les assets finaux (mêmes dimensions).
export function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-label="MyHanout AI">
      <defs>
        <linearGradient id="mh-grad" x1="0" y1="0" x2="48" y2="48">
          <stop stopColor="#12B76A" />
          <stop offset="1" stopColor="#0E9A59" />
        </linearGradient>
      </defs>
      {/* Bulle de chat */}
      <path
        d="M8 6h32a4 4 0 0 1 4 4v22a4 4 0 0 1-4 4H20l-9 7v-7H8a4 4 0 0 1-4-4V10a4 4 0 0 1 4-4z"
        fill="url(#mh-grad)"
      />
      {/* Échoppe (auvent + comptoir) en négatif blanc */}
      <path d="M14 16h20l-2 5H16l-2-5z" fill="#fff" opacity="0.95" />
      <rect x="16" y="22" width="16" height="8" rx="1.5" fill="#fff" opacity="0.9" />
    </svg>
  );
}

export function LogoWordmark() {
  return (
    <div className="flex items-center gap-2">
      <Logo size={28} />
      <span className="text-lg font-extrabold tracking-tight">MyHanout AI</span>
    </div>
  );
}
