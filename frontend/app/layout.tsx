import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Sidebar from './components/Sidebar'
import { AppProvider } from '@/lib/context'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Hyperfeed',
  description: 'AI-powered social media content generator',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen bg-gray-50`} suppressHydrationWarning={true}>
        <AppProvider>
          <div className="flex h-screen">
            <Sidebar />
            <main className="flex-1 overflow-auto">
              {children}
            </main>
          </div>
        </AppProvider>
      </body>
    </html>
  )
}
