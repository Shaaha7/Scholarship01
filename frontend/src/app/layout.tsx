import type { Metadata, Viewport } from "next";
import { Noto_Sans, Noto_Sans_Tamil, Mukta, JetBrains_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getLocale } from "next-intl/server";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { Toaster } from "@/components/ui/toaster";
import "./globals.css";

const notoSans = Noto_Sans({ subsets: ["latin"], variable: "--font-noto-sans", weight: ["300","400","500","600","700"] });
const notoTamil = Noto_Sans_Tamil({ subsets: ["tamil"], variable: "--font-noto-sans-tamil", weight: ["300","400","500","600","700"] });
const mukta = Mukta({ subsets: ["latin"], variable: "--font-mukta", weight: ["400","500","600","700","800"] });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono", weight: ["400","500"] });

export const metadata: Metadata = {
  title: { default: "TamilScholar Pro – Tamil Nadu Scholarship Portal", template: "%s | TamilScholar Pro" },
  description: "AI-powered scholarship discovery for Tamil Nadu students. Find BC, MBC, SC, ST scholarships in Tamil and English.",
  keywords: ["scholarship", "Tamil Nadu", "BC", "MBC", "SC", "ST", "education"],
};

export const viewport: Viewport = { themeColor: "#1e3a8a" };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();
  return (
    <html lang={locale} className={`${notoSans.variable} ${notoTamil.variable} ${mukta.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-background font-sans antialiased">
        <NextIntlClientProvider messages={messages}>
          <QueryProvider>
            {children}
            <Toaster />
          </QueryProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
