import { api } from "./api-client";

export interface Template {
    id: string;
    template_id: string;
    name: string;
    description: string;
    content_type: string;
    category: string;
    html_template: string;
    css_styles: string;
    version: string;
}

export interface Palette {
    id: string;
    name: string;
    category: string;
    colors: Record<string, string>;
    is_default: boolean;
}

export interface Theme {
    id: string;
    theme_id: string;
    name: string;
    description: string;
    palette: Palette;
    typography: any;
    spacing: any;
    borders: any;
}

export const templateApi = {
    getTemplates: async (category?: string) => {
        let url = '/api/templates';
        if (category && category !== 'All') {
            url += `?category=${category.toLowerCase()}`;
        }
        return api.get<Template[]>(url);
    },

    getThemes: async () => {
        return api.get<Theme[]>('/api/themes');
    },

    getPalettes: async () => {
        return api.get<Palette[]>('/api/palettes');
    },

    createPalette: async (data: { name: string; category: string; colors: Record<string, string> }) => {
        return api.post<Palette>('/api/palettes', data);
    },

    updatePalette: async (id: string, data: { name?: string; category?: string; colors?: Record<string, string> }) => {
        return api.request<Palette>(`/api/palettes/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },

    deletePalette: async (id: string) => {
        return api.request<{ status: string }>(`/api/palettes/${id}`, {
            method: 'DELETE',
        });
    },

    getPreviewUrl: (themeId: string, templateType: string = 'title') => {
        // Construct standard API URL but ensure it points to backend port 8080
        const baseUrl = api.getBaseUrl();
        return `${baseUrl}/api/themes/${themeId}/preview?template_type=${templateType}`;
    }
};

