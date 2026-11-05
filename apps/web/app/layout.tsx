import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'V-Index — Job index', description: 'Search jobs with transparent sources and indexing evidence.' };
export default function Layout({children}: Readonly<{children:React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
