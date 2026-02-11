"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Loader2, Palette, Save, Plus, Eye } from "lucide-react";
import { templateApi, Template, Theme, Palette as PaletteType } from "@/lib/templates";

interface ColorEditorProps {
    colors: Record<string, string>;
    onChange: (colors: Record<string, string>) => void;
}

function ColorEditor({ colors, onChange }: ColorEditorProps) {
    const colorKeys = [
        { key: "primary", label: "Primary" },
        { key: "secondary", label: "Secondary" },
        { key: "accent", label: "Accent" },
        { key: "background", label: "Background" },
        { key: "surface", label: "Surface" },
        { key: "text_primary", label: "Text Primary" },
        { key: "text_secondary", label: "Text Secondary" },
        { key: "border", label: "Border" },
    ];

    const handleColorChange = (key: string, value: string) => {
        onChange({ ...colors, [key]: value });
    };

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {colorKeys.map(({ key, label }) => (
                <div key={key} className="space-y-2">
                    <Label htmlFor={key} className="text-sm text-neutral-400">{label}</Label>
                    <div className="flex items-center gap-2">
                        <input
                            type="color"
                            id={key}
                            value={colors[key] || "#000000"}
                            onChange={(e) => handleColorChange(key, e.target.value)}
                            className="w-10 h-10 rounded-md border border-neutral-700 bg-transparent cursor-pointer"
                        />
                        <Input
                            value={colors[key] || ""}
                            onChange={(e) => handleColorChange(key, e.target.value)}
                            placeholder="#000000"
                            className="flex-1 bg-neutral-900 border-neutral-700 text-white font-mono text-sm"
                        />
                    </div>
                </div>
            ))}
        </div>
    );
}

