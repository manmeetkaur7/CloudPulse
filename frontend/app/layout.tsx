import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CloudPulse",
  description: "Real-time application observability foundation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
