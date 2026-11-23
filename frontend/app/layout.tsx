import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Knowly",
  description: "Enterprise AI knowledge and research assistant",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
