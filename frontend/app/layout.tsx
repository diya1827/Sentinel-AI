import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sentinel AI",
  description: "AI-powered Application Security Reviewer",
};

/**
 * Root layout — wraps every route. Scaffold only; global providers
 * (theme, query client, etc.) will be added here as features land.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-pistachio-200 text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
