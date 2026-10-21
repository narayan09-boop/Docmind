import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DocMind — Editorial RAG Research & Evaluation Platform',
  description: 'A thoughtful research console for grounded retrieval-augmented generation and continuous model evaluation.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link 
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Press+Start+2P&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className="h-full bg-paper text-espresso font-sans antialiased selection:bg-terracotta/20 selection:text-espresso">
        {children}
      </body>
    </html>
  );
}
