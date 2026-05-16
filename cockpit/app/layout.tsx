import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "Qadam Cockpit",
  description: "Local-first Qadam intelligence cockpit"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const document = (
    <html lang="en">
      <body>{children}</body>
    </html>
  );

  if (!publishableKey) {
    return document;
  }

  return (
    <ClerkProvider publishableKey={publishableKey}>
      {document}
    </ClerkProvider>
  );
}
