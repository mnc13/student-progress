export const metadata = {
  title: 'MedEdu',
  description: 'Personalized learning for medical students',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white text-gray-900">
        <div className="mx-auto max-w-5xl p-6">
          <header className="mb-6 flex items-center justify-between">
            <h1 className="text-xl font-semibold">MedEdu</h1>
            <nav className="text-sm">
              <a href="/" className="hover:underline mr-4">Home</a>
              <a href="/study" className="hover:underline">Study</a>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  )
}
