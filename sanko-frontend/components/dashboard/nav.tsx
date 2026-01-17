import { cn } from "@/lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { LayoutDashboard, FileText, Settings, LogOut, Plus } from "lucide-react";
import { PrefetchLink, PREFETCH_CONFIGS } from "@/components/ui/prefetch-link";

interface DashboardNavProps {
    items: {
        title: string;
        href: string;
        icon: React.ComponentType<{ className?: string }>;
    }[];
}

// Map routes to their prefetch configurations
const ROUTE_PREFETCH_MAP: Record<string, string[]> = {
    '/dashboard/templates': PREFETCH_CONFIGS.templates,
};

export function DashboardNav({ items }: DashboardNavProps) {
    const pathname = usePathname();

    return (
        <nav className="grid items-start gap-2">
            {items.map((item, index) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                const prefetchUrls = ROUTE_PREFETCH_MAP[item.href];

                const linkContent = (
                    <span
                        className={cn(
                            "group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-all duration-200 ease-in-out",
                            isActive
                                ? "bg-primary/10 text-primary border border-primary/20 shadow-[0_0_15px_-4px_rgba(16,185,129,0.3)]"
                                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                        )}
                    >
                        <Icon className={cn("mr-2 h-4 w-4 transition-colors", isActive ? "text-primary" : "text-muted-foreground group-hover:text-primary")} />
                        <span>{item.title}</span>
                    </span>
                );

                // Use PrefetchLink for routes with prefetch config, otherwise use regular Link
                if (prefetchUrls) {
                    return (
                        <PrefetchLink key={index} href={item.href} prefetchUrls={prefetchUrls}>
                            {linkContent}
                        </PrefetchLink>
                    );
                }

                return (
                    <Link key={index} href={item.href}>
                        {linkContent}
                    </Link>
                );
            })}
        </nav>
    );
}

