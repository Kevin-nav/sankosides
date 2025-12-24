import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Dashboard | SankoSlides",
    description: "Manage your presentations",
};

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <DashboardShell>{children}</DashboardShell>;
}
