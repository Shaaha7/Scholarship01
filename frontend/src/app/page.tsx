import Link from "next/link";
import { GraduationCap, Bot, Search, Bell, Shield, Globe } from "lucide-react";

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <div className="gov-stripe w-full" />
      <header className="bg-white border-b border-border sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-800 rounded-lg flex items-center justify-center">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <div>
              <p className="font-display font-bold text-blue-900 text-lg leading-none">TamilScholar Pro</p>
              <p className="text-xs text-muted-foreground font-tamil">Tamil Nadu Scholarship Portal</p>
            </div>
          </div>
          <nav className="flex items-center gap-2">
            <Link href="/scholarships" className="text-sm text-muted-foreground hover:text-foreground px-3 py-2 rounded-md hover:bg-muted transition-colors">Scholarships</Link>
            <Link href="/chat" className="text-sm bg-blue-700 text-white px-4 py-2 rounded-lg hover:bg-blue-800 transition-colors flex items-center gap-2">
              <Bot className="w-4 h-4" />AI Chat
            </Link>
          </nav>
        </div>
      </header>

      <section className="relative bg-gradient-to-br from-blue-900 via-blue-800 to-orange-600 text-white py-24 overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-72 h-72 bg-white rounded-full blur-3xl" />
          <div className="absolute bottom-10 right-10 w-96 h-96 bg-orange-300 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-sm mb-6 backdrop-blur-sm">
            <Shield className="w-4 h-4 text-orange-300" />
            <span>Official Tamil Nadu Government Scholarship Portal</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-display font-bold mb-4">
            Your Education<br/>
            <span className="text-orange-300">Scholarship</span> Finder
          </h1>
          <p className="text-xl text-blue-100 mb-3 font-tamil">Find Your Scholarship in Tamil or English</p>
          <p className="text-blue-200 mb-10 max-w-2xl mx-auto">
            AI-powered search for BC, MBC, SC, ST, General and Minority scholarships.
            Ask in Tamil, Tanglish, or English.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/chat" className="bg-orange-500 hover:bg-orange-600 text-white font-semibold px-8 py-4 rounded-xl text-lg transition-all hover:scale-105 shadow-lg flex items-center justify-center gap-2">
              <Bot className="w-5 h-5" />Chat with AI Guide
            </Link>
            <Link href="/scholarships" className="bg-white/10 hover:bg-white/20 border border-white/30 text-white font-semibold px-8 py-4 rounded-xl text-lg transition-all backdrop-blur-sm flex items-center justify-center gap-2">
              <Search className="w-5 h-5" />Browse Scholarships
            </Link>
          </div>
        </div>
      </section>

      <section className="bg-white border-b py-10">
        <div className="max-w-7xl mx-auto px-4 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { value: "150+", label: "Active Scholarships" },
            { value: "8", label: "Categories" },
            { value: "AI-Powered", label: "Smart Search" },
            { value: "Free", label: "Always Free" },
          ].map((s) => (
            <div key={s.label} className="py-4">
              <p className="text-3xl font-display font-bold text-blue-800">{s.value}</p>
              <p className="text-sm font-medium mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="bg-gray-950 text-gray-400 py-8 text-center text-sm">
        <div className="gov-stripe mb-6" />
        <p className="font-display text-white mb-1">TamilScholar Pro</p>
        <p>Tamil Nadu Government Initiative</p>
        <p className="mt-2 text-gray-500">2024 Department of Social Welfare, Tamil Nadu</p>
      </footer>
    </main>
  );
}
