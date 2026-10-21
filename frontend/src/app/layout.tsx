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
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link 
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className="h-full bg-[#030712] text-slate-100 antialiased selection:bg-indigo-500/30 selection:text-indigo-200 font-sans overflow-hidden">
        {children}
      </body>
    </html>
  );
}
