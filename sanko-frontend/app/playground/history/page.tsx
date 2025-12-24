import { SessionHistory } from "@/components/playground/session-history";

export const metadata = {
    title: 'History | Agent Playground',
    description: 'View past agent sessions and logs.',
};

export default function HistoryPage() {
    return (
        <SessionHistory />
    );
}
