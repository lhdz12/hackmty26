import Link from "next/link";
import { useRouter } from "next/router";

export default function BottomNav() {
  const router = useRouter();
  const isActive = (path) => router.pathname === path;

  return (
    <nav className="bottom-nav">
      <Link
        href="/"
        className={`nav-item ${isActive("/") ? "nav-item--active" : ""}`}
      >
        Pedidos
      </Link>
      <Link
        href="/summary"
        className={`nav-item ${isActive("/summary") ? "nav-item--active" : ""}`}
      >
        Ganancias
      </Link>
    </nav>
  );
}
