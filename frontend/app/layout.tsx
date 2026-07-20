import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gravel Manager",
  description: "Train with intent. Ride beyond the numbers.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

