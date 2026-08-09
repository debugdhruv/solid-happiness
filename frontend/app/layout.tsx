import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Support Ticket Analytics",
  description: "Support operations analytics and root-cause monitoring dashboard"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

