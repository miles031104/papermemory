import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaperMemory",
  description: "Local-first multimodal paper memory for research agents"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
