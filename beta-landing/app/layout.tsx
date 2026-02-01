import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import SmoothScrolling from "@/components/SmoothScrolling";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "SankoSlides Beta - Turn Notes into Presentations",
  description: "SankoSlides transforms your notes, PDFs, and raw ideas into professional, university-grade presentations. Built for Ghanaian students.",
  keywords: ["presentation", "slides", "UMaT", "Ghana", "university", "AI", "PowerPoint"],
  authors: [{ name: "SankoSlides" }],
  openGraph: {
    title: "SankoSlides Beta - Turn Notes into Presentations",
    description: "Transform your notes into university-grade presentations in minutes. Built for Ghanaian students.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`}>
        <SmoothScrolling>{children}</SmoothScrolling>
      </body>
    </html>
  );
}
