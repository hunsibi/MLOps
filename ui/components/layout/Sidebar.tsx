"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Database, Tag, Dumbbell, FlaskConical, Box } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/",            label: "Dashboard",    icon: LayoutDashboard },
  { href: "/datasets",    label: "Datasets",     icon: Database },
  { href: "/labeling",    label: "Labeling",     icon: Tag },
  { href: "/training",    label: "Training",     icon: Dumbbell },
  { href: "/experiments", label: "Experiments",  icon: FlaskConical },
  { href: "/models",      label: "Models",       icon: Box },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="px-5 py-4 border-b border-gray-800">
        <span className="font-bold text-lg tracking-tight text-white">MLOps</span>
        <span className="text-xs text-gray-500 ml-1">Pipeline</span>
      </div>
      <nav className="flex-1 py-4 space-y-1 px-2">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
              path === href || (href !== "/" && path.startsWith(href))
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white hover:bg-gray-800"
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
