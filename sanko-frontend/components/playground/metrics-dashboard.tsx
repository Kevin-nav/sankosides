"use client";

import { Loader2, Brain, Zap, Activity, DollarSign, Cpu } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MetricsSummary {
    total_agents: number;
    successful_agents: number;
    failed_agents: number;
    total_tokens: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_thinking_tokens: number;
    total_duration_ms: number;
    total_cost_usd: number;
    agents: Record<string, any>;
}

export function MetricsDashboard({ metrics }: { metrics: MetricsSummary | null }) {
    if (!metrics) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-neutral-500 gap-3">
                <div className="relative">
                    <Loader2 className="w-8 h-8 animate-spin text-emerald-500/50" />
                    <div className="absolute inset-0 animate-pulse-glow rounded-full" />
                </div>
                <span className="text-xs font-mono tracking-widest uppercase">Initializing Telemetry...</span>
            </div>
        );
    }

    const successRate = metrics.total_agents > 0
        ? Math.round((metrics.successful_agents / metrics.total_agents) * 100)
        : 0;

    return (
        <div className="space-y-6">
            {/* KPI Grid */}
            <div className="grid grid-cols-2 gap-3">
                <MetricCard
                    label="Token Usage"
                    value={metrics.total_tokens.toLocaleString()}
                    subValue={`$${metrics.total_cost_usd.toFixed(4)}`}
                    icon={<Zap className="w-4 h-4 text-amber-500" />}
                    trend="up"
                />
                <MetricCard
                    label="Success Rate"
                    value={`${successRate}%`}
                    subValue={`${metrics.successful_agents}/${metrics.total_agents} Agents`}
                    icon={<Activity className="w-4 h-4 text-emerald-500" />}
                    trend={successRate > 80 ? "up" : "neutral"}
                />
            </div>

            {/* Thinking Budget Visualization */}
            <div className="glass-card p-4 space-y-4">
                <div className="flex justify-between items-center">
                    <h3 className="text-xs font-medium text-neutral-400 uppercase tracking-wider flex items-center gap-2">
                        <Brain className="w-3 h-3 text-indigo-400" /> Neural Compute
                    </h3>
                    <span className="text-[10px] font-mono text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded">
                        {metrics.total_thinking_tokens.toLocaleString()} TOKENS
                    </span>
                </div>

                <div className="relative h-2 w-full bg-neutral-900/50 rounded-full overflow-hidden border border-white/5">
                    <div className="absolute inset-0 hud-scanline opacity-30" />
                    <div
                        className="h-full bg-gradient-to-r from-indigo-600 to-indigo-400 shadow-[0_0_10px_rgba(99,102,241,0.5)] transition-all duration-700 ease-out"
                        style={{ width: `${Math.min((metrics.total_thinking_tokens / (metrics.total_tokens || 1)) * 100, 100)}%` }}
                    />
                </div>

                <div className="grid grid-cols-3 gap-2 pt-1 border-t border-white/5 mt-2">
                    <StatMini label="Input" value={metrics.total_input_tokens} color="text-blue-400" />
                    <StatMini label="Output" value={metrics.total_output_tokens} color="text-purple-400" />
                    <StatMini label="Reasoning" value={metrics.total_thinking_tokens} color="text-indigo-400" />
                </div>
            </div>

            {/* Agent Fleet Status */}
            <div className="space-y-3">
                <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider flex items-center gap-2 px-1">
                    <Cpu className="w-3 h-3" /> Agent Swarm
                </h3>
                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2 scrollbar-dark">
                    {Object.entries(metrics.agents).map(([name, data]: [string, any]) => (
                        <div key={name} className="glass p-3 rounded-lg hover:bg-white/5 transition-all group border border-transparent hover:border-white/10">
                            <div className="flex justify-between items-start mb-2">
                                <span className="text-xs font-medium text-neutral-200 capitalize group-hover:text-emerald-400 transition-colors">
                                    {name.replace(/_/g, ' ')}
                                </span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${getStatusColor(data.status)} bg-opacity-10 border border-opacity-20`}>
                                    {data.status || 'IDLE'}
                                </span>
                            </div>
                            <div className="flex justify-between items-end text-[10px] font-mono text-neutral-500">
                                <span>{data.model}</span>
                                <span className="text-neutral-400 group-hover:text-neutral-200">
                                    {data.total_tokens.toLocaleString()}t
                                </span>
                            </div>
                        </div>
                    ))}
                    {Object.keys(metrics.agents).length === 0 && (
                        <div className="text-xs text-neutral-600 text-center py-8 border border-dashed border-neutral-800 rounded-lg">
                            System Idle. Awaiting Instructions.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function MetricCard({ label, value, subValue, icon, trend }: any) {
    return (
        <div className="glass-card p-4 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-3 opacity-50 group-hover:opacity-100 transition-opacity">
                {icon}
            </div>
            <div className="relative z-10">
                <div className="text-[10px] text-neutral-500 uppercase tracking-widest font-semibold mb-1">{label}</div>
                <div className="text-xl font-mono text-white mb-1 group-hover:text-glow transition-all">{value}</div>
                <div className="text-[10px] text-neutral-400 font-mono">{subValue}</div>
            </div>
            <div className="absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-white/10 to-transparent scale-x-0 group-hover:scale-x-100 transition-transform duration-500" />
        </div>
    );
}

function StatMini({ label, value, color }: any) {
    return (
        <div className="text-center">
            <div className="text-[9px] text-neutral-600 uppercase mb-0.5">{label}</div>
            <div className={`text-xs font-mono ${color}`}>{value > 1000 ? `${(value / 1000).toFixed(1)}k` : value}</div>
        </div>
    );
}

function getStatusColor(status: string) {
    switch (status?.toLowerCase()) {
        case 'success': return 'text-emerald-400 border-emerald-400';
        case 'failed': return 'text-rose-400 border-rose-400';
        case 'running': return 'text-amber-400 border-amber-400';
        default: return 'text-neutral-400 border-neutral-400';
    }
}
