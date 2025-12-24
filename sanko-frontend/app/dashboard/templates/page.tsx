"use client";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Layers, Star, Plus } from "lucide-react";
import { useState } from "react";

// Mock Data
const templates = [
    {
        id: "1",
        title: "Modern Lecture",
        description: "Clean typography and spacious layout ideal for university lectures.",
        category: "Academic",
        color: "bg-emerald-500",
        isPro: false,
    },
    {
        id: "2",
        title: "Corporate Quarterly",
        description: "Data-driven layout perfect for business reports and analytics.",
        category: "Business",
        color: "bg-blue-500",
        isPro: true,
    },
    {
        id: "3",
        title: "Creative Portfolio",
        description: "Vibrant and image-heavy design for showcasing creative work.",
        category: "Creative",
        color: "bg-purple-500",
        isPro: false,
    },
    {
        id: "4",
        title: "Thesis Defense",
        description: "Structured and formal layout for academic defenses.",
        category: "Academic",
        color: "bg-slate-500",
        isPro: true,
    },
    {
        id: "5",
        title: "Startup Pitch",
        description: "Bold headings and high-impact slides for securing funding.",
        category: "Business",
        color: "bg-amber-500",
        isPro: false,
    },
    {
        id: "6",
        title: "Minimalist Dark",
        description: "High contrast dark mode design for sleek presentations.",
        category: "Minimal",
        color: "bg-neutral-800",
        isPro: false,
    },
];

const categories = ["All", "Academic", "Business", "Creative", "Minimal"];

export default function TemplatesPage() {
    const { loading } = useAuth();
    const [activeTab, setActiveTab] = useState("All");

    if (loading) {
        return (
            <div className="flex items-center justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    const filteredTemplates = activeTab === "All"
        ? templates
        : templates.filter(t => t.category === activeTab);

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                    <h2 className="text-3xl font-bold tracking-tight text-foreground">Templates</h2>
                    <p className="text-muted-foreground">Start your next presentation with a professionally designed foundation.</p>
                </div>
                <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Custom Template
                </Button>
            </div>

            <Tabs defaultValue="All" className="space-y-6" onValueChange={setActiveTab}>
                <div className="w-full overflow-x-auto pb-2">
                    <TabsList className="w-full h-auto p-1 bg-muted grid grid-cols-5 min-w-[320px] sm:w-fit sm:flex sm:h-9 sm:p-1">
                        {categories.map((category) => (
                            <TabsTrigger
                                key={category}
                                value={category}
                                className="data-[state=active]:bg-background data-[state=active]:shadow-sm border-0"
                            >
                                <span className="text-xs sm:text-sm">{category}</span>
                            </TabsTrigger>
                        ))}
                    </TabsList>
                </div>

                <TabsContent value={activeTab} className="mt-0">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredTemplates.map((template) => (
                            <Card key={template.id} className="group overflow-hidden border-border bg-card hover:bg-accent/50 transition-colors">
                                <div className={`h-40 w-full ${template.color} relative overflow-hidden`}>
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
                                    {template.isPro && (
                                        <Badge className="absolute top-3 right-3 bg-emerald-500 hover:bg-emerald-600 border-none text-white font-medium shadow-sm flex gap-1">
                                            <Star className="w-3 h-3 fill-current" />
                                            PRO
                                        </Badge>
                                    )}
                                </div>
                                <CardHeader>
                                    <div className="flex justify-between items-start">
                                        <CardTitle className="text-lg">{template.title}</CardTitle>
                                    </div>
                                    <CardDescription className="line-clamp-2">{template.description}</CardDescription>
                                </CardHeader>
                                <CardFooter className="flex justify-between items-center">
                                    <Badge variant="secondary" className="text-xs font-normal">
                                        {template.category}
                                    </Badge>
                                    <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                                        Use Template
                                    </Button>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}
