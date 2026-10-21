import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DocMind | Multimodal Intelligent Knowledge Copilot',
  description: 'Enterprise Multimodal Knowledge Copilot with Grounded Citations, Hybrid Retrieval & Evaluation Suite',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full">
      <body className="h-full bg-slate-950 text-slate-100 antialiased selection:bg-indigo-500/30 selection:text-indigo-200">
        {children}
      </body>
    </html>
  );
}
