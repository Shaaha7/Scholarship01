"use client";
import { useState } from "react";
import { Search, Filter, Calendar, IndianRupee, ArrowLeft, GraduationCap } from "lucide-react";
import Link from "next/link";
import { useScholarships } from "@/hooks/useScholarships";
import { ScholarshipCard } from "@/components/scholarship/ScholarshipCard";

const CATEGORIES = ["All", "BC", "MBC", "SC", "ST", "General", "OBC", "EWS", "Minority"];

export default function ScholarshipsPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [maxIncome, setMaxIncome] = useState("");
  const [gender, setGender] = useState("any");

  const { data, isLoading, error } = useScholarships({
    q: search || undefined,
    category: category === "All" ? undefined : category,
    max_income: maxIncome ? parseFloat(maxIncome) : undefined,
    gender: gender !== "any" ? gender : undefined,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="gov-stripe" />
      <header className="bg-white border-b shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-4">
          <Link href="/" className="text-muted-foreground hover:text-foreground p-1.5 rounded-md hover:bg-muted">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="flex-1 relative">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search scholarships in English..."
              className="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-muted/50"
            />
          </div>
          <Link href="/chat" className="flex items-center gap-2 bg-orange-500 text-white text-sm px-3 py-2 rounded-lg hover:bg-orange-600 transition-colors whitespace-nowrap">
            <GraduationCap className="w-4 h-4" />AI Guide
          </Link>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Category filter */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-6">
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={"px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors border " +
                (category === cat ? "bg-blue-700 text-white border-blue-700" : "bg-card text-muted-foreground border-border hover:border-blue-300 hover:text-blue-700")}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Filters row */}
        <div className="flex gap-3 mb-6 flex-wrap">
          <div className="flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-2">
            <IndianRupee className="w-4 h-4 text-muted-foreground" />
            <input
              type="number"
              value={maxIncome}
              onChange={e => setMaxIncome(e.target.value)}
              placeholder="Max Income (₹)"
              className="text-sm focus:outline-none bg-transparent w-36"
            />
          </div>
          <select
            value={gender}
            onChange={e => setGender(e.target.value)}
            className="text-sm border border-border rounded-lg px-3 py-2 bg-card focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="any">All Genders</option>
            <option value="female">Female Only</option>
            <option value="male">Male Only</option>
          </select>
        </div>

        {/* Results */}
        {isLoading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-card border rounded-xl p-5 animate-pulse h-48" />
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-16">
            <p className="text-destructive">Failed to load scholarships. Please try again.</p>
          </div>
        ) : !data?.items?.length ? (
          <div className="text-center py-16">
            <GraduationCap className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground">No scholarships found. Try adjusting your filters.</p>
            <Link href="/chat" className="mt-4 inline-flex items-center gap-2 text-blue-700 hover:underline text-sm">
              Ask the AI Guide instead
            </Link>
          </div>
        ) : (
          <>
            <p className="text-sm text-muted-foreground mb-4">{data.total} scholarships found</p>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.items.map((s: any) => <ScholarshipCard key={s.id} scholarship={s} />)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
