// Logo MyHanout AI : icône de marque (échoppe dans une bulle de chat, tuile verte).
// L'icône est servie depuis /logo-icon.png (master) ; le wordmark associe l'icône
// à un texte dont la couleur suit le thème (lisible sur fond clair comme sombre).
export function Logo({ size = 32 }: { size?: number }) {
  return (
    <img
      src="/logo-icon.png"
      width={size}
      height={size}
      alt="MyHanout AI"
      className="rounded-[22%]"
    />
  );
}

export function LogoWordmark() {
  return (
    <div className="flex items-center gap-2">
      <Logo size={30} />
      <span className="text-lg font-extrabold tracking-tight">
        MyHanout<span className="text-brand"> AI</span>
      </span>
    </div>
  );
}
