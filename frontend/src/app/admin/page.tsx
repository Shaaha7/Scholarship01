"use client";
import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Users, BookOpen, Bell, TrendingUp, Upload, Plus, LogOut, Shield } from "lucide-react";
import Link from "next/link";
import { useAdminStats, useCreateScholarship } from "@/hooks/useAdmin";

export default function AdminDashboard() {
  const { data: stats, isLoading } = useAdminStats();

  const categoryData = stats ? Object.entries(stats.category_breakdown).map(([name, count]) => ({ name, count })) : [];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="gov-stripe" />
      <header className="bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-900 rounded-lg flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="font-display font-bold text-blue-900">TamilScholar Admin</p>
              <p className="text-xs text-muted-foreground">Management Console</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/admin/scholarships/new" className="flex items-center gap-2 bg-blue-700 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-800 transition-colors">
              <Plus className="w-4 h-4" />Add Scholarship
            </Link>
            <Link href="/admin/upload" className="flex items-center gap-2 border border-border text-sm px-4 py-2 rounded-lg hover:bg-muted transition-colors">
              <Upload className="w-4 h-4" />Upload PDF
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-display font-bold text-foreground">Dashboard Overview</h1>
          <p className="text-muted-foreground mt-1">Tamil Nadu Scholarship Portal — Admin View</p>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-card border rounded-xl p-6 animate-pulse h-28" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
            {[
              { icon: BookOpen, label: "Total Scholarships", value: stats?.total_scholarships ?? 0, sub: `${stats?.active_scholarships ?? 0} active`, color: "blue" },
              { icon: Users, label: "Registered Users", value: stats?.total_users ?? 0, sub: "Students", color: "green" },
              { icon: TrendingUp, label: "Applications", value: stats?.total_applications ?? 0, sub: "Saved/Applied", color: "orange" },
              { icon: Bell, label: "Categories", value: Object.keys(stats?.category_breakdown ?? {}).length, sub: "BC, MBC, SC, ST...", color: "purple" },
            ].map(card => (
              <div key={card.label} className="bg-card border border-border rounded-xl p-6 shadow-sm">
                <div className={"w-10 h-10 rounded-lg mb-3 flex items-center justify-center bg-" + card.color + "-100"}>
                  <card.icon className={"w-5 h-5 text-" + card.color + "-700"} />
                </div>
                <p className="text-2xl font-display font-bold text-foreground">{card.value.toLocaleString()}</p>
                <p className="text-sm font-medium text-foreground mt-0.5">{card.label}</p>
                <p className="text-xs text-muted-foreground">{card.sub}</p>
              </div>
            ))}
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h2 className="font-display font-semibold text-foreground mb-4">Scholarships by Category</h2>
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={categoryData}>
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#1d4ed8" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-52 flex items-center justify-center text-muted-foreground text-sm">No data yet</div>
            )}
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h2 className="font-display font-semibold text-foreground mb-4">Quick Actions</h2>
            <div className="space-y-3">
              {[
                { href: "/admin/scholarships/new", label: "Create New Scholarship", icon: Plus, desc: "Add a scholarship manually" },
                { href: "/admin/upload", label: "Upload Scholarship PDF", icon: Upload, desc: "Parse and ingest PDF into AI" },
                { href: "/admin/users", label: "Manage Users", icon: Users, desc: "View and manage student accounts" },
              ].map(action => (
                <Link key={action.href} href={action.href} className="flex items-center gap-4 p-3 rounded-lg border border-border hover:bg-muted transition-colors">
                  <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center">
                    <action.icon className="w-4 h-4 text-blue-700" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">{action.label}</p>
                    <p className="text-xs text-muted-foreground">{action.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
