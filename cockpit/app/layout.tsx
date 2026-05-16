import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Qadam Cockpit",
  description: "Local-first Qadam intelligence cockpit"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

