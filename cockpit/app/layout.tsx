import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Qadam",
  description:
    "A boutique macro intelligence fund running on a hybrid system of local orchestration, AI research, and quantum-assisted modelling."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
