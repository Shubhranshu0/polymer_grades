import type { Metadata } from "next";
import { Geist, Geist_Mono, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-serif-display",
  subsets: ["latin"],
  weight: ["600", "700"],
});

export const metadata: Metadata = {
  title: "SHLOK Polymer Grade Book — HDPE · LLDPE · LDPE · PP TDS Comparison",
  description:
    "Complete polymer grade book: 245 technical data sheets from Haldia (Halene), Reliance, IOCL and OPaL with TDS properties, processing windows, BIS codes, September 2026 prices and competitive mapping.",
  keywords: [
    "polymer",
    "TDS",
    "HDPE",
    "LLDPE",
    "LDPE",
    "polypropylene",
    "Halene",
    "Relene",
    "Repol",
    "Propel",
    "OPaL",
    "grade book",
  ],
  icons: {
    icon: "/shlok-logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${sourceSerif.variable} font-sans antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