export default function AdminTemplatesPage() {
    const { loading: authLoading } = useAuth();
    const [templates, setTemplates] = useState<Template[]>([]);
    const [palettes, setPalettes] = useState<PaletteType[]>([]);
    const [, setThemes] = useState<Theme[]>([]);
    const [loading, setLoading] = useState(true);

    // Editor State
    const [editingPalette, setEditingPalette] = useState<PaletteType | null>(null);
    const [editedColors, setEditedColors] = useState<Record<string, string>>({});
    const [editedName, setEditedName] = useState("");
    const [previewOpen, setPreviewOpen] = useState(false);
    const [selectedThemeId, setSelectedThemeId] = useState("modern");

    useEffect(() => {
        async function fetchData() {
            try {
                const [templatesData, themesData, palettesData] = await Promise.all([
                    templateApi.getTemplates(),
                    templateApi.getThemes(),
                    templateApi.getPalettes()
                ]);
                setTemplates(templatesData);
                setThemes(themesData);
                setPalettes(palettesData);
                if (themesData.length > 0) {
                    setSelectedThemeId(themesData[0].theme_id);
                }
            } catch (error) {
                console.error("Failed to fetch data:", error);
            } finally {
                setLoading(false);
            }
        }

        fetchData();
    }, []);

    const [saving, setSaving] = useState(false);

    const handleEditPalette = (palette: PaletteType) => {
        setEditingPalette(palette);
        setEditedColors(palette.colors);
        setEditedName(palette.name);
    };

    const handleSavePalette = async () => {
        if (!editingPalette) return;

        setSaving(true);
        try {
            const updated = await templateApi.updatePalette(editingPalette.id, {
                name: editedName,
                colors: editedColors
            });

            // Update local state
            setPalettes(prev => prev.map(p => p.id === updated.id ? updated : p));
            setEditingPalette(null);
        } catch (error) {
            console.error("Failed to save palette:", error);
        } finally {
            setSaving(false);
        }
    };

    const previewUrl = templateApi.getPreviewUrl(selectedThemeId, "title");

    if (authLoading || loading) {
        return (
            <div className="flex items-center justify-center p-8 h-[50vh]">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
            </div>
        );
    }

    return (
        <div className="flex flex-col space-y-6 p-4 md:p-8 pt-6">
            {/* Header */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                    <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white">Template Admin</h2>
                    <p className="text-neutral-400">Manage color palettes and template designs.</p>
                </div>
                <Button className="bg-emerald-600 hover:bg-emerald-700 text-white">
                    <Plus className="mr-2 h-4 w-4" />
                    New Palette
                </Button>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="palettes" className="space-y-6">
                <TabsList className="bg-neutral-900 border border-neutral-800">
                    <TabsTrigger value="palettes" className="data-[state=active]:bg-neutral-800 data-[state=active]:text-white">
                        <Palette className="mr-2 h-4 w-4" />
                        Color Palettes
                    </TabsTrigger>
                    <TabsTrigger value="templates" className="data-[state=active]:bg-neutral-800 data-[state=active]:text-white">
                        Templates
                    </TabsTrigger>
                </TabsList>

                {/* Palettes Tab */}
                <TabsContent value="palettes" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {palettes.map((palette) => (
                            <Card key={palette.id} className="bg-neutral-900 border-neutral-800 hover:border-neutral-700 transition-colors">
                                <CardHeader className="pb-3">
                                    <div className="flex justify-between items-start">
                                        <CardTitle className="text-lg text-white">{palette.name}</CardTitle>
                                        {palette.is_default && (
                                            <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                                                Default
                                            </Badge>
                                        )}
                                    </div>
                                    <CardDescription className="text-neutral-500 capitalize">
                                        {palette.category}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {/* Color Swatches */}
                                    <div className="flex gap-1 flex-wrap">
                                        {Object.entries(palette.colors).slice(0, 5).map(([key, color]) => (
                                            <div
                                                key={key}
                                                className="w-8 h-8 rounded-md border border-neutral-700"
                                                style={{ backgroundColor: color }}
                                                title={`${key}: ${color}`}
                                            />
                                        ))}
                                    </div>
                                </CardContent>
                                <CardFooter className="flex justify-between pt-3 border-t border-neutral-800">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="text-neutral-400 hover:text-white"
                                        onClick={() => handleEditPalette(palette)}
                                    >
                                        Edit Colors
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="text-neutral-400 hover:text-white"
                                        onClick={() => {
                                            setSelectedThemeId("modern"); // Apply palette preview
                                            setPreviewOpen(true);
                                        }}
                                    >
                                        <Eye className="mr-2 h-4 w-4" />
                                        Preview
                                    </Button>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                </TabsContent>

                {/* Templates Tab */}
                <TabsContent value="templates" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {templates.map((template) => (
                            <Card key={template.id} className="bg-neutral-900 border-neutral-800 hover:border-neutral-700 transition-colors">
                                <CardHeader>
                                    <div className="flex justify-between items-start">
                                        <CardTitle className="text-lg text-white">{template.name}</CardTitle>
                                        <Badge variant="secondary" className="capitalize text-xs bg-neutral-800 text-neutral-300">
                                            {template.content_type}
                                        </Badge>
                                    </div>
                                    <CardDescription className="text-neutral-500">
                                        {template.description}
                                    </CardDescription>
                                </CardHeader>
                                <CardFooter className="flex justify-between pt-3 border-t border-neutral-800">
                                    <span className="text-xs text-neutral-500">v{template.version}</span>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="text-neutral-400 hover:text-white"
                                    >
                                        Edit HTML
                                    </Button>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                </TabsContent>
            </Tabs>

            {/* Color Editor Dialog */}
            <Dialog open={!!editingPalette} onOpenChange={(open) => !open && setEditingPalette(null)}>
                <DialogContent className="max-w-3xl bg-neutral-950 border-neutral-800">
                    <DialogHeader>
                        <DialogTitle className="text-xl text-white">Edit Palette</DialogTitle>
                        <DialogDescription className="text-neutral-400">
                            Modify the colors in this palette. Changes will affect all themes using it.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-6 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="palette-name" className="text-neutral-400">Palette Name</Label>
                            <Input
                                id="palette-name"
                                value={editedName}
                                onChange={(e) => setEditedName(e.target.value)}
                                className="bg-neutral-900 border-neutral-700 text-white"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label className="text-neutral-400">Colors</Label>
                            <ColorEditor colors={editedColors} onChange={setEditedColors} />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setEditingPalette(null)} className="text-neutral-400" disabled={saving}>
                            Cancel
                        </Button>
                        <Button onClick={handleSavePalette} className="bg-emerald-600 hover:bg-emerald-700 text-white" disabled={saving}>
                            {saving ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Save className="mr-2 h-4 w-4" />
                            )}
                            {saving ? "Saving..." : "Save Changes"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Preview Dialog */}
            <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
                <DialogContent className="max-w-5xl h-[85vh] flex flex-col p-0 bg-neutral-950 border-neutral-800 overflow-hidden">
                    <DialogHeader className="p-6 pb-2 shrink-0 border-b border-neutral-800">
                        <DialogTitle className="text-white">Live Preview</DialogTitle>
                        <DialogDescription className="text-neutral-400">
                            See how the palette looks on actual slides.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 bg-neutral-900 p-4 md:p-8 flex items-center justify-center overflow-hidden">
                        <div className="w-full h-full max-w-[1280px] max-h-[720px] shadow-2xl rounded-lg overflow-hidden border border-neutral-700">
                            <iframe
                                src={previewUrl}
                                className="w-full h-full border-0"
                                title="Template Preview"
                            />
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
