import SurveyFlow from '@/components/survey/SurveyFlow';

export default function SurveyPage() {
    return (
        <div className="min-h-screen bg-[#0a0a0f] text-white flex flex-col">
            <header className="p-6 border-b border-zinc-800/50">
                <div className="max-w-7xl mx-auto flex items-center gap-2">
                    <span className="text-xl font-bold tracking-tight">
                        <span className="text-emerald-500">Sanko</span>Slides
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-medium border border-emerald-500/20">
                        Beta Profile
                    </span>
                </div>
            </header>

            <main className="flex-1 flex flex-col items-center justify-center p-4">
                <SurveyFlow />
            </main>
        </div>
    );
}
