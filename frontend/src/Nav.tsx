import { Link, useLocation } from "react-router-dom";

export function Nav() {
  const { pathname } = useLocation();
  const is = (p: string) => (p === "/" ? pathname === "/" : pathname.startsWith(p));

  return (
    <div className="nav">
      <Link to="/" className="nav-brand">
        <span className="serif">NIRNAY</span>
        <span className="deva">निर्णय</span>
      </Link>
      <div className="nav-links">
        <Link to="/districts" className={is("/districts") ? "active" : ""}>Districts</Link>
        <Link to="/districts/mangan" className={is("/districts/mangan") ? "active" : ""}>Overview</Link>
        <Link to="/districts/mangan/plan" className={is("/districts/mangan/plan") ? "active" : ""}>Relocation plan</Link>
      </div>
    </div>
  );
}
